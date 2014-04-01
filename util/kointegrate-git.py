#!/usr/bin/env python
# Copyright (c) 2014 ActiveState Software Inc.

"""
Easily integrate a change from its branch or tree to other active
Komodo branches. This will help create appropriate commit messages.

Notes:
    - This only handles git at the moment
"""

__version_info__ = (0, 0, 1)
__version__ = '.'.join(map(str, __version_info__))
__usage__ = """
    cd SOURCE-BRANCH-DIR
    %(prog)s COMMIT-ID TARGET-BRANCH-NAMES...
"""

import applib
import argparse
import cStringIO
import fnmatch
import itertools
import logging
import os
import os.path
import subprocess
import sys
import textwrap

from ConfigParser import SafeConfigParser
from os.path import exists, expanduser, isdir, join, normpath

#---- globals

log = logging.getLogger("kointegrate")

#---- handling of active branches

class IntegrationError(RuntimeError): pass

class Branch(object):
    scc_is_distributed = False ### If true, this is a DVCS and just commit locally

    def __init__(self, name, base_dir):
        self.name = name
        self.base_dir = normpath(base_dir)

    @property
    def desc(self):
        return self.name

    def __repr__(self):
        return "<%s: %r at %s>" % (type(self).__name__, self.name, self.base_dir)

    def __str__(self):
        return "%r branch at '%s' (%s)" % (self.name, self.base_dir, self.scc_type)

    def __cmp__(self, other):
        return cmp(self.name, other.name) or cmp(self.base_dir, other.base_dir)

    def get_revision(self, revision):
        raise NotImplementedError("%s needs to implement get_revision" % self)

    def get_missing_paths(self, paths):
        """Return the set of paths that don't exist on this branch
        @param paths {iterable of ChangedPath} paths to check
        """
        raise NotImplementedError("%s needs to implement get_missing_paths" % self)

    def check_patch(self, patch, options):
        """Check that the given patch can apply
        @param patch {str} The patch to apply
        @param options {Namespace} command line options
        @return {set} Paths that failed to apply
        """
        raise NotImplementedError("%s needs to implement check_patch" % self)

    def apply_patch(self, revision, patch, paths, options):
        """Apply the given patch.
        @param revision {Revision} The revision the change was from
        @param patch {str} The patch to apply; this should have passed check_patch
        @param paths {iterable of ChangedPath} paths modified in the revision
        @param options {Namespace} command line options
        @returns {str} The commit message
        @raises {IntegrationError} The patch failed to apply
        If the patch application fails, the state of the tree should be left
        such that the user may manually resolve the bad patch and continue
        committing.
        """
        raise NotImplementedError("%s needs to implement apply_patch" % self)

    def commit(self, revision, paths, options):
        """Commit the changes, using a message based on the given source revision
        @param revision {Revision} The revision the change was from
        @param paths {iterable of ChangedPath} paths modified in the revision
        @param options {Namespace} command line options
        """
        raise NotImplementedError("%s needs to implement commit" % self)

class NonExistantBranch(Branch):
    scc_type = "non-existant"
    def __repr__(self):
        return "<Branch: %s, base dir `%s' does not exist>" \
               % (self.name, self.base_dir)

class GitBranch(Branch):
    scc_type = "git"
    scc_is_distributed = True

    _git_exe_cache = None

    @property
    def _git_exe(self):
        if GitBranch._git_exe_cache is None:
            import which
            setattr(GitBranch, "_git_exe_cache", which.which("git"))
        return GitBranch._git_exe_cache

    def _open(self, *args, **kwargs):
        kwargs.setdefault("cwd", self.base_dir)
        kwargs["env"] = dict(kwargs.get("env", os.environ))
        kwargs["env"]["LANG"] = "C"
        log.debug("git: %s", " ".join(args))
        return subprocess.Popen([self._git_exe] + list(args), **kwargs)

    def _execute(self, *args, **kwargs):
        kwargs.setdefault("cwd", self.base_dir)
        kwargs["env"] = dict(kwargs.get("env", os.environ))
        kwargs["env"]["LANG"] = "C"
        log.debug("git: %s", " ".join(args))
        return subprocess.check_call([self._git_exe] + list(args), **kwargs)

    def _capture_output(self, *args, **kwargs):
        kwargs.setdefault("cwd", self.base_dir)
        kwargs["env"] = dict(kwargs.get("env", os.environ))
        kwargs["env"]["LANG"] = "C"
        log.debug("git: %s", " ".join(args))
        return subprocess.check_output([self._git_exe] + list(args), **kwargs)

    @property
    def is_clean(self):
        # Clean trees have no output
        return not self._capture_output("status", "--porcelain")

    def get_revision(self, revision):
        # Check that the revision exists
        try:
            with open("/dev/null", "w+") as null:
                subprocess.check_call([self._git_exe, "log", "-1", revision],
                    stdout=null, stderr=null)
        except:
            raise
        return GitRevision(revision, self)

    def get_missing_paths(self, paths):
        paths = set(paths)
        found_paths = self._capture_output("ls-files", "-z", "--",
                                           *map(str, paths))
        for path in list(paths):
            if path.src in found_paths:
                paths.discard(path)
        log.debug("missing paths: %r", paths)
        return paths

    @property
    def desc(self):
        branch = self._capture_output("describe", "--all", "--abbrev=0").strip()
        if not branch:
            return self.__dict__.get("name", "unknown branch")
        if branch.startswith("remotes/"):
            branch = branch[len("remotes/"):]
        if branch.startswith("tags/"):
            return branch[len("tags/"):] + " tag"
        if branch.startswith("heads/"):
            return branch[len("heads/"):] + " branch"
        return branch
    @desc.setter
    def desc(self, value):
        self.__dict__["name"] = value

    __git_dir_cache = None
    @property
    def _git_dir(self):
        if self.__git_dir_cache is None:
            git_dir = self._capture_output("rev-parse", "--git-dir").strip()
            self.__git_dir_cache = join(self.base_dir, git_dir)
        return self.__git_dir_cache

    def check_patch(self, patch, options):
        cmd = ["apply", "--check", "--binary", "-"]
        proc = self._open(*cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        stderr = proc.communicate(patch)[1]
        if not proc.returncode:
            return {}

        failed_paths = set()
        for line in stderr.splitlines():
            if not line.startswith("error:"):
                continue
            line = line.split(":", 1)[-1].strip()
            if line.startswith("patch failed:"):
                failed_paths.add(line.split(":", 1)[-1].rsplit(":", 1)[0].strip())
            else:
                failed_paths.add(line.rsplit(":", 1)[0].strip())
        return failed_paths

    def apply_patch(self, revision, patch, paths, options):
        # Save the commit message
        message = "\n\n(integrated from {branch} change {rev} by {author})"
        message = message.format(branch=self.desc,
                                 rev=revision.pretty_rev,
                                 author=revision.author)
        message = revision.description + message
        with open(join(self._git_dir, "GITGUI_MSG"), "w") as msg_file:
            msg_file.write(message)

        # Apply all deletes first
        for path in paths:
             if path.action == ChangedPath.DELETED:
                abs_path = join(self.base_dir, path.src)
                log.debug("Remove file %s", abs_path)
                if exists(abs_path):
                    os.unlink(abs_path)

        # Apply the patch
        all_changed_paths = set(path.src for path in paths)
        all_changed_paths |= set(path.dest for path in paths)
        all_changed_paths = filter(bool, all_changed_paths)
        cmd = ["apply", "--binary", "--reject", "-"]
        proc = self._open(*cmd, stdin=subprocess.PIPE)
        proc.communicate(patch)
        self._execute("add", "--", *all_changed_paths)
        if proc.returncode:
            raise IntegrationError("Failed to apply patch")
        return message

    def commit(self, revision, paths, options):
        try:
            with open(join(self._git_dir, "GITGUI_MSG"), "r") as msg_file:
                message = msg_file.read()
        except:
            message = ""
        if not message.strip():
            message = "\n\n(integrated from {branch} change {rev} by {author})"
            message = message.format(branch=self.desc,
                                     rev=revision.pretty_rev,
                                     author=revision.author)
            message = revision.description + message
        all_changed_paths = set(path.src for path in paths)
        all_changed_paths |= set(path.dest for path in paths)
        all_changed_paths = filter(bool, all_changed_paths)
        cmd = ["commit", "--only",
               "--author", revision.author,
               "--date", revision.date,
               "--message", message,
               "--"] + all_changed_paths
        self._execute(*cmd)

#---- configuration/prefs handling

class Configuration(SafeConfigParser):
    branches = None

    def __init__(self):
        SafeConfigParser.__init__(self)
        self._load()

    @property
    def cfg_path(self):
        user_data_dir = applib.user_data_dir("komodo-dev", "ActiveState")
        return join(user_data_dir, "kointegrate.ini")

    def _load(self):
        self.read(self.cfg_path)
        self.branches = {}
        if self.has_section("active-branches"):
            for name, base_dir in self.items("active-branches"):
                base_dir = expanduser(base_dir)
                if not exists(base_dir):
                    self.branches[name] = NonExistantBranch(name, base_dir)
                #elif isdir(join(base_dir, ".svn")):
                #    self.branches[name] = SVNBranch(name, base_dir)
                elif isdir(join(base_dir, ".git")):
                    self.branches[name] = GitBranch(name, base_dir)
                else:
                    log.info("Ignoring unknown repository at %r", base_dir)

    def get_branch(self, branch_name):
        try:
            branch = self.branches[branch_name]
        except KeyError:
            branches = ('    "%s" (%s) at %s' %
                            (branch.name, branch.scc_type, branch.base_dir)
                        for branch in self.branches.values())
            msg = ('\n    "%s" is an unknown active Komodo branch name\n'
                   'known branches are:\n%s'
                   % (branch_name, '\n'.join(branches)))
            raise IntegrationError(msg)
        return branch

    def get_revision(self, revision):
        for branch in self.branches.values():
            if not os.getcwd().startswith(branch.base_dir):
                continue
            try:
                return branch.get_revision(revision)
            except:
                msg = "%s is not a revision in %s" % (revision, branch)
                raise argparse.ArgumentTypeError(msg)
        msg = "Failed to find branch of current working directory %s" % (os.getcwd())
        raise IntegrationError(msg)

cfg = Configuration()

#--- functions

class HelpIniAction(argparse.Action):
    def __init__(self, *args, **kwargs):
        super(HelpIniAction, self).__init__(*args, nargs=0, **kwargs)
    def __call__(self, parser, namespace, values, option_string=None):
        print textwrap.dedent("""
            Configuring %s
            --------------------------

            This script uses a "kointegrate.ini" file here:
                %s

            The "[active-branches]" section of that file (a normal
            INI-syntax file) is used. Each entry in that section should
            be of the form:

                <branch-nickname> = <full-path-to-branch-working-copy>

            For example,

                [active-branches]
                openkomodo = /home/me/play/openkomodo
                devel      = /home/me/wrk/Komodo-devel
                4.3.x      = /home/me/wrk/Komodo-4.3.x
        """ % (parser.prog, cfg.cfg_path))
        sys.exit(0)

class ChangedPath(object):
    """A changed path within a revision"""

    # Action types; renames are split into a (copy, delete) pair.
    ADDED = 1
    MODIFIED = 2
    DELETED = 4
    COPIED = 8
    ALL = (ADDED | MODIFIED | DELETED | COPIED)

    def __init__(self, action, src=None, dest=None):
        if isinstance(action, str):
            action = getattr(self, action.upper())
        assert action in (self.ADDED, self.MODIFIED, self.DELETED, self.COPIED)
        self.action = action
        assert bool(src), "No source provided"
        self.src = src
        self.dest = dest
        self.binary = False

    def __str__(self):
        return self.src

    def __repr__(self):
        action = {
            ChangedPath.ADDED: "A",
            ChangedPath.MODIFIED: "M",
            ChangedPath.DELETED: "D",
            ChangedPath.COPIED: "C",
        }[self.action]
        s = "<change: {action} {src}".format(action=action, src=self.src)
        if self.dest is not None:
            s += " => {dest}".format(dest=self.dest)
        if self.binary:
            s += " #"
        s += ">"
        return s

class Revision(object):
    def __init__(self, revision, branch):
        self.revision = str(revision)
        self.branch = branch

    @property
    def paths(self):
        """The paths that are affected in this revision.
        @returns an iterable of ChangedPath objects.
        """
        raise NotImplementedError("%s needs to implement paths" % self)

    def get_paths(self, types=ChangedPath.ALL):
        """The list of paths, relative to the root of the repository, that are
        affected in this revision.
        @param types {iterable} types to include; empty includes everything.
            valid values are "add", "modify", "delete", "copy"
            (renames are copy + delete)
        @returns iterable of ChangedPath objects.
        """
        raise NotImplementedError("%s needs to implement paths" % self)

    @property
    def description(self):
        """The commit message of this revision"""
        raise NotImplementedError("%s needs to implement description" % self)

    @property
    def summary(self):
        """A one-line summary of the commit message of this revision"""
        return _one_line_summary_from_text(self.description, 60)

    @property
    def author(self):
        """The author of this commit"""
        raise NotImplementedError("%s needs to implement author" % self)

    def get_patch(self, options, paths=None):
        """Get a patch file for this revision
        @param options {Namespace} command-line options
        @param paths {iterable of ChangedPath} paths to include in the patch;
            if not given, all files provided are included
        """
        raise NotImplementedError("%s needs to implement get_patch" % self)

    def integrate(self, options, branch, paths):
        """Integrate this revision into the target branch
        @param options {Namespace} The command line options
        @param branch {Branch} The branch to integrate into
        @param paths {iterable of ChangedPath} The paths to integrate
        """
        if options.exclude_outside_paths:
            paths -= branch.get_missing_paths(paths)
        if not paths:
            log.warn("No files in %s to integrate, skipping %s",
                     options.revision, branch)
            return

        log.debug("Integrating files %s", ", ".join(map(str, paths)))
        patch = self.get_patch(options, paths)
        #log.debug("Got patch: \n    %s", "    ".join(patch.splitlines(True)))

        # Check that this patch can be applied
        failed_paths = branch.check_patch(patch, options)
        if failed_paths:
            prefix = textwrap.fill("During a dry-run patching attempt there "
                                   "were failures in the following files:",
                                   initial_indent=" " * 7,
                                   subsequent_indent=" " * 7)
            suffix = textwrap.fill("You could use the `-x SUBPATH` option to "
                                   "skip a particular file.",
                                   initial_indent=" " * 7,
                                   subsequent_indent=" " * 7)
            message = "%s\n%s\n%s\n" % (prefix[7:],
                                        "\n".join(" " * 11 + p for p in failed_paths),
                                        suffix)
            log.info("")
            log.error(message)
            if options.force:
                if options.interactive:
                    answer = _query_yes_no("Continue integrating failed patch?",
                                           default="no")
                    if answer != "yes":
                        raise IntegrationError("Conflicts in patch")
                    log.info("")
                else:
                    log.warn("Failure applying patch, forcing integration anyway")
            else:
                raise IntegrationError("Conflicts in patch")

        if options.dry_run:
            log.info("Skipping application and commit due to dry-run")
            return True

        # Apply the patch
        try:
            commit_msg = branch.apply_patch(options.revision, patch, paths, options)
        except IntegrationError:
            log.info("")
            if options.force:
                if options.interactive:
                    message = ("There were issues integrating the patch; do "
                               "you want to force a commit anyway?  (You can "
                               "manually fix the branch now if desired)")
                    log.warn(textwrap.fill(message, subsequent_indent=" " * 9) + "\n")
                    answer = _query_yes_no("Continue integrating this change?",
                                           default="no")
                    if answer != "yes":
                        raise
                else:
                    log.warn("Failure applying patch, forcing integration anyway")
            else:
                raise

        # Commit the patch
        log.info("\n\nReady to commit to %s:", branch)
        log.info(_banner("commit message", '-'))
        log.info(commit_msg)
        log.info(_banner(None, '-'))
        log.info("")

        auto_commit = True
        if not branch.scc_is_distributed and options.interactive:
            message = ("Would you like this script to automatically commit "
                       "this integration to '%s'?") % branch
            answer = _query_yes_no(textwrap.fill(message), default=None)
            if answer != "yes":
                auto_commit = False

        if auto_commit:
            branch.commit(self, paths, options)

class GitRevision(Revision):
    def __str__(self):
        return "Git revision %s of %s" % (self.revision[:8], self.branch)

    _paths_cache = None
    def _get_paths(self):
        """The paths affected by this revision.
        @returns hash.
            key is source path, or for deletes, destination path.
            action is a PathTypes constant
            src is the source path (again)
            dest is the destination path (only for copies and renames)
        """
        if self._paths_cache is None:
            cmd = ["diff-tree", "--raw", "--numstat", "-C", "-z", "-r", self.revision]
            lines = self.branch._capture_output(*cmd).split("\0")
            if not lines[-1]:
                lines.pop() # empty line at the end
            self.revision = lines.pop(0) # commit hash of the tree
            paths = {}
            changes = [] # in order

            # Look at the --raw output
            while len(lines) > 0 and lines[0].startswith(":"):
                line = lines.pop(0)
                src_mode, dest_mode, src_hash, dest_hash, action = line[1:].split()

                change = []
                src = lines.pop(0)
                if action[0] == "A":
                    path = ChangedPath(ChangedPath.ADDED, src=src)
                    change.append(path)
                    paths[src] = path
                elif action[0] == "C":
                    path = ChangedPath(ChangedPath.COPIED,
                                       src=src,
                                       dest=lines.pop(0))
                    change.append(path)
                    paths[src] = path
                elif action[0] == "D":
                    path = ChangedPath(ChangedPath.DELETED, src=src)
                    change.append(path)
                    paths[src] = path
                elif action[0] in "M":
                    path = ChangedPath(ChangedPath.MODIFIED, src=src)
                    change.append(path)
                    paths[src] = path
                elif action[0] == "R":
                    # split rename into copy and delete
                    dest = lines.pop(0)
                    path = ChangedPath(ChangedPath.COPIED, src=src, dest=dest)
                    change.append(path)
                    paths[src] = path
                    if dest not in paths:
                        path = ChangedPath(ChangedPath.DELETED, src=dest)
                        change.append(path)
                        paths[dest] = path
                elif acton[0] in "TUX":
                    raise NotImplementedError("Unsuppported change state " + action)
                else:
                    raise NotImplementedError("Unknown change state " + action)

                changes.append(change)

            # Look at the --numstat output
            while len(lines) > 0:
                line = lines.pop(0)
                if line[0] not in "0123456789-":
                    continue
                change = changes.pop(0)
                stats = line.split()[:2]
                change[0].binary = stats[0] == "-"
                change[-1].binary = stats[-1] == "-"

            self._paths_cache = paths
            log.debug("Files in %s: %r", self.revision, self._paths_cache)
        return self._paths_cache

    @property
    def paths(self):
        return set(self._get_paths().values())

    def get_paths(self, types=ChangedPath.ALL):
        paths = set()
        for path in self._get_paths().values():
            if path.action & types:
                paths.add(path.src)
        return paths

    def _get_property_from_log(self, cache_attr, format_string, strip=True):
        if getattr(self, cache_attr, None) is None:
            cmd = ["log", "-1", "--pretty=" + format_string, self.revision]
            cache = self.branch._capture_output(*cmd)
            if strip:
                cache = cache.strip()
            setattr(self, cache_attr, cache)
        return getattr(self, cache_attr)

    _description_cache = None
    @property
    def description(self):
        return self._get_property_from_log("_description_cache", "%B")

    _summary_cache = None
    @property
    def summary(self):
        if self._summary_cache is None:
            cmd = ["log", "-1", "--pretty=%s", self.revision]
            summary = self.branch._capture_output(*cmd).strip()
            self._summary_cache = _one_line_summary_from_text(summary, 60)
        return self._summary_cache

    _author_cache = None
    @property
    def author(self):
        return self._get_property_from_log("_author_cache", "%aN <%aE>")

    _date_cache = None
    @property
    def date(self):
        return self._get_property_from_log("_date_cache", "%ai")

    _pretty_rev_cache = None
    @property
    def pretty_rev(self):
        if self._pretty_rev_cache is None:
            cmd = ["describe", "--long", "--always", self.revision]
            self._pretty_rev_cache = self.branch._capture_output(*cmd).strip()
        return self._pretty_rev_cache

    def get_patch(self, options, paths=None):
        cmd = ["diff", "--no-color", "--binary", self.revision + "^",
               self.revision, "--"] + [path.src for path in paths]
        return self.branch._capture_output(*cmd)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--help-ini", action=HelpIniAction,
                        help="show help on configuring %s and exit" % parser.prog)
    parser.add_argument("-q", "--quiet", dest="log_level",
                        action="store_const", const=logging.WARN,
                        help="suppress informational messages")
    parser.add_argument("-v", "--verbose", dest="log_level",
                        action="store_const", const=logging.DEBUG,
                        help="more verbose output")
    parser.add_argument("-i", "--interactive", action="store_true",
                        help="interactively verify steps of integration "
                             "(default)")
    parser.add_argument("-n", "--non-interactive", action="store_false",
                        dest="interactive", help="no interaction")
    parser.add_argument("-f", "--force", action="store_true",
                        help="force application of patches that won't apply "
                             "cleanly; ignore files missing in the target")
    parser.add_argument("-X", "--exclude-outside-paths", action="store_true",
                        help="exclude (ignore) paths in the changeset "
                             "outside of the branch")
    parser.add_argument("-x", "--exclude", dest="excludes", action="append",
                        metavar="PATTERN",
                        help="Exclude files in the change matching the "
                             "given glob pattern. This is matched against "
                             "the file relative path.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't actually do anything; this may cause the "
                             "integration to fail where it would otherwise succeed")
    parser.add_argument("-V", "--version", action="version", version=__version__)
    parser.add_argument("revision", help="revision (commit hash) to integrate")
    parser.add_argument("branches", help="branches to merge into",
                        nargs="+")
    parser.set_defaults(log_level=logging.INFO, exclude_outside_paths=False,
                        interactive=True, excludes=[], force=False, dry_run=False)
    args = parser.parse_args(argv)
    log.setLevel(args.log_level)

    args.revision = cfg.get_revision(args.revision)

    branches = []
    for branch in args.branches:
        branch = cfg.get_branch(branch)
        if not branch.is_clean:
            msg = "Can't integrate to unclean branch:\n    " + str(branch)
            raise IntegrationError(msg)
        branches.append(branch)
    args.branches[:] = branches

    paths = args.revision.paths
    for path in list(paths):
        matching_excludes = filter(lambda e: fnmatch.fnmatch(path.src, e),
                                   args.excludes)
        if matching_excludes:
            log.info("skipping `%s' (matches excludes: '%s')",
                     path.src, "', '".join(matching_excludes))
            paths.discard(path)

    # Give the user the chance to abort.
    log.info("  change: %s", args.revision)
    log.info("    desc: %s", args.revision.summary)
    log.info("      by: %s", args.revision.author)
    if len(args.branches) == 1:
        log.info("      to: %s", args.branches[0])
    else:
        prefixes = itertools.chain(["to:"], itertools.repeat("   "))
        for i, (prefix, branch) in enumerate(itertools.izip(prefixes, sorted(args.branches)), 1):
            log.info("      %s %d. %s", prefix, i, branch)
    path_names = sorted(map(str, paths))
    if len(paths) > 7:
        path_names = path_names[:7] + ['...and %d other files' % (len(paths) - 7)]
    log.info("   files: %s", ("\n" + " " * 10).join(path_names))

    if args.interactive:
        log.info("")
        answer = _query_yes_no("Continue integrating this change?")
        if answer != "yes":
            return False

    # If any of the files to integrate are binary, then ensure it is
    # okay to integrate them (because can't detect conflicts).
    binary_paths = [path for path in args.revision.paths
                    if path.binary and path.action != ChangedPath.DELETED]
    if False and binary_paths:
        log.info(textwrap.dedent("""
            ***
            The following source files are binary:
                %s

            Integrating these files just copies the whole file over to
            the target. This could result in lost changes in the target.
            ***""") \
            % "\n    ".join(map(str, binary_paths)))
        if args.interactive:
            answer = _query_yes_no("Continue integrating this change?")
            if answer != "yes":
                return False

    for branch in args.branches:
        args.revision.integrate(args, branch, paths)

# Recipe: banner (1.0.1)
def _banner(text, ch='=', length=78):
    """Return a banner line centering the given text.

        "text" is the text to show in the banner. None can be given to have
            no text.
        "ch" (optional, default '=') is the banner line character (can
            also be a short string to repeat).
        "length" (optional, default 78) is the length of banner to make.

    Examples:
        >>> _banner("Peggy Sue")
        '================================= Peggy Sue =================================='
        >>> _banner("Peggy Sue", ch='-', length=50)
        '------------------- Peggy Sue --------------------'
        >>> _banner("Pretty pretty pretty pretty Peggy Sue", length=40)
        'Pretty pretty pretty pretty Peggy Sue'
    """
    if text is None:
        return ch * length
    elif len(text) + 2 + len(ch)*2 > length:
        # Not enough space for even one line char (plus space) around text.
        return text
    else:
        remain = length - (len(text) + 2)
        prefix_len = remain / 2
        suffix_len = remain - prefix_len
        if len(ch) == 1:
            prefix = ch * prefix_len
            suffix = ch * suffix_len
        else:
            prefix = ch * (prefix_len/len(ch)) + ch[:prefix_len%len(ch)]
            suffix = ch * (suffix_len/len(ch)) + ch[:suffix_len%len(ch)]
        return prefix + ' ' + text + ' ' + suffix

# Recipe: text_escape (0.1)
def _escaped_text_from_text(text, escapes="eol"):
    r"""Return escaped version of text.

        "escapes" is either a mapping of chars in the source text to
            replacement text for each such char or one of a set of
            strings identifying a particular escape style:
                eol
                    replace EOL chars with '\r' and '\n', maintain the actual
                    EOLs though too
                whitespace
                    replace EOL chars as above, tabs with '\t' and spaces
                    with periods ('.')
                eol-one-line
                    replace EOL chars with '\r' and '\n'
                whitespace-one-line
                    replace EOL chars as above, tabs with '\t' and spaces
                    with periods ('.')
    """
    #TODO:
    # - Add 'c-string' style.
    # - Add _escaped_html_from_text() with a similar call sig.
    import re

    if isinstance(escapes, basestring):
        if escapes == "eol":
            escapes = {'\r\n': "\\r\\n\r\n", '\n': "\\n\n", '\r': "\\r\r"}
        elif escapes == "whitespace":
            escapes = {'\r\n': "\\r\\n\r\n", '\n': "\\n\n", '\r': "\\r\r",
                       '\t': "\\t", ' ': "."}
        elif escapes == "eol-one-line":
            escapes = {'\n': "\\n", '\r': "\\r"}
        elif escapes == "whitespace-one-line":
            escapes = {'\n': "\\n", '\r': "\\r", '\t': "\\t", ' ': '.'}
        else:
            raise ValueError("unknown text escape style: %r" % escapes)

    # Sort longer replacements first to allow, e.g. '\r\n' to beat '\r' and
    # '\n'.
    escapes_keys = escapes.keys()
    escapes_keys.sort(key=lambda a: len(a), reverse=True)
    def repl(match):
        val = escapes[match.group(0)]
        return val
    escaped = re.sub("(%s)" % '|'.join([re.escape(k) for k in escapes_keys]),
                     repl,
                     text)

    return escaped

def _one_line_summary_from_text(text, length=78,
        escapes={'\n':"\\n", '\r':"\\r", '\t':"\\t"}):
    r"""Summarize the given text with one line of the given length.

        "text" is the text to summarize
        "length" (default 78) is the max length for the summary
        "escapes" is a mapping of chars in the source text to
            replacement text for each such char. By default '\r', '\n'
            and '\t' are escaped with their '\'-escaped repr.
    """
    if len(text) > length:
        head = text[:length-3]
    else:
        head = text
    escaped = _escaped_text_from_text(head, escapes)
    if len(text) > length:
        summary = escaped[:length-3] + "..."
    else:
        summary = escaped
    return summary

# Recipe: query_yes_no (1.0)
def _query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes":"yes",   "y":"yes",  "ye":"yes",
             "no":"no",     "n":"no"}
    if default == None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while 1:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return default
        elif choice in valid.keys():
            return valid[choice]
        else:
            sys.stdout.write("Please repond with 'yes' or 'no' "\
                             "(or 'y' or 'n').\n")

# Recipe: pretty_logging (0.1) in C:\trentm\tm\recipes\cookbook
class _PerLevelFormatter(logging.Formatter):
    """Allow multiple format string -- depending on the log level.

    A "fmtFromLevel" optional arg is added to the constructor. It can be
    a dictionary mapping a log record level to a format string. The
    usual "fmt" argument acts as the default.
    """
    def __init__(self, fmt=None, datefmt=None, fmtFromLevel=None):
        logging.Formatter.__init__(self, fmt, datefmt)
        if fmtFromLevel is None:
            self.fmtFromLevel = {}
        else:
            self.fmtFromLevel = fmtFromLevel
    def format(self, record):
        record.lowerlevelname = record.levelname.lower()
        if record.levelno in self.fmtFromLevel:
            #XXX This is a non-threadsafe HACK. Really the base Formatter
            #    class should provide a hook accessor for the _fmt
            #    attribute. *Could* add a lock guard here (overkill?).
            _saved_fmt = self._fmt
            self._fmt = self.fmtFromLevel[record.levelno]
            try:
                return logging.Formatter.format(self, record)
            finally:
                self._fmt = _saved_fmt
        else:
            return logging.Formatter.format(self, record)

def _setup_logging(stream=None):
    """Do logging setup:

    We want a prettier default format:
        $name: level: ...
    Spacing. Lower case. Drop the prefix for INFO-level.
    """
    hdlr = logging.StreamHandler(stream)
    fmtr = _PerLevelFormatter(fmt="%(levelname)s: %(message)s",
                              fmtFromLevel={logging.INFO: "%(message)s"})
    hdlr.setFormatter(fmtr)
    logging.root.addHandler(hdlr)

#--- entry point

if __name__ == "__main__":
    _setup_logging(stream=sys.stdout)
    try:
        retval = main()
    except SystemExit:
        pass
    except KeyboardInterrupt:
        sys.exit(1)
    except IntegrationError as ex:
        log.error(ex)
        sys.exit(1)
    except:
        if log.isEnabledFor(logging.DEBUG):
            import traceback
            traceback.print_exc()
        else:
            exc_type, exc_value = sys.exc_info()[:2]
            if hasattr(exc_type, "__name__"):
                log.error(exc_value)
            else:  # string exception
                log.error(exc_type)
        sys.exit(1)
    else:
        sys.exit(retval)

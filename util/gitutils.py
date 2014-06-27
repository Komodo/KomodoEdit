def _capture_stdout(argv, ignore_retval=False, cwd=None, env=None):
    # Only available on python 2.4 and above
    import subprocess
    p = subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE, env=env)
    stdout = p.stdout.read()
    retval = p.wait()
    if retval and not ignore_retval:
        raise RuntimeError("error running '%s'" % ' '.join(argv))
    return stdout

def _last_svn_commit():
    # Find the last known commit that was imported from svn
    cmd = ["git", "log", "--all", "-1", "--grep=git-svn-id:",
           "--date-order", "--pretty=%ci%n%b"]
    last_svn_commit = _capture_stdout(cmd).splitlines(False)
    last_svn_date = last_svn_commit.pop(0)
    for line in reversed(last_svn_commit):
        if line.startswith("git-svn-id:"):
            last_svn_rev = int(line.split("@", 1)[-1].split()[0])
            return last_svn_rev, last_svn_date
    raise RuntimeError("Failed to find last svn revision id")

def buildnum_from_revision(revision=None):
    """Get the Komodo build number for the given revision (or HEAD)"""
    if revision is None:
        revision = "--all"
    # count the number of commits since the last known svn commit
    last_svn_rev, last_svn_date = _last_svn_commit()
    cmd = ["git", "rev-list", "--since=" + last_svn_date, revision]
    git_revisions = _capture_stdout(cmd)
    return git_revisions.count('\n') + last_svn_rev

def revision_from_buildnum(buildnum):
    """Return the git revision for the given Komodo build number"""
    # count the number of commits since the last known svn commit
    last_svn_rev, last_svn_date = _last_svn_commit()
    cmd = ["git", "rev-list", "--all", "--since=" + last_svn_date]
    git_revisions = _capture_stdout(cmd).splitlines()
    git_index = len(git_revisions) - (buildnum - last_svn_rev)
    return git_revisions[git_index]

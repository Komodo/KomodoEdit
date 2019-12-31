from __future__ import print_function
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
    # We have to use "http://svn.openkomodo.com/" in order to skip ko-integrated
    # code from the Komodo IDE repository!
    cmd = ["git", "log", "--all", "-1", "--grep=git-svn-id: http://svn.openkomodo.com/",
           "--date-order", "--pretty=%ci%n%b"]
    last_svn_commit = _capture_stdout(cmd).splitlines(False)
    last_svn_date = last_svn_commit.pop(0)
    for line in reversed(last_svn_commit):
        if line.startswith("git-svn-id:"):
            last_svn_rev = int(line.split("@", 1)[-1].split()[0])
            return last_svn_rev, last_svn_date
    raise RuntimeError("Failed to find last svn revision id")

def _get_current_revision():
    cmd = ["git", "rev-parse", "HEAD"]
    return _capture_stdout(cmd)[:-1] #trim newline char from end of output

def buildnum_from_revision(revision=None):
    """Get the Komodo build number for the given revision (or HEAD)"""
    if revision is None:
        revision = _get_current_revision()
    # count the number of commits since the last known svn commit
    last_svn_rev, last_svn_date = _last_svn_commit()
    cmd = ["git", "rev-list", "--since=" + last_svn_date, revision]
    git_revisions = _capture_stdout(cmd)
    # because of how this was originally implemented it's been providing the
    # wrong build number which ended up in incorrect build numbers.
    # Fixing the issue results in a much lower build number.  To keep public
    # builds consistent we have to add an appropriate offset.
    import black
    offset = 0
    productType = black.configure.items["productType"].Get()
    if "ide" in productType.lower() :
        offset = 105
    elif "edit" in productType.lower():
        offset = 89
    else:
        offset = 105
        import sys
        for arg in sys.argv[1:]:
            if arg.startswith("--product-type="):
                if "edit" in arg.lower():
                    offset = 89
    return git_revisions.count('\n') + last_svn_rev + offset

def revision_from_buildnum(buildnum):
    """Return the git revision for the given Komodo build number"""
    # count the number of commits since the last known svn commit
    last_svn_rev, last_svn_date = _last_svn_commit()
    cmd = ["git", "rev-list", "--all", "--since=" + last_svn_date]
    git_revisions = _capture_stdout(cmd).splitlines()
    git_index = len(git_revisions) - (int(buildnum) - int(last_svn_rev))
    return git_revisions[git_index]

if __name__ == '__main__':
    import sys
    def usage():
        print("Usage: gitutils REVISION (where REVISION is a svn or git revision)")
        sys.exit(1)
    if len(sys.argv) != 2:
        usage()
    revision = sys.argv[1]
    if len(revision) > 10:
        # Git sha1
        print("buildnum: %s" % (buildnum_from_revision(revision)))
    else:
        gitrev = revision_from_buildnum(revision)
        print("git rev: %s" % (gitrev, ))
        print("https://github.com/Komodo/KomodoEdit/commit/%s" % (gitrev, ))

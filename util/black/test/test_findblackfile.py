# This will test the mechanisms by which a Blackfile.py is found.
#

import os, sys, tempfile, re

#---- utility routines

bkLine2Re = re.compile("Development shell for project in '(?P<dirname>.*)'")
def WhichBlackfileIsSelected(bkLines):
    """return the full path to the Blackfile that "bk" now selects"""
    bkMatch = bkLine2Re.search(bkLines[1])
    if bkMatch:
        return os.path.join(bkMatch.group("dirname"), "Blackfile.py")
    else:
        return None


#--- test mainline
# setup:
#       <tmp>/<fallback>/Blackfile.py
#       <tmp>/<root>/Blackfile.py
#       <tmp>/<root>/<sub>
tmpDir = tempfile.mktemp()
os.mkdir(tmpDir)

fallbackTmpDir = os.path.join(tmpDir, "fallback")
fallbackBlackfile = os.path.join(fallbackTmpDir, "Blackfile.py")
os.mkdir(fallbackTmpDir)
open(fallbackBlackfile, "w").close()

rootTmpDir = os.path.join(tmpDir, "root")
rootBlackfile = os.path.join(rootTmpDir, "Blackfile.py")
os.mkdir(rootTmpDir)
open(rootBlackfile, "w").close()

subTmpDir = os.path.join(rootTmpDir, "sub")
os.mkdir(subTmpDir)

startDir = os.getcwd()


# a Blackfile specified via "-f <blackfile>"
lines = os.popen("bk -f %s" % rootBlackfile).readlines()
assert WhichBlackfileIsSelected(lines) == rootBlackfile

# a Blackfile in the current directory (with BLACKFILE_FALLBACK not defined)
if os.environ.has_key("BLACKFILE_FALLBACK"):
    os.environ["BLACKFILE_FALLBACK"] = ""
os.chdir(rootTmpDir)
lines = os.popen("bk").readlines()
assert WhichBlackfileIsSelected(lines) == rootBlackfile

# a Blackfile in the current directory (with BLACKFILE_FALLBACK defined)
os.environ["BLACKFILE_FALLBACK"] = fallbackBlackfile
os.chdir(rootTmpDir)
lines = os.popen("bk").readlines()
assert WhichBlackfileIsSelected(lines) == rootBlackfile

# a Blackfile in an ancestral directory (with BLACKFILE_FALLBACK not defined)
if os.environ.has_key("BLACKFILE_FALLBACK"):
    os.environ["BLACKFILE_FALLBACK"] = ""
os.chdir(subTmpDir)
lines = os.popen("bk").readlines()
assert WhichBlackfileIsSelected(lines) == rootBlackfile

# a Blackfile in an ancestral directory (with BLACKFILE_FALLBACK defined)
os.environ["BLACKFILE_FALLBACK"] = fallbackBlackfile
os.chdir(subTmpDir)
lines = os.popen("bk").readlines()
assert WhichBlackfileIsSelected(lines) == rootBlackfile


# no ancestral Blackfile (with BLACKFILE_FALLBACK not defined)
if os.environ.has_key("BLACKFILE_FALLBACK"):
    os.environ["BLACKFILE_FALLBACK"] = ""
if sys.platform.startswith("win"):
    os.chdir("C:\\")
else:
    os.chdir("/")
lines = os.popen("bk").readlines()
blackfile = WhichBlackfileIsSelected(lines)
assert blackfile == None, "blackfile '%s' is not None" % blackfile

# no ancestral Blackfile (with BLACKFILE_FALLBACK defined)
os.environ["BLACKFILE_FALLBACK"] = fallbackBlackfile
if sys.platform.startswith("win"):
    os.chdir("C:\\")
else:
    os.chdir("/")
lines = os.popen("bk").readlines()
assert WhichBlackfileIsSelected(lines) == fallbackBlackfile


# clean up
os.chdir(startDir)
os.rmdir(subTmpDir)
os.unlink(rootBlackfile)
os.unlink(rootBlackfile+"c")  # the .pyc
os.rmdir(rootTmpDir)
os.unlink(fallbackBlackfile)
os.unlink(fallbackBlackfile+"c") # the .pyc
os.rmdir(fallbackTmpDir)
os.rmdir(tmpDir)


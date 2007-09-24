# A trivial Python script to serve as a reasonable sample for discussing
# and designing the Code Intelligence autocomplete and calltip support.

import os, sys
from urllib import urlopen
from urlparse import urlparse as myurlparse
if sys.platform.startswith("win"):
    import win32api
from os.path import *

try:
    import logging
except ImportError:
    url = "http://www.red-dove.com/python_logging.html#download"
    sys.stderr.write("error: could not import 'logging': you must get this "
                     "package from here: %s\n" % url)
    sys.exit(1)


log = logging.getLogger("websave")


class WebSaveError(Exception):
    pass

def websave(url):
    """Save the given URL to the HOME/My Documents directory.
    
        "url" (string) is the URL to download
    """
    content = urlopen(url).read()
    if sys.platform.startswith("win"):
        # Note: intentionally haven't imported win32con.
        saveDir = win32api.GetSpecialFolder(win32con.CLSID_MYDOCS)
    else:
        saveDir = os.environ["HOME"]
    urlpath = myurlparse(url)[2]
    localFile = os.path.join(saveDir, os.path.basename(urlpath))
    open(localFile, "w").write(content)
    return 1

if name == "__main__":
    for url in sys.argv[1:]:
        websave(url)

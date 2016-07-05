#!python
# Copyright (c) 2000-2011 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# Simple Django syntax checker
# args: pathname djangoProjectPath
# returns: 0 or 1
# writes error messages to stderr

import os, sys
# django.template.loader isn't used here, but loading it triggers
# essential side-effects that initialize the parser.

from django.template import loader, Template, TemplateSyntaxError

def loadTemplate(pathname):
    f = open(pathname)
    try:
        s = f.read()
    finally:
        f.close()
    try:
        t = Template(s)
    except TemplateSyntaxError as ex:
        sys.stderr.write("TemplateSyntaxError: %s\n" % ex[0])
        return 1
    except Exception as ex:
        sys.stderr.write("Unexpected error: %s\n" % ex[0])
    return 0

def main(argv):
    pathname, projectPath = argv[1:3]
    if os.path.dirname(projectPath):
        # When Komodo tries to auto-find a "project/settings.py", it will pass
        # the full directory path of "project". Add it to PYTHONPATH such that
        # when Django tries to do something like "import project.settings", it
        # will behave as expected.
        sys.path.insert(0, os.path.dirname(projectPath))
        sys.path.insert(0, projectPath)
    os.environ["DJANGO_SETTINGS_MODULE"] = os.path.basename(projectPath)
    return loadTemplate(pathname)
    
if __name__ == "__main__":
    sys.exit(main(sys.argv))

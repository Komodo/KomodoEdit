"""

This file creates an HTML file which is embedded in an iframe by iconpicker.xul.

It is invoked by the Conscript file in this directory.  It takes two
arguments: the first is the name of the file to write to.  The second
is the relative path to the directory where the icons are stored.

Example command line:

  python mkiconlist.py content/crystal.html skin/icons

"""

header = """<html>
<body>
<style>img:hover { border-color: black; }</style>
<style>img { border-color: white; }</style>
"""

footer = """</body>
</html>"""

imgtemplate = """
<img border="1"
     ondblclick="parent.ValidatedPickIcon('chrome://crystal/skin/icons/%(fname)s');"
     onclick="parent.Pick_Icon('chrome://crystal/skin/icons/%(fname)s');"
     src="chrome://crystal/skin/icons/%(fname)s"
     alt="%(fname)s"
     title="%(fname)s"
     style="padding: 4px;"/>
"""

import sys, os
print sys.argv
target = sys.argv[1]
fp = open(target, 'w')
where = os.path.dirname(target)
here = os.getcwd()
content = []
extensions = ['.png', '.gif']
try:
    #os.chdir(where)
    #print os.getcwd()
    fp.write(header)
    icons = os.path.normpath(os.path.join(os.getcwd(), sys.argv[2]))
    print "icons are in ",icons
    for f in sorted(os.listdir(icons)):
        extension = os.path.splitext(f)[-1].lower()
        if extension in extensions:
            content.append(imgtemplate % {'fname': f})
    fp.write('\n'.join(content))
    fp.write(footer)
finally:
    os.chdir(here)

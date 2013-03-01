"""

This file creates an HTML file which is embedded in an iframe by iconpicker.xul.

This was originally done as dynamically created content, but
JavaScript security made it impossible for that to work in installer
builds (for some strange reason it worked in dev builds.

It is invoked by the Conscript file in this directory.  It takes two
arguments: the first is the name of the file to write to.  The second
is the relative path to the directory where the icons are stored.

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
     ondblclick="parent.ValidatedPickIcon('chrome://icomoon/%(fname)s');"
     onclick="parent.Pick_Icon('chrome://icomoon/%(fname)s');"
     src="chrome://icomoon/%(fname)s"
     alt="%(basename)s"
     style="padding: 4px;"/>
"""

import sys, os, zipfile
here = os.getcwd()
target = here + os.path.sep + 'icomoon.html'
fp = open(target, 'w')
where = os.path.dirname(target)
content = []
extensions = ['.png', '.gif']
try:
    os.chdir(where)
    print os.getcwd()
    fp.write(header)
    zip = zipfile.ZipFile(here + os.path.sep + "../../chrome/iconsets/dark/dark.jar")
    zipFiles = zip.namelist()
    for f in sorted(zipFiles):
        extension = os.path.splitext(f)[-1].lower()
        if extension in extensions:
            content.append(imgtemplate % {'fname': f, 'basename': os.path.basename(f)})
    fp.write('\n'.join(content))
    fp.write(footer)
finally:
    os.chdir(here)

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
<style>
img { padding: 4px; }
img.hide { display: none; }
</style>
"""

footer = """</body>
</html>"""

imgtemplate = """
<img ondblclick="parent.ValidatedPickIcon('koicon://ko-svg/chrome/fontawesome/skin/%(fname)s');"
     onclick="parent.Pick_Icon('koicon://ko-svg/chrome/fontawesome/skin/%(fname)s');"
     src="koicon://ko-svg/chrome/fontawesome/skin/%(fname)s"
     alt="%(basename)s" />
"""

import sys, os
here = os.getcwd()
target = here + os.path.sep + 'fontawesome.html'
fp = open(target, 'w')
where = os.path.dirname(target)
content = []
extensions = ['.svg']
try:
    fp.write(header)
    os.chdir(where)
    path = here + os.path.sep + "../../modules/fontawesome/content/"
    for f in os.listdir(path):
        extension = os.path.splitext(f)[-1].lower()
        if extension in extensions:
            content.append(imgtemplate % {'fname': f, 'basename': os.path.splitext(f)[0]})
    fp.write('\n'.join(content))
    fp.write(footer)
finally:
    os.chdir(here)

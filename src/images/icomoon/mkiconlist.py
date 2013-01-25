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
<style>
img {
    border-color: white;
}
</style>
<ul>
"""

footer = """</ul></body>
</html>"""

imgtemplate = """
<img border="1" width="16"
     ondblclick="parent.ValidatedPickIcon('chrome://icomoon/skin/icons/svg/%(fname)s');"
     onclick="parent.Pick_Icon('chrome://icomoon/skin/icons/svg/%(fname)s');"
     src="chrome://icomoon/skin/icons/svg/%(fname)s"
     alt="%(fname)s"
     style="padding: 4px;"/>
"""

import sys, os, re
print sys.argv
target = sys.argv[1]
fp = open(target, 'w')
where = os.path.dirname(target)
here = os.getcwd()
content = []
extensions = ['.svg']
try:
    #os.chdir(where)
    #print os.getcwd()
    fp.write(header)
    icons = os.path.normpath(os.path.join(os.getcwd(), sys.argv[2]))
    os.chdir(icons)
    print "icons are in ",icons
    for fname in sorted(os.listdir(icons)):
        extension = os.path.splitext(fname)[-1].lower()
        if extension in extensions:
            content.append(imgtemplate % {'fname': fname})
            
            file = open(fname)
            fileContents = file.read()
            file.close()
            
            fileContents = re.sub("<g.*?</g>", "", fileContents)
            file = open(fname, "w")
            file.write(fileContents)
            file.close()
            
    fp.write('\n'.join(content))
    fp.write(footer)
finally:
    os.chdir(here)

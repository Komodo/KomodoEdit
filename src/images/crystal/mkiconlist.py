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
<style>
img { padding: 4px; }
img.hide { display: none; }</style>
<script>
function ValidatedPickIcon(imgElement) {
    parent.ValidatedPickIcon(imgElement.getAttribute('src'));
}
function PickIcon(imgElement) {
    parent.Pick_Icon(imgElement.getAttribute('src'));
}
</script>
"""

footer = """</body>
</html>"""

imgtemplate = """
<img ondblclick="ValidatedPickIcon(this);" onclick="PickIcon(this);"
     src="chrome://crystal/skin/icons/%(fname)s"/>"""

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

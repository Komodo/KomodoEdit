#!python
#
# Change all GUIDs in the give files.
# 
# Note: WiX (MSI?) requires uppercase A-F hex letters.
#

import os
import sys
import re
from os.path import exists
import shutil

def new_guid():
    import pythoncom
    guid = str(pythoncom.CreateGuid())
    guid = guid[1:-1] # strip of the {}'s
    return guid


def main():
    for filepath in sys.argv[1:]:
        print "changing GUIDs in '%s':" % filepath

        fin = open(filepath, 'r')
        original = content = fin.read()
        fin.close()
        # E.g.: Guid="32A46AA4-051B-4574-A6B2-E7B3C7666CB6"
        pattern = re.compile('Guid="([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})"')
        for match in pattern.finditer(content):
            start, end = match.start(1), match.end(1)
            guid = new_guid()
            assert (end-start) == len(guid)
            print "  s/%s/%s/" % (content[start:end], guid)
            content = content[:start] + guid + content[end:]

        if content == original:
            print "  no changes, leaving alone"
        else:
            bakpath = filepath+".bak"
            print "  backing up original to '%s'" % bakpath
            if exists(bakpath):
                os.chmod(bakpath, 0777)
                os.remove(bakpath)
            shutil.copy2(filepath, bakpath)

            try:
                fout = open(filepath, 'w')
            except EnvironmentError, ex:
                print "  p4 edit %s" % filepath
                os.system("p4 edit %s" % filepath)
                fout = open(filepath, 'w')
            fout.write(content)
            fout.close()

main()    


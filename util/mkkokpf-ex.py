# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

"""Only run this script with from the Komodo build directory!

Documentation may or may not happen one day.
"""

import sys
import os
import os.path
import copy
import string

projects = [ {'directory' : 'src/editor'},
             {'directory' : 'src/help'},
             {'directory' : 'src/components'},
             {'directory' : 'src/languages'},
             {'directory' : 'src/lint'},
             {'directory' : 'src/prefs'},

             {'directory' : 'src/chrome/komodo/content/editor', 'name' : 'chrome-editor.kpf' },
             {'directory' : 'src/chrome/komodo/content/debugger', 'name' : 'chrome-debugger.kpf' }
             ]
projectPrefix = '''<project name="%s">
<files>'''

projectPostfix = '''</files>
</project>
'''

def buildProject(targetDirectory, directory, name = None, extensions=['.js', '.idl', '.py', '.xml'], names=['Conscript']):
    def fileSorter(a,b):
        if a.startswith('ko'):
            a = a[2:]
            if a.startswith('I'):
                a = a[1:]
        if b.startswith('ko'):
            b = b[2:]
            if b.startswith('I'):
                b = b[1:]

        return cmp(a,b)

    allFiles = os.listdir(directory)
    files = []
 
    for file in allFiles:
        basename, extension = os.path.splitext(file)
        if os.path.isfile(os.path.join(directory, file)) and (extension in extensions or basename in names):
            files.append(file)

    if name is None:
        name = apply(os.path.split,(directory,))[-1] + '.kpf'

    files.sort(fileSorter)
    
    print 'Creating project "%s"' % name
    projectFile = open(os.path.join(targetDirectory, name), 'w+')
    projectFile.write(projectPrefix % name)

    for file in files:
        print '\tadding "%s"' % file
        projectFile.write('<file url="file:///%s"/>\n' % os.path.abspath(os.path.join(directory,file)).replace('\\','/'))

    projectFile.write(projectPostfix)    

def buildProjects(rootDirectory):
    # Create a "projects" directory if it doesn't already exist
    targetDirectory = os.path.join(rootDirectory, 'projects')
    if not os.path.exists(targetDirectory):
        os.mkdir(targetDirectory)
        
    for project in projects:
        project = copy.deepcopy(project)
        project['directory'] = apply(os.path.join, [rootDirectory] + project['directory'].split('/'))
        project.update({'targetDirectory' : targetDirectory})
        apply(buildProject,(),project)
        
buildProjects('..\\')
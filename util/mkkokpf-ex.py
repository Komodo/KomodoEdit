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
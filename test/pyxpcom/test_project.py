# Copyright (c) 2000-2007 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Test Project functionality in Komodo."""
#TODO:
#   - This test does not clean up after itself. It leave 'test*.kpf'
#     turds. It should clean up.

import os
import sys
import unittest

try:
    from xpcom import components, ServerException, COMException, nsError
    from xpcom.server import WrapObject, UnwrapObject
    import uriparse
except ImportError:
    pass # Allow testing without PyXPCOM to proceed.


class ProjectTestCase(unittest.TestCase):
    __tags__ = ["knownfailure"]

    def setUp(self):
        initSvc = components.classes["@activestate.com/koInitService;1"] \
                      .getService(components.interfaces.koIInitService)
        initSvc.setEncoding()

    def _setupProject(self, name):
        project = components.classes["@activestate.com/koProject;1"] \
                      .createInstance(components.interfaces.koIProject)
        testkpfcontents = """<project><files><file url="test.txt"></file>
        <file url="test2.txt"></file></files></project>"""
        open(name, 'w').write(testkpfcontents)
        return project

    def test_dirty(self):
        name = 'test.kpf'
        project = self._setupProject(name)
        dirname, basename = os.path.split(name)
        basename = os.path.splitext(basename)[0]    
        project.load(uriparse.localPathToURI((os.path.abspath(name))));
        assert project.isDirty
        project.save()
        assert not project.isDirty
        folder = components.classes["@activestate.com/koPart?type=folder;1"] \
                      .createInstance(components.interfaces.koIPart_folder)
        project.addChild(folder)
        assert project.isDirty

    def test_read(self):
        verbose = 0
        name = 'test.kpf'
        project = self._setupProject(name)
        dirname, basename = os.path.split(name)
        basename = os.path.splitext(basename)[0]    
        project.load(uriparse.localPathToURI((os.path.abspath(name))));
        if verbose:
            project.dump(0)
            print project.getChildren(), len(project.getChildren())
        self.failUnless(len(project.getChildren()) == 2, "didn't read the right number of children")
        project.prefset.setStringPref('pref1', u'valueofpref1')
        assert project.prefset.getStringPref('pref1') == u'valueofpref1'
        project.name = project.name + '2'
        self.failUnlessEqual(project.name, "test2")
        project.save()
        
        project = components.classes["@activestate.com/koProject;1"] \
                      .createInstance(components.interfaces.koIProject)
        name = 'test2.kpf'
        project.load(uriparse.localPathToURI((os.path.abspath(name))));
        if verbose:
            project.dump(0)
            project.prefset.dump(0)
            print "Project %s has %d children" % (name, len(project.getChildren()))
        assert project.prefset.getStringPref('pref1') == u'valueofpref1'
        project.prefset.deletePref('pref1')
        file1 = project.getChildren()[0]
        if verbose:
            file1.dump(0)
        fileprefs = components.classes["@activestate.com/koPreferenceSet;1"] \
                      .createInstance(components.interfaces.koIPreferenceSet)
        fileprefs.setStringPref("foo", "bar")
        file1.prefset = fileprefs
        project.name = project.name[:-1] + '3'
        if verbose:
            project.dump(0)
        project.save()
        
        project = components.classes["@activestate.com/koProject;1"] \
                      .createInstance(components.interfaces.koIProject)
        name = 'test3.kpf'
        project.load(uriparse.localPathToURI((os.path.abspath(name))));
        file1 = project.getChildren()[0]
        assert file1.prefset.getStringPref('foo') == 'bar'
        # check that we can add children
        newfile = components.classes["@activestate.com/koPart;1"] \
                      .createInstance(components.interfaces.koIPart)
        newfile.type = 'file'
        newfile.setStringAttribute('url', 'foo')
        project.addChild(newfile)
        assert 3 == len(project.getChildren())
        # check that reverts do revert
        project.revert()
        assert 2 == len(project.getChildren())
        
        assert not project.isDirty
        project.name = 'foo'
        assert project.isDirty
        project.revert()
        assert not project.isDirty

        assert project.hasAttribute('kpf_version')
        assert not project.hasAttribute('foobar')

        #print '-'*70
        #print type(project)
        #print project
        #project.importFromDisk(r'd:\test', '*.py;*.idl', '*.tmp', 1, 1, 1)
        #project.dump(0)
        #print '1'*70
        #project.revert()
        #project.importFromDisk(r'd:\test', '*.py;*.idl', '*.tmp', 1, 1, 0)
        #project.dump(0)
        #print '2'*70
        #project.revert()
        #project.importFromDisk(r'd:\test', '', '', 1, 1, 0) 
        #project.dump(0)
        #print '3'*70
        #project.revert()
        #project.importFromDisk(r'd:\test', '*.py;*.idl', '*.tmp', 1, 0, 0)
        #project.dump(0)
        #print '4'*70
        #project.revert()
    
    def test_package(self):
        packageDir = os.path.join(os.getcwd(),'tmp')
        packageName = 'test'
        packagePath = os.path.join(packageDir,packageName+'.kpz')
        if not os.path.exists(packageDir):
            os.makedirs(packageDir)
        packager = components.classes["@activestate.com/koProjectPackageService;1"] \
                      .getService(components.interfaces.koIProjectPackageService)
        packager = UnwrapObject(packager)
        #packager.debug = 1
        project = components.classes["@activestate.com/koProject;1"] \
                      .createInstance(components.interfaces.koIProject)
        uri = uriparse.localPathToURI(os.path.join(os.getcwd(),'install','release','INSTALLDIR','samples','sample_test.kpf'))
        #uri = uriparse.localPathToURI(os.path.join(os.getcwd(),'install','release','INSTALLDIR','samples','toolbox.kpf'))
        project.load(uri)
        packager.packageProject(packagePath, project)
        assert os.path.exists(packagePath)
        packager.extractPackage(packagePath, packageDir)
        assert os.path.exists(os.path.join(packageDir,packageName,packageName+'.kpf'))
        
        otherproject = components.classes["@activestate.com/koProject;1"] \
                      .createInstance(components.interfaces.koIProject)
        packager.importPackage(packagePath, packageDir, otherproject)
        assert len(project.getChildren()) == len(otherproject.getChildren())



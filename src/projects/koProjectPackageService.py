#!/usr/bin/env python
from xpcom import components, ServerException, COMException, nsError
from xpcom.server import WrapObject, UnwrapObject

import os, re
import uriparse
import koToolbox2

import logging
log = logging.getLogger("koProjectPackageService")

class koProjectPackageService:
    _com_interfaces_ = [components.interfaces.koIProjectPackageService]
    _reg_desc_ = "Komodo Packaging Service Component"
    _reg_contractid_ = "@activestate.com/koProjectPackageService;1"
    _reg_clsid_ = "{16237ba5-3d97-475b-ad22-fa60b2cd3a33}"

    def __init__(self):
        self.verbose = False
        self.percent = 10
        self.debug = 0
        self.test = 0
        self.lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
            .getService(components.interfaces.koILastErrorService)
        self.fileSvc = components.classes["@activestate.com/koFileService;1"]\
            .getService(components.interfaces.koIFileService)

    def _gatherIcons(self, part):
        icons = []
        self._gatherIconsAux(part, icons)
        return icons

    def _gatherIconsAux(self, part, icons):
        part = UnwrapObject(part)
        icon = part.get_iconurl()
        if self.test:
            print "icon [%s]"%icon
        if not icon.startswith(('chrome://', 'moz-icon://stock/')):
            newicon = os.path.join('.icons', os.path.basename(icon))
            part.set_iconurl(newicon)
            icons.append((uriparse.URIToLocalPath(icon),newicon))
        if hasattr(part, 'getChildren'):
            for p in part.getChildren():
                self._gatherIconsAux(p, icons)

    def _gatherLiveFileUrls(self, part, relativeDir, extradir):
        #_getImportConfig(self, recursive=0, type="makeFlat")
        if not part.live:
            return []
        config = part._getImportConfig(recursive=1, type="useFolders")
        include = config[0]
        exclude = config[1]
        recursive = config[2]
        type = config[3]
        path = config[4]
        if not path:
            return []

        importService = components.classes["@activestate.com/koFileImportingService;1"].\
                        getService(components.interfaces.koIFileImportingService)
        filenames = set(importService.findCandidateFiles(part, path, include, exclude, recursive))
        flist = []
        for name in filenames:
            diskfile = os.path.abspath(name)
            if not os.path.isfile(diskfile): continue
            url = uriparse.localPathToURI(diskfile)
            dest = uriparse.RelativizeURL(relativeDir, url)
            if extradir:
                dest = os.path.join(extradir, dest)
            flist.append((diskfile, dest))
        return flist
            
    def packageProject(self, packagePath, project, overwrite):
        try:
            if project.isDirty:
                err = 'Save project before packaging'
                self.lastErrorSvc.setLastError(1, err)
                raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, err)
            project = UnwrapObject(project)
            self._packageParts(packagePath, orig_project=project,
                               live=project.live, extradir=0,
                               overwrite=overwrite)
        except Exception, e:
            log.exception(e)

    def _clonePartList(self, newproject, partList):
        # clone parts and add them to the project
        for part in partList:
            part = UnwrapObject(part)
            if part.type == 'project':
                self._clonePartList(newproject, part.children)
            else:
                newpart = part.copyToProject(newproject)
                newproject.addChild(newpart)

    def packageParts(self, packagePath, partList, overwrite):
        try:
            self._packageParts(packagePath, partList=partList, overwrite=overwrite)
        except:
            log.exception("packageParts failed")

    # a list of parts instead of project
    def _packageParts(self, packagePath, partList=None, orig_project=None,
                            live=0, extradir=1, overwrite=0):
        # setup a temporary project file, as we may need to do modifications
        # that shoule only be in the packaged version
        if packagePath.find('.kpz') == -1:
            zipfilename = packagePath+'.kpz'
        else:
            zipfilename = packagePath
        if self.debug:
            print "zipfilename [%s]" % zipfilename
        if os.path.exists(zipfilename):
            if overwrite:
                os.unlink(zipfilename)
            else:
                err = 'A package with the same name already exists at that location.'
                self.lastErrorSvc.setLastError(1, err)
                raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, err)

        try:
            projectName = os.path.splitext(os.path.basename(packagePath))[0]
            if orig_project:
                newproject = orig_project.clone()
            else:
                newproject = UnwrapObject(components.classes["@activestate.com/koProject;1"]
                                          .createInstance(components.interfaces.koIProject))
                newproject.create()
            newproject.live = live
            newproject._url = os.path.join(os.path.dirname(zipfilename), 'package.kpf')
            tmp_project_localPath = uriparse.URIToLocalPath(newproject._url)
            newproject.name = projectName
            if self.debug:
                print "newproject._url [%s]" % newproject._url
            
            if partList:
                # clone parts and add them to the project
                self._clonePartList(newproject, partList)

            # figure out a base path for all the parts
            newproject._relativeBasedir = os.path.commonprefix(newproject._urlmap.keys())
            if not newproject._relativeBasedir:
                newproject._relativeBasedir = os.path.dirname(newproject._url)
            if self.debug:
                print "using relative base [%s]" % newproject._relativeBasedir

            import zipfile
            if not self.test:
                zf = zipfile.ZipFile(str(zipfilename), 'w')

            # look at all the url's in the project, copy files, remove parts, etc.
            # as necessary
            extraDirName = None
            if extradir:
                extraDirName = newproject.name
            fix_drive_re = re.compile(r'^(?:file:\/\/\/)?(?:(\w):)?(.*)$')
            flist = set()
            for source in newproject._urlmap:
                part = newproject._urlmap[source]
                
                # gather files from live folders
                if part.live and hasattr(part, 'refreshChildren'):
                    if newproject.live or part._parent.live: continue
                    flist = flist.union(self._gatherLiveFileUrls(part, newproject._relativeBasedir, extraDirName))
                    continue
                
                if 'url' in part._tmpAttributes and \
                   part._tmpAttributes['url'] == part._attributes['url']:
                    dest = part._tmpAttributes['relativeurl']
                else:
                    dest = uriparse.RelativizeURL(newproject._relativeBasedir, part._attributes['url'])
                diskfile = uriparse.URIToLocalPath(part._attributes['url'])
                # XXX FIXME this is *VERY HACKY*.  I've done a quick fix, but what the !?
                # we should never get a full path in dest, it should be relative
                if dest.find('file:')==0:
                    try:
                        dest = fix_drive_re.sub(r'\1\2',dest)
                    except Exception, e:
                        dest = fix_drive_re.sub(r'\2',dest)

                # we do not add directories
                if os.path.isfile(diskfile):
                    part._attributes['url'] = dest
                    if extraDirName:
                        dest = os.path.join(extraDirName, dest)
                    if self.debug:
                        print "diskfile [%r] dest[%r]" % (diskfile, dest)
                    flist.add((diskfile, dest))

                
            if orig_project:
                koProjectFile = orig_project.getFile()
                projectDirName = koProjectFile.dirName
                if koProjectFile.isLocal:
                    # For each file in
                    # .../.komodotools/D/f
                    # write out fullpath => .komodotools/D/f
                    ktools = koToolbox2.PROJECT_TARGET_DIRECTORY
                    toolboxPath = os.path.join(projectDirName, ktools)
                    if os.path.exists(toolboxPath):
                        self._archiveDir(zf, projectDirName, toolboxPath)

                    # Now write out any referenced local files and folders,
                    # but only if they're relative to the project's home.

                    pathPairs = [(uriparse.URIToLocalPath(x), x)
                                 for x in orig_project.getAllContainedURLs() 
                                 if x.startswith("file://")]
                    for p, url in pathPairs:
                        if os.path.isdir(p):
                            if p.startswith(projectDirName):
                                self._archiveDir(zf, projectDirName, p)
                            else:
                                self._archiveDirUnderBasename(zf, p)
                                part = newproject.getChildByURL(url)
                                part.url = UnwrapObject(part).name
                        elif os.path.isfile(p):
                            if p.startswith(projectDirName):
                                zf.write(p, p[len(projectDirName) + 1:])
                            else:
                                zf.write(p, os.path.basename(p))
                                part = newproject.getChildByURL(url)
                                part.url = UnwrapObject(part).get_name()

            # get a list of all the icons that are not in chrome so we can package
            # them
            iconlist = self._gatherIcons(newproject)
            for icondata in iconlist:
                source = icondata[0]
                if extraDirName:
                    dest = os.path.join(extraDirName, icondata[1])
                else:
                    dest = icondata[1]
                if self.debug:
                    print "icon diskfile [%r] dest[%r]" % (source,dest)
                if not self.test:
                    zf.write(str(source), str(dest))

            # save the temporary project file, add it to the zipfile, then delete it
            newproject.save()
            # save the new project
            if extraDirName:
                project_filename = os.path.join(extraDirName, os.path.basename(tmp_project_localPath))
            else:
                project_filename = os.path.basename(tmp_project_localPath)
            if self.debug:
                print "writing project to zip as [%r]" % project_filename
            if not self.test:
                zf.write(str(tmp_project_localPath), str(project_filename))
                zf.close()
        except Exception, e:
            log.exception(e)
            if os.path.exists(tmp_project_localPath):
                os.unlink(tmp_project_localPath)
            err = 'An error occurred while attempting to export the package:\n\n%s' % e
            self.lastErrorSvc.setLastError(1, err)
            raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, err)

        os.unlink(tmp_project_localPath)
        self.lastErrorSvc.setLastError(0, 'The package has been exported successfully to %s' % zipfilename)

    def _archiveDir(self, zf, projectDirName, srcPath):
        self._archiveDirWithRootLength(zf, srcPath, len(projectDirName) + 1)
               
    def _archiveDirUnderBasename(self, zf, srcDir):
        srcDirParent = os.path.dirname(srcDir)
        self._archiveDirWithRootLength(zf, srcDir, len(srcDirParent) + 1)
        
    def _archiveDirWithRootLength(self, zf, srcDir, srcRootLen):
        for root, dirs, files in os.walk(srcDir):
            if os.path.basename(root) == ".svn":
            # XXX Are there others that should be ignored?
                continue
            try:
                idx = dirs.index(".svn")
                del dirs[idx]
            except ValueError:
                # do nothing
                pass
            archive_root = os.path.abspath(root)[srcRootLen:]
            for f in files:
                fullpath = os.path.join(root, f)
                archive_name = os.path.join(archive_root, f)
                zf.write(fullpath, archive_name)

    def newProjectFromPackage(self, file, dir):
        return self._importPackage(file, dir, None)

    def importPackage(self, file, dir, part):
        self._importPackage(file, dir, part)

    def _importPackage(self, file, dir, part):
        from zipfile import BadZipfile
        isTempProjectFile = True
        try:
            packageDir, projectFile = self.extractPackage(file, dir)
        except BadZipfile, e:
            # The file may be a kpf already (not a kpz).
            projectFile = file
            isTempProjectFile = False
        except Exception, e:
            log.exception(e)
            packageDir = None
            projectFile = None
            raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, e)

        newproject = UnwrapObject(components.classes["@activestate.com/koProject;1"]
                                  .createInstance(components.interfaces.koIProject))
        newproject.create()
        newproject.loadQuiet(projectFile)
        if isTempProjectFile and os.path.exists(projectFile):
            os.unlink(projectFile)

        if not part:
            # we clone to update all the id's in the project
            return newproject.clone()

        for child in newproject.children:
            if child.get_name() == "package.kpf":
                # This is the internal kpz package name, we don't want to add
                # this.
                continue
            newchild = child.clone()
            if child._attributes.has_key('icon'):
                # cloned parts have a relative url here, fix it
                if newchild._attributes['icon'].find("://") == -1:
                    newchild._attributes['icon'] = uriparse.UnRelativizeURL(newproject._relativeBasedir, child._attributes['icon'])
            part.addChild(newchild)

        if not part.name:
            part.name = "Package %s" % projectName
        self.lastErrorSvc.setLastError(0, 'The package "%s" has been imported successfully.' % file)
        return None

    def extractPackage(self, file, dir):
        import zipfile
        if not dir.endswith(':') and not os.path.exists(dir):
            os.mkdir(dir)

        zf = zipfile.ZipFile(file)
        try:
            files = zf.namelist()
            # create directory structure to house files
            self._createstructure(file, dir)
    
            num_files = len(files)
            percent = self.percent
            divisions = 100 / percent
            perc = int(num_files / divisions)
    
            kpf = None
            basedir = os.path.dirname(os.path.join(dir, files[0]))
            # extract files to directory structure
            for name in files:
                if name.endswith('/'):
                    continue
                outfile = open(os.path.join(dir, name), 'wb')
                outfile.write(zf.read(name))
                outfile.flush()
                outfile.close()
                
                if not kpf and os.path.splitext(name)[1] == ".kpf":
                    kpf = os.path.join(dir, name)
                if os.path.basename(name) == "package.kpf":
                    kpf = os.path.join(dir, name)
        finally:
            zf.close()
        return basedir, kpf


    def _createstructure(self, file, dir):
        self._makedirs(self._listdirs(file), dir)


    def _makedirs(self, directories, basedir):
        """ Create any directories that don't currently exist """
        for dir in directories:
            curdir = os.path.join(basedir, dir)
            if not os.path.exists(curdir):
                os.makedirs(curdir)

    def _listdirs(self, file):
        """ Grabs all the directories in the zip structure
        This is necessary to create the structure before trying
        to extract the file to it. """
        import zipfile
        zf = zipfile.ZipFile(file)

        dirs = {}

        for name in zf.namelist():
            if name.endswith('/'):
                dirs[name] = 1
            else:
                dirs[os.path.dirname(name)] = 1

        dirs = dirs.keys()
        dirs.sort()
        return dirs



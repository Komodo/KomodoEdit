#!python
# Copyright (c) 2017-2017 ActiveState Software Inc.

"""Utils module for simple one-off services that don't really belong elsewhere"""

from xpcom.components import interfaces as Ci
from xpcom.components import classes as Cc
from xpcom import components
from xpcom.server import UnwrapObject

import logging
import threading
import zipfile
import shutil
import os

log = logging.getLogger("koutils")
#log.setLevel(10)

class koUtils:

    _com_interfaces_ = [Ci.koIUtils]
    _reg_desc_ = "Komodo Utils"
    _reg_clsid_ = "{043fbad0-861c-476a-a08a-1754004379f9}"
    _reg_contractid_ = "@activestate.com/koUtils;1"

    def unzip(self, path, subfolder, target, cb):
        """unzip give path to given target, specifying a subfolder will only extract
        files from that subfolder in the zip (if it exists)

        calls self._unzip in a thread
        """
        t = threading.Thread(target=self._unzip, args=(path, subfolder, target, cb),
                             name="Unzip operation")
        t.setDaemon(True)
        t.start()

    def _unzip(self, path, subfolder, target, cb):
        if not subfolder:
            filename = os.path.basename(path)
            subfolder = os.path.splitext(filename)[0]

        subfolder = "%s/" % subfolder

        extracted = False

        try:
            archive = zipfile.ZipFile(path)

            if subfolder:
                # if we are extracting from a subfolder we need to manually iterate
                # through the files and extract them as needed, as ZipFile.extractall
                # does not support this
                for item in (f for f in archive.filelist if f.filename.startswith(subfolder)):
                    # Strip subfolder from filepath
                    filename = os.path.join(*(item.filename.split("/")[1:])) 

                    if not filename:
                        continue

                    extracted = True

                    _targetPath = os.path.join(target, filename)
                    _targetDir = os.path.dirname(_targetPath)

                    if not os.path.isdir(_targetDir):
                        os.makedirs(_targetDir)

                    if item.filename.endswith(os.path.sep):
                        # Directories end with a path separator
                        if not os.path.isdir(_targetDir):
                            os.makedirs(_targetPath)
                    else:
                        _source = archive.open(item.filename)
                        _target = open(_targetPath, "wb+")

                        shutil.copyfileobj(_source, _target)

                        _source.close()
                        _target.close()

            if not extracted:
                archive.extractall(target)

        except Exception, e:
            log.exception("Failed extracting %s" % path)
            self.callback(1, str(e), cb)
        else:
            self.callback(0, "", cb)
        finally:
            if archive:
                archive.close()

    def copytree(self, path, target, cb):
        """copy give path to given target (recursively)
        
        calls self._copytree in a thread
        """
        t = threading.Thread(target=self._copytree, args=(path, target, cb),
                             name="Copytree operation")
        t.setDaemon(True)
        t.start()
        
    def _copytree(self, path, target, cb):
        try:
            self._doCopytree(path, target)
        except Exception, e:
            log.exception("Failed copying %s" % path)
            self.callback(1, str(e), cb)
        else:
            self.callback(0, "", cb)
    
    def _doCopytree(self, path, target):
        """Effectively does what self.copytree suggests, needs to live in its own
        function as it calls itself for recursion
        """
        if os.path.isdir(path):
            if not os.path.isdir(target):
                os.makedirs(target)
            files = os.listdir(path)
            for f in files:
                self._doCopytree(os.path.join(path, f),
                                 os.path.join(target, f))
        else:
            shutil.copyfile(path, target)
            
    @components.ProxyToMainThreadAsync
    def callback(self, code, message, cb):
        cb.callback(code, str(message))

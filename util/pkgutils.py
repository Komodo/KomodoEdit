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

"""Some utils for building and working with Komodo's packages system."""

import os
from os.path import (join, dirname, basename, isdir, isfile, abspath,
                     splitext, exists, expanduser)
import sys
from glob import glob
import re
import logging
import md5
from pprint import pprint
from posixpath import join as urljoin

import applib
import buildutils




#---- globals

log = logging.getLogger("pkgutils")


#---- module API

class KomodoReleasesGuru(object):
    """A class that knows how to scan the Komodo file share to figure out
    what the current dev builds and releases are.
    """
    file_share_dir = "crimper:/home/apps/Komodo"
    _devbuild_platname_from_platname = {
        "win32-x86": "Windows",
        "linux-libcpp5-x86": "Linux",
        "linux-libcpp6-x86": "Linux",
        "macosx-x86": "MacOSX",
        "macosx-powerpc": "MacOSX",
    }
    
    def __init__(self, platname, pretty_product_type, version):
        self.platname = platname
        self.pretty_product_type = pretty_product_type
        self.version = version
    
    @property
    def ver(self):
        return '.'.join(self.version.split('.')[:2])
    
    @property
    def devbuilds_dir(self):
        return urljoin(self.file_share_dir, "DevBuilds",
                       self._devbuild_platname_from_platname[self.platname])

    def changenum_from_mar_path(self, mar_path):
        changenum_pat = re.compile("^Komodo-.*?-(\d+)-%s-.*$" % self.platname)
        try:
            return int(changenum_pat.search(basename(mar_path)).group(1))
        except AttributeError, ex:
            raise ValueError("'%s' doesn't match '%s'"
                             % (basename(mar_path), changenum_pat.pattern))

    def version_from_mar_path(self, mar_path):
        ver_pat = re.compile("^Komodo-%s-(.+?)-%s-complete.mar$"
                             % (self.pretty_product_type, self.platname))
        try:
            return ver_pat.search(basename(mar_path)).group(1)
        except IndexError, ex:
            raise Error("`%s' didn't match `%s'"
                        % (basename(mar_path), ver_pat.pattern))

    _released_versions_cache = None
    @property
    def released_versions(self):
        """Generate the list of Komodo releases (lastest first).
        
        A Komodo "release" counts if there is a ver dir in
        "crimper:/home/apps/Komodo" with a GoldBits directory.

        Returns 3-tuples:
            (<parsed-version-tuple>, <version-string>, <is-beta>)
        E.g.:
            ((4,2,0,'b',1,12345),    "4.2.0b1",        True)
            ((4,1,1,'c',0,12346),    "4.1.1",          False)
        """
        if self._released_versions_cache is None:
            self._released_versions_cache = []
            for f in buildutils.remote_glob(
                        urljoin(self.file_share_dir, "*", "GoldBits")):
                ver_str = basename(dirname(f))
                ver = buildutils.split_short_ver(ver_str, intify=True)
                if len(ver) == 3: # e.g. (4,1,0) -> (4,1,0,'c',0)
                    # This helps sort 4.1.0 before 4.1.0b2.
                    ver = (ver[0], ver[1], ver[2], 'c', 0)
                    is_beta = False
                else:
                    is_beta = True
                
                pkg_pat = urljoin(self.file_share_dir, ver_str, "GoldBits",
                                  "Komodo-*-*-*.msi")
                for p in buildutils.remote_glob(pkg_pat):
                    # Warning: This parse is brittle.
                    changenum = int(splitext(basename(p))[0].split('-')[-1])
                    break
                else:
                    #log.warn("skip version '%s' (can't determine changenum)",
                    #         ver_str)
                    continue
                ver = tuple(list(ver) + [changenum])

                self._released_versions_cache.append(
                    (ver, ver_str, is_beta)
                )
            self._released_versions_cache.sort(reverse=True)

        for v in self._released_versions_cache:
            yield v

    def last_dev_complete_mar(self, ignore_changenum=None):
        """Return the remote path to the latest dev build .mar file.
        
        @param ignore_changenum  If specified, a changenum to ignore.
            Typically this is used to ignore the current build changenum
            to ensure one doesn't create a partial .mar relative to oneself.
        """
        pat = "Komodo-%s-%s.*-%s-complete.mar" \
              % (self.pretty_product_type, self.ver, self.platname)
        mar_paths = buildutils.remote_glob(urljoin(self.devbuilds_dir, pat))
        if not mar_paths:
            return None
        mar_paths.sort(key=self.changenum_from_mar_path, reverse=True)

        if ignore_changenum is not None:
            if self.changenum_from_mar_path(mar_paths[0]) == ignore_changenum:
                del mar_paths[0]

        if not mar_paths:
            return None
        return mar_paths[0]

    def dev_complete_mar_from_changenum(self, changenum):
        """Return the remote path to the dev build complete .mar file
        for the given change number, if any. Otherwise, returns None.
        """
        pat = "Komodo-%s-%s-%s-%s-complete.mar" \
              % (self.pretty_product_type, self.version, changenum,
                 self.platname)
        mar_paths = buildutils.remote_glob(urljoin(self.devbuilds_dir, pat))
        if mar_paths:
            return mar_paths[0]
        else:
            return None

    def dev_partial_mars_from_changenum(self, changenum):
        """Return the remote paths to the dev build partial .mar files
        for the given change number, if any. Otherwise, returns None.
        """
        pat = "Komodo-%s-%s-%s-%s-partial-*.mar" \
              % (self.pretty_product_type, self.version, changenum,
                 self.platname)
        mar_paths = buildutils.remote_glob(urljoin(self.devbuilds_dir, pat))
        if not mar_paths:
            return None
        return mar_paths

    def _get_last_release_complete_mar(self, include_betas=False):
        for ver, ver_str, is_beta in self.released_versions:
            if not include_betas and is_beta:
                continue
            last_release_ver = ver
            last_release_ver_dir = ver_str
            break

        last_release_ver_str = '.'.join(map(str, last_release_ver[:3]))
        if last_release_ver[3] == 'a':
            last_release_ver_str += "-alpha%d" % last_release_ver[4]
        elif last_release_ver[3] == 'b':
            last_release_ver_str += "-beta%d" % last_release_ver[4]
        last_release_ver_str += "-%s" % last_release_ver[5]

        mar_name = "Komodo-%s-%s-%s-complete.mar" \
                   % (self.pretty_product_type, last_release_ver_str,
                      self.platname)
        mar_path = urljoin(self.file_share_dir, last_release_ver_dir,
                           "GoldBits", mar_name)
        return mar_path
    
    @property
    def last_release_complete_mar(self):
        """Return the remote path to the complete .mar for the latest
        release (beta or final).
        
        Note that this doesn't verify that the .mar exists for this version.
        It might be missing.
        """
        return self._get_last_release_complete_mar(include_betas=True)

    @property
    def last_final_release_complete_mar(self):
        """Return the remote path to the complete .mar for the latest
        *final* release.
        
        Note that this doesn't verify that the .mar exists for this version.
        It might be missing.
        """
        return self._get_last_release_complete_mar(include_betas=False)



class KomodoMarCacher(object):
    """Use one of these to get cracked versions of complete Komodo .mar
    archives. This is useful for creating partial Komodo archives.
    
    Dev Notes:
    - There is a path limitation that breaks "mar -x ..." if a full file
      path length exceeds ~256 chars. We try to mitigate that by using
      some shorter paths.
    """
    def __init__(self):
        self.cache_dir = join(applib.user_cache_dir("kodev", "ActiveState"),
                              "mar")

    def _cache_mar_path_from_mar_path(self, mar_path):
        return join(self.cache_dir, basename(mar_path))

    def _cache_mar_dir_from_mar_path(self, mar_path):
        cache_mar_path = self._cache_mar_path_from_mar_path(mar_path)
        return join(dirname(cache_mar_path),
                    md5.new(basename(cache_mar_path)).hexdigest())

    def _cache_mar_path(self, mar_path, skip_checksum_check=False):
        """Get a clean local cache of the given remote .mar path.
        
        Returns the path to the local copy of the .mar.
        """
        cache_mar_path = self._cache_mar_path_from_mar_path(mar_path)
        have_new_mar = False

        # If not in the cache, download it.
        if not exists(cache_mar_path):
            if not exists(dirname(cache_mar_path)):
                log.debug("mkdir `%s'", dirname(cache_mar_path))
                os.makedirs(dirname(cache_mar_path))
            buildutils.remote_cp(mar_path, cache_mar_path, log.debug)
            have_new_mar = True
            
        # Ensure cache's validity.
        if not skip_checksum_check:
            src_md5 = buildutils.remote_md5sum(mar_path, log.debug)
            cache_md5 = md5.new(open(cache_mar_path, 'rb').read()).hexdigest()
            if src_md5 != cache_md5:
                log.info("'%s' in cache is invalid: reloading", basename(mar_path))
                os.remove(cache_mar_path)
                buildutils.remote_cp(mar_path, cache_mar_path, log.debug)
                have_new_mar = True
                
                cache_md5 = md5.new(open(cache_mar_path, 'rb').read()).hexdigest()
                if src_md5 != cache_md5:
                    raise Error("cannot get valid copy of '%s' in mar cache: "
                                "md5sum even after a reload does not checkout"
                                % basename(mar_path))

        cache_mar_dir = self._cache_mar_dir_from_mar_path(mar_path)
        if have_new_mar and exists(cache_mar_dir):
            _rmtree(cache_mar_dir)
        
        return cache_mar_path

    def get_image_for_mar_path(self, mar_path, skip_checksum_check=False):
        """Return the full local path to an unpacking of the given mar."""
        cache_mar_path = self._cache_mar_path(mar_path, skip_checksum_check)

        # Crack it if necessary.
        cache_mar_dir = self._cache_mar_dir_from_mar_path(mar_path)
        if not exists(cache_mar_dir):
            if exists(cache_mar_dir):
                log.debug("rm `%s'", cache_mar_dir)
                _rmtree(cache_mar_dir)
            os.makedirs(cache_mar_dir)
            mozupdate = join(dirname(__file__), "mozupdate.py")
            buildutils.run('python %s -q unpack -d "%s" "%s"'
                            % (mozupdate, cache_mar_dir, cache_mar_path),
                           log.debug)

        return cache_mar_dir

    def get_size_of_mar_path(self, mar_path):
        """Return the size (in bytes) of the given remote .mar path.
        
        As will the other the other caching methods the .mar is downloaded
        and stat'd locally.
        """
        cache_mar_path = self._cache_mar_path(mar_path)
        return os.stat(cache_mar_path).st_size



#---- internal support stuff

def _rmtreeOnError(rmFunction, filePath, excInfo):
    if excInfo[0] == OSError:
        # presuming because file is read-only
        os.chmod(filePath, 0777)
        rmFunction(filePath)

def _rmtree(dirname):
    import shutil
    shutil.rmtree(dirname, 0, _rmtreeOnError)


#---- self-test

def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()


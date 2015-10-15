#!/usr/bin/env python
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
# Author:
#   Trent Mick (TrentM@ActiveState.com)

"""
    wax -- generate WiX fragments from an install image

    usage:
        wax.py

    options:
        -h, --help          Print this help and exit.
        -V, --version       Print the version of this script and exit.
        -v, --verbose       Increase the verbosity of output
        -q, --quiet         Only print output for warnings and errors.
        --self-test         Run a self-test and exit.

        -p <file>, --project-file <file>
            Tell 'wax' about your current WiX project files. Wax works
            better with this information because it can then attempt to
            ensure that there are no <File>, <Component> and <Directory>
            Id collisions with your existing definitions. As well, Wax
            can attempt to skip files already included in your project
            when it processes an install image.
        -b <dir>
            Specify the base directory to locate image files. Defaults
            to the current directory.
        -w, --write-files
            Write generated content to "feature-<name>-wax.wxs" instead
            of writing to stdout.
        -f, --force         Force overwriting existing files.

    Wax analyzes an install image (structured in a particular way) and
    spits out WiX fragments suitable for use in a WiX project. If you
    have a large number of files in your project then creating the
    initial WiX <Directory>, <Component> and <File> definitions can be a
    PITA and error prone. So can future maintenance as files are added
    and removed.
    
    So here is what you do. Create an install image for your project
    structured as follows:

        feature-<featurename1>/
            <directory1>/
                ...
            <directory2>/
                ...
        feature-<featurename2>/
            <directory1>/
                ...

    - At the top-level you want a "feature-*" directory for each
      <Feature> in your product.
    - At the second-level you have a directory for each disjoint
      <Directory> Id in your project to which you want to install files.
    - Below the second-level, lay out the files as you would like them
      installed on the target machine.

    Most commonly you are just going to install some files to the
    configurable "INSTALLDIR". E.g. if you have something like this:

        <Directory Id="TARGETDIR" Name="SourceDir">
          <Directory Id="ProgramFilesFolder" Name="PFILES">
            <Directory Id="INSTALLDIR" Name="Doodle"
                       LongName="Acme SuperDoodle"/>
          </Directory>
        </Directory>
        ...
        <Feature Id="core" ConfigurableDirectory="INSTALLDIR" ...>
          ...
        </Feature>

    Then your install image should look something like this:

        feature-core/
            INSTALLDIR/
                doodle.exe
                doodle.dll

    Then your install image should be:

        feature-core/
            INSTALLDIR/
                doodle.exe
                doodle.dll

    Now run "wax" to generate the appropriate WiX fragment for your
    project.

        $ python wax.py -p product.wxs
        wax: importing project data from 'product.wxs'
        wax: generate WiX <Fragment> for feature 'core' from 'feature-core/...'
        <?xml version="1.0" encoding="utf-8"?>
        <Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
          <Fragment>
            <DirectoryRef Id="INSTALLDIR">
              <Component Id="component0" DiskId="1" Guid="$(autowix.guid)">
        ...

    Wax spits out complete Wix fragment documents that can be linked in
    with your other .wixobj files. (Note the presence of "$(autowix.guid)"
    means you either need to manually change these to real GUIDs, or use
    the "autowix.py" tool.)

    Examples:
        # Process the install image in the current dir, accounting for
        # existing definitions in the current "*.wxs" WiX project files.
        python wax.py -p *.wxs
"""
# TODO:
# - get a pretty printer for ElementTree writing
# - then, convert Accumulator over to using it
# - then, update 'add_directory' usage to be smart enough to track
#   existing directory definitions and use <DirectoryRef>'s instead.
#   *Or* (if that isn't a good maintenance mechanism) then try a system
#   where Wax updates an existing feature-*.wxs document. That will be
#   tricky, but is probably the best way to go, long term.
#
# - I think there is a bug in component_id and directory_id numbering
#   that causes them to get higher than they need. Test it out by adding
#   a file or two to the Komodo install image.
# - look at "mallow" tool for doing similar thing:
#   http://sourceforge.net/mailarchive/forum.php?thread_id=6534155&forum_id=39978
# - might be breaking component rules!:
#   http://www.lukemelia.com/devblog/archives/2005/09/30/wix-fragment-component-generation/
# - expected dir layout definition in base .wxs file
# - Perhaps add option to generate actual GUIDs? Only when this script
#   is good at only generating *update* information.

__version_info__ = (0, 4, 1)
__version__ = '.'.join(map(str, __version_info__))

import os
from os.path import exists, isdir, isfile, abspath, basename, splitext, \
                    join, dirname, normpath, normcase
import sys
import getopt
import re
import pprint
import glob
import traceback
import logging
from optparse import OptionParser
import cgi


sys.path.insert(0, dirname(__file__))
try:
    try:
        from ElementTree import dump, parse, Element, SubElement, ElementTree
    except ImportError:
        from elementtree.ElementTree import dump, parse, Element, SubElement, ElementTree
finally:
    del sys.path[0]



class Error(Exception):
    pass



#---- globals

log = logging.getLogger("wax")

# Be restrictive of feature names.
PATTERN_FEATURE = re.compile("^\w+$")
# A legal 8.3 filename.
PATTERN_8_3_NAME = re.compile("^(\w){1,8}(\.(\w){1,3})?$")



#---- main functions

def wax(project_files, write_files, base_image_dir, force=False):
    """Generate WiX fragments from an install image.

        "project_files" is a list of WiX source files to take into
            account during generation.
        "write_files" is a boolean indicating if generated content
            should be written to stdout or to "feature-<name>-wax.wxs"
            files.
        "base_image_dir" is the base directory of the install image,
            i.e. the one with "feature-*" directories.
        "force" is a boolean indicating if existing files can be
          overwritten (only makes sense if "write_files" is true).

    This function doesn't return anything.
    """
    #XXX Parse main .wxs to get the list of features. Then validate the
    #    found install image dirs against that.

    feature_dirs = glob.glob(join(base_image_dir, "feature-*"))
    guru = Guru(project_files)
    for feature_dir in feature_dirs:
        if not isdir(feature_dir): continue
        feature_name = basename(feature_dir).split('-', 1)[1]
        if not PATTERN_FEATURE.match(feature_name):
            raise Error("aborting, weird feature name: %r" % feature_name)

        if write_files:
            output_filename = "feature-%s-wax.wxs" % feature_name
            if exists(output_filename) and not force:
                raise Error("'%s' already exists: use '--force' to overwrite"
                            % output_filename)

        log.info("generate WiX <Fragment> for feature '%s' from '%s'",
                 feature_name, feature_dir)
        accum = Accumulator(feature_name, guru)
        accum.start()
        level = 1
        accum.start_fragment()
        walk_feature_dir(accum, feature_dir, level=level+1)
        accum.add_feature_ref()
        accum.end_fragment()
        accum.end()

        if accum.has_content():
            if write_files:
                fout = open(output_filename, 'w')
                try:
                    accum.write(fout)
                except:
                    fout.close()
                log.info("'%s' written", output_filename)
            else:
              if not log.isEnabledFor(logging.DEBUG):
                  # If debugging the content has already been printed.
                  accum.write(sys.stdout)
        else:
            log.info("no files to add for feature '%s'", feature_name)

def walk_feature_dir(accum, feature_dir, level=0):
    # Each top-level subdir of the feature_dir corresponds to a
    # <Directory/> Id in the main WiX source. (XXX verify that)
    for directory_id in os.listdir(feature_dir):
        ref_dir = join(feature_dir, directory_id)
        if not isdir(ref_dir):
            log.debug("skipping non-reference dir: '%s'", ref_dir)
            continue

        walk_ref_dir(accum, ref_dir, ref_dir)

def is_8_3_name(name):
    """Is the given name a legal 8.3 filename?

        >>> is_8_3_name("foo.txt")
        True
        >>> is_8_3_name("12345678.123")
        True
        >>> is_8_3_name("123456789.123")
        False
        >>> is_8_3_name("12345678.1234")
        False
        >>> is_8_3_name("12345678.")
        False
        >>> is_8_3_name(".123")
        False
        >>> is_8_3_name("1.1")
        True
        >>> is_8_3_name("Makefile")
        True
        >>> is_8_3_name("doc")
        True
        >>> is_8_3_name(".ssh")
        False
    """
    return PATTERN_8_3_NAME.match(name) is not None


class Guru:
    """A Guru instance is used to manage generating names, etc. while
    avoiding name/id collisions. It takes into account (as well as it
    can) the information from given existing WiX project source files.
    """
    def __init__(self, project_files):
        self.directory_index = 0
        self.component_index = 0
        self.file_index = 0
        self.removefile_index = 0

        # Already used Id's and Name's in this project.
        self.short_path_names = {} # used short path names in this project
        self.component_ids = {}
        self.directory_ids = {}
        self.removefile_ids = {}
        self.file_ids = {}
        self.file_srcs = {}
        self._process_project_files(project_files)

    def _process_project_files(self, project_files):
        """Process all the given WiX project files."""
        ns = "http://schemas.microsoft.com/wix/2006/wi"
        for project_file in project_files:
            log.info("importing project data from '%s'", project_file)
            tree = parse(project_file)
            for c in tree.findall("//{%s}Component" % ns):
                id = c.get("Id")
                if "$(" in id:
                    log.warn("cannot guarantee no 'Id' collision with "
                             "<Component Id='%s'> "
                             "because of preprocessor variable", id)
                else:
                    self.component_ids[id] = True
            for d in tree.findall("//{%s}Directory" % ns):
                id, name = d.get("Id"), d.get("Name")
                if id is None:
                    raise Error("there is no 'Id' attribute on "
                                "'Directory' element %r" % d)
                elif "$(" in id:
                    log.warn("cannot guarantee no 'Id' collision with "
                             "<Directory Id='%s' Name='%s'> "
                             "because of preprocessor variable", id, name)
                else:
                    self.directory_ids[id] = True
                if name is None:
                    pass
                elif "$(" in name:
                    log.warn("cannot guarantee no 'Name' collision with "
                             "<Directory Id='%s' Name='%s'> "
                             "because of preprocessor variable", id, name)
                else:
                    self.short_path_names[name] = True
            for d in tree.findall("//{%s}RemoveFile" % ns):
                id = d.get("Id")
                if id == "NEWREMOVEFILE":
                    continue
                self.removefile_ids[id] = True
            for f in tree.findall("//{%s}File" % ns):
                id = f.get("Id")
                if id == "NEWFILE":
                    continue
                name, src = f.get("Name"), f.get("src")
                if "$(" in id:
                    log.warn("cannot guarantee no 'Id' collision with "
                             "<File Id='%s' Name='%s'> "
                             "because of preprocessor variable", id, name)
                else:
                    self.file_ids[id] = True
                if "$(" in name:
                    log.warn("cannot guarantee no 'Name' collision with "
                             "<File Id='%s' Name='%s'> "
                             "because of preprocessor variable", id, name)
                else:
                    self.short_path_names[name] = True
                if "$(" in src:
                    log.warn("cannot guarantee no 'src' collision with "
                             "<File Id='%s' src='%s'> "
                             "because of preprocessor variable", id, src)
                else:
                    self.file_srcs[normcase(normpath(src))] = True

        if log.isEnabledFor(logging.DEBUG):
            pprint.pprint(self.short_path_names)
            pprint.pprint(self.component_ids)
            pprint.pprint(self.directory_ids)
            pprint.pprint(self.file_ids)
            pprint.pprint(self.file_srcs)

    def have_file_src(self, src):
        return normcase(normpath(src)) in self.file_srcs

    def _use_short_path_name(self, name):
        # Sanity check: blow up if there is a short name collision.
        #XXX Should compare the existing .wxs files to ensure don't add
        #    a collision.
        key = name.upper()
        if key in self.short_path_names:
            raise Error("short path name collision (something went "
                        "wrong): '%s'" % key)
        self.short_path_names[key] = True

    def _is_short_path_name_used(self, name):
        return name.upper() in self.short_path_names

    def _get_short_path_name(self, basename):
        """Return a suitable 8.3-ized short name for this file base
        name, trying to avoid collisions with other shortnames in this
        WiX project.
        """
        # Get a clean, uppercase, and 8.3 "base" and "ext" -> our "key"
        base, ext = splitext(basename)
        ext = ext[1:]               # drop '.' in ext
        base = re.sub("[^\w]", "", base)[:8].upper() or "FILE"
        ext = re.sub("[^\w]", "", ext)[:3].upper()
        if ext: ext = '.' + ext     # put the '.' back in ext
        key = base + ext

        NUM_ATTEMPTS = 1000
        for i in range(NUM_ATTEMPTS):
            # Append numbered suffix to "key" until we have a unique
            # short name:
            #   ABCDEFGH.ABC -> ABCDEF_<i>.ABC   #   1 <= i <   10
            #   ABCDEFGH.ABC -> ABCDE_<i>.ABC    #  10 <= i <  100
            #   ABCDEFGH.ABC -> ABCD_<i>.ABC     # 100 <= i < 1000
            #   ...
            suffix = "_%s" % i
            name = base[:8-len(suffix)] + suffix + ext
            if not self._is_short_path_name_used(name):
                break
        else:
            raise Error("This is crazy. Apparently you have more than "
                        "%d files matching the 8.3 pattern '%s'. If "
                        "this is actually true, then NUM_ATTEMPTS "
                        "here needs to be increased."
                        % (NUM_ATTEMPTS, key))

        #log.debug("short path name: '%s' -> '%s' -> '%s'",
        #          basename, key, name)
        return name

    def get_path_names(self, basename):
        """Return (<Name>, <LongName>) for the given path basename as
        required for WiX attributes of those names.

        Basically, in WiX (and MSI) the "Name" attribute in <File> and
        <Directory> tags (1) have to fit 8.3 name requirements (no
        spaces) and (2) have to be unique for the whole project.

        If the given basename already fits and it doesn't look like
        there is a collision with others in the project, then we just
        use that for the "Name". In this case the "LongName" attribute
        is not necessary -- signified here by returning None:
            (basename, None)

        If the basename has to be modified then we create a unique one
        and return:
            (<shortname>, basename)
        """
        if is_8_3_name(basename) \
           and not self._is_short_path_name_used(basename):
            name = basename
            longname = None
        else:
            # Have the construct a short path name.
            name = self._get_short_path_name(basename)
            longname = basename

        self._use_short_path_name(name)
        return (name, longname)
        
    def get_removefile_id(self):
        SENTINEL = 1000
        for i in range(self.removefile_index, SENTINEL):
            id = "removefile%s" % i
            if id not in self.removefile_ids:
                self.removefile_index = i+1
                return id
        else:
            raise Error("hit sentinel on number of 'removefile<num>' "
                        "RemoveFile ids: if you *do* actually have more "
                        "than %d <RemoveFile>s in your WiX project then "
                        "you'll need to increase SENTINEL in the code, "
                        "otherwise there is a bug" % SENTINEL)

    def get_file_id(self):
        SENTINEL = 10000
        for i in range(self.file_index, SENTINEL):
            id = "file%s" % i
            if id not in self.file_ids:
                self.file_index = i+1
                return id
        else:
            raise Error("hit sentinel on number of 'file<num>' File ids: "
                        "if you *do* actually have more than %d files in "
                        "your WiX project then you'll need to increase "
                        "SENTINEL in the code, otherwise there is a bug"
                        % SENTINEL)

    def get_directory_id(self):
        SENTINEL = 1500
        for i in range(self.directory_index, SENTINEL):
            id = "directory%s" % i
            if id not in self.directory_ids:
                self.directory_index = i+1
                return id
        else:
            raise Error("hit sentinel on number of 'directory<num>' "
                        "Directory ids: if you *do* actually have more "
                        "than %d directories in your WiX project then "
                        "you'll need to increase SENTINEL in the code, "
                        "otherwise there is a bug"
                        % SENTINEL)

    def get_component_id(self):
        SENTINEL = 5000
        for i in range(self.component_index, SENTINEL):
            id = "component%s" % i
            if id not in self.component_ids:
                self.component_index = i+1
                return id
        else:
            raise Error("hit sentinel on number of 'component<num>' "
                        "Component ids: if you *do* actually have more "
                        "than %d components in your WiX project then "
                        "you'll need to increase SENTINEL in the code, "
                        "otherwise there is a bug"
                        % SENTINEL)

class Accumulator(list):
    """Accumulate WiX source content.
    
    At the most basic level, WiX content can be added with the .add()
    method.  However, more typically the various .add_*() and
    .start_*()/.end_*() methods should be used.
    """
    def __init__(self, feature, guru, *args, **kwargs):
        list.__init__(self, *args, **kwargs)
        self.feature = feature  # the feature name for this fragment
        self.guru = guru  # tools for getting conformant MSI field names
        self.level = None   # for indentation of XML output
        self.added_component_ids = []
        self.directory_path = "" # track dir path for </Directory> comments
##        self.tree = None

    def add(self, item, level=None):
        """Add some WiX source content to the accumulator."""
        indent = '  ' * (level or self.level)
        s = indent + item
        list.append(self, s)
        if log.isEnabledFor(logging.DEBUG):
            print s

    def has_content(self):
        return bool(self)

    def write(self, stream):
        stream.write('\n'.join(self) + '\n')
##        self.tree.write(stream)

    def start(self):
        self.level = 0
        self.add('<?xml version="1.0" encoding="utf-8"?>')
        self.add('<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">')
##        self.focus = Element("Wix",
##            xmlns="http://schemas.microsoft.com/wix/2006/wi")
##        self.focus.tail = self.focus.text = '\n'
##        self.tree = ElementTree(self.focus)
        self.level += 1
    def end(self):
        self.level -= 1
        # If there was no content for this Wix then drop everything.
        if self[-1].lstrip().startswith("<Wix "):
            while self:
                self.pop()
        else:
            self.add('</Wix>')

    def start_fragment(self):
        self.add('<Fragment>')
##        self.focus = self.fragment = SubElement(self.focus, "Fragment")
##        self.focus.tail = self.focus.text = '\n'
        self.level += 1
    def end_fragment(self):
        self.level -= 1
        # If there was no content for this Fragment then drop it.
        if self[-1].lstrip().startswith("<Fragment"):
            self.pop()
        else:
            self.add('</Fragment>')

    def start_directory_ref(self, id):
        self.add('<DirectoryRef Id="%s">' % id)
##        self.focus = SubElement(self.focus, "DirectoryRef", Id=id)
##        self.focus.tail = self.focus.text = '\n'
        self.level += 1
    def end_directory_ref(self):
        self.level -= 1
        # If there was no content for this DirectoryRef then drop it.
        if self[-1].lstrip().startswith("<DirectoryRef "):
            self.pop()
        else:
            self.add('</DirectoryRef>')

    def start_directory(self, basename):
        self.directory_path = join(self.directory_path, basename)
        id = self.guru.get_directory_id()
        name, longname = self.guru.get_path_names(basename)
        if longname:
            self.add('<Directory Id="%s" Name="%s" LongName="%s">'
                     % (id, name, longname))
##            self.focus = SubElement(self.focus, "Directory",
##                                    Id=id, Name=name, LongName=longname)
        else:
            self.add('<Directory Id="%s" Name="%s">' % (id, name))
##            self.focus = SubElement(self.focus, "Directory",
##                                    Id=id, Name=name)
##        self.focus.tail = self.focus.text = '\n'
        self.level += 1
    def end_directory(self):
        self.level -= 1
        # If there was no content for this directory then drop it.
        if self[-1].lstrip().startswith("<Directory "):
            # XXX Should really recycle the directory id
            self.pop()
        else:
            self.add('</Directory> <!-- %s -->' % self.directory_path)
        self.directory_path = dirname(self.directory_path)

    def start_component(self, diskid=1):
        id = self.guru.get_component_id()
        guid = "$(autowix.guid)"
        self.add('<Component Id="%s" DiskId="%s" Guid="%s">'
                 % (id, diskid, guid))
##        self.focus = SubElement(self.focus, "Component",
##                                Id=id, DiskId=str(diskid), Guid=guid)
##        self.focus.tail = self.focus.text = '\n'
        self.added_component_ids.append(id)
        self.level += 1
    def end_component(self):
        self.level -= 1
        # If there was no content for this component then drop it.
        if self[-1].lstrip().startswith("<Component "):
            # XXX Should really recycle the component id
            del self.added_component_ids[-1]
            self.pop()
        else:
            self.add('</Component>')

    def add_file(self, src, vital=True):
        if self.guru.have_file_src(src):
            log.debug("skipping '%s', already have it", src)
            return
        id = self.guru.get_file_id()
        name, longname = self.guru.get_path_names(basename(src))
        attrs = 'Id="%s" Name="%s"' % (id, name)
        if longname:
            attrs += ' LongName="%s"' % cgi.escape(longname, True)
        if vital:
            attrs += ' Vital="%s"' % (vital and "yes" or "no")
        attrs += ' src="%s"' % cgi.escape(normpath(src), True)
        self.add('<File %s/>' % attrs)

##        attrs = {"Id": id, "Name": name, "src": src}
##        if longname: attrs["LongName"] = longname
##        if vital: attrs["Vital"] = (vital and "yes" or "no")
##        self.focus = SubElement(self.focus, "File", **attrs)
##        self.focus.tail = self.focus.text = '\n'

    def add_feature_ref(self):
        """Add the <FeatureRef> block for all the scanned components."""
        if self.added_component_ids:
            self.add('<FeatureRef Id="%s">' % self.feature)
            self.level += 1
            for component_id in self.added_component_ids:
                self.add('<ComponentRef Id="%s"/>' % component_id)
            self.level -= 1
            self.add('</FeatureRef>')

##        feature_ref = SubElement(self.fragment, "FeatureRef", Id=self.feature)
##        feature_ref.tail = feature_ref.text = '\n'
##        for component_id in self.added_component_ids:
##            e = SubElement(feature_ref, "ComponentRef", Id=component_id)
##            e.tail = e.text = '\n'


def walk_ref_dir(accum, dirpath, ref_dir):
    if dirpath == ref_dir:
        accum.start_directory_ref(basename(dirpath))
    else:
        accum.start_directory(basename(dirpath))
    
    # Separate files from subdirs in this directory.
    filepaths = []
    subdirpaths = []
    for path in [join(dirpath, f) for f in os.listdir(dirpath)]:
        if isdir(path):
            subdirpaths.append(path)
        elif isfile(path):
            filepaths.append(path)
        else:
            raise Error("what is this? it isn't a dir or file: '%s'" % path)

    # Add a <Component> for the files in this dir.
    if filepaths:
        accum.start_component()
        for filepath in filepaths:
            accum.add_file(filepath)
        accum.end_component()
     
    # Recurse into each subdirectory.
    for subdirpath in subdirpaths:
        walk_ref_dir(accum, subdirpath, ref_dir)

    if dirpath == ref_dir:
        accum.end_directory_ref()
    else:
        accum.end_directory()



#---- internal support functions

# Recipe: pretty_logging (0.1) in C:\trentm\tm\recipes\cookbook
class _PerLevelFormatter(logging.Formatter):
    """Allow multiple format string -- depending on the log level.
    
    A "fmtFromLevel" optional arg is added to the constructor. It can be
    a dictionary mapping a log record level to a format string. The
    usual "fmt" argument acts as the default.
    """
    def __init__(self, fmt=None, datefmt=None, fmtFromLevel=None):
        logging.Formatter.__init__(self, fmt, datefmt)
        if fmtFromLevel is None:
            self.fmtFromLevel = {}
        else:
            self.fmtFromLevel = fmtFromLevel
    def format(self, record):
        record.levelname = record.levelname.lower()
        if record.levelno in self.fmtFromLevel:
            #XXX This is a non-threadsafe HACK. Really the base Formatter
            #    class should provide a hook accessor for the _fmt
            #    attribute. *Could* add a lock guard here (overkill?).
            _saved_fmt = self._fmt
            self._fmt = self.fmtFromLevel[record.levelno]
            try:
                return logging.Formatter.format(self, record)
            finally:
                self._fmt = _saved_fmt
        else:
            return logging.Formatter.format(self, record)

def _setup_logging():
    hdlr = logging.StreamHandler()
    defaultFmt = "%(name)s: %(levelname)s: %(message)s"
    infoFmt = "%(name)s: %(message)s"
    fmtr = _PerLevelFormatter(fmt=defaultFmt,
                              fmtFromLevel={logging.INFO: infoFmt})
    hdlr.setFormatter(fmtr)
    logging.root.addHandler(hdlr)
    log.setLevel(logging.INFO)



#---- mainline

def main(argv):
    # Process command line.
    try:
        optlist, args = getopt.getopt(argv[1:], "h?Vvqp:wfb:",
            ["help", "version", "verbose", "quiet", "self-test",
             "project-file=", "write-files", "force"])
    except getopt.GetoptError, ex:
        raise Error(str(ex))
        return 1
    help = False
    project_files = []
    write_files = False
    force = False
    base_image_dir = os.curdir
    for opt, optarg in optlist:
        if opt in ("-h", "-?", "--help"):
            print __doc__
            return 0
        elif opt in ("-V", "--version"):
            print "wax %s" % __version__
            return 0
        elif opt in ("-v", "--verbose"):
            log.setLevel(logging.DEBUG)
        elif opt in ("-q", "--quiet"):
            log.setLevel(logging.WARN)
        elif opt in ("--self-test",):
            log.info("running self-test...")
            import doctest
            return doctest.testmod()
        elif opt == "-b":
            base_image_dir = optarg
            if not isdir(base_image_dir):
                raise Error("given base image dir is not a directory: '%s'"
                            % base_image_dir)
        elif opt in ("-p", "--project-file"):
            if '?' in optarg or '*' in optarg:
                files = glob.glob(optarg)
                if not files:
                    raise Error("no files found matching '%s'" % optarg)
                project_files += files
            else:
                if not exists(optarg):
                    raise Error("'%s' does not exist" % optarg)
                project_files.append(optarg)
        elif opt in ("-w", "--write-files"):
            write_files = True
        elif opt in ("-f", "--force"):
            force = True

    return wax(project_files, write_files, base_image_dir=base_image_dir,
               force=force)


if __name__ == "__main__":
    if sys.version_info[:2] <= (2,2): __file__ = sys.argv[0]
    _setup_logging()
    try:
        retval = main(sys.argv)
    except KeyboardInterrupt:
        sys.exit(1)
    except:
        exc_info = sys.exc_info()
        if log.isEnabledFor(logging.DEBUG):
            print
            traceback.print_exception(*exc_info)
        else:
            if hasattr(exc_info[0], "__name__"):
                #log.error("%s: %s", exc_info[0].__name__, exc_info[1])
                log.error(exc_info[1])
            else:  # string exception
                log.error(exc_info[0])
        sys.exit(1)
    else:
        sys.exit(retval)



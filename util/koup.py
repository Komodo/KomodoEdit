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
# Contributors:
#   Trent Mick (TrentM@ActiveState.com)

"""Upgrade to the latest Komodo development build."""

__revision__ = "$Id$"
__version_info__ = (0, 2, 0)
__version__ = '.'.join(map(str, __version_info__))

import os
from os.path import exists, join, basename, expanduser
from posixpath import join as urljoin
import sys
import re
from pprint import pprint
from glob import glob
import traceback
import logging
import optparse
import urllib
import socket
import tempfile
if sys.platform == "win32":
    import _winreg
from xml.dom import minidom



#---- exceptions

class Error(Exception):
    pass



#---- globals

log = logging.getLogger("koup")
g_ko_branch_name = "devel"



#---- module API

def koup(version=None, product_type=None, buildnum=None, dry_run=False,
         channel=None):
    """Upgrade to the latest available Komodo dev-build of the given
    version.
    
        "version" is either a "<major>.<minor>" Komodo version or None
            (indicating the latest).
        "product_type" (optional) can be used to specify the Komodo
            product type to install. Either "ide" (the default) or
            "edit".
        "buildnum" (optional) can be used to restrict to a specific
            Komodo build number (a.k.a. p4 changenum). Can use a negative
            number to count back from latest available rev, e.g. "-b -1"
            will choose the second-latest build.
        "dry_run" (optional, default False) just go through the motions.
        "channel" (optional) if specified will edit channel-prefs.js appropriately
            post-install to switch that Komodo install to the given channel name.
    """
    if version is None:
        version = _get_latest_komodo_version()
    if not re.match(r"\d+\.\d+", version):
        raise Error("illegal Komodo version, %r, must match "
                    "'<major>.<minor>'" % version)
    if product_type is None:
        product_type = "ide"
    pretty_product_type = {
        "ide": "IDE",
        "edit": "Edit",
    }.get(product_type) or product_type.capitalize()
    log.info("upgrading to latest Komodo %s %s", pretty_product_type, version)

    fullver, buildnum, package_path \
        = _find_latest_komodo_dev_build(version, pretty_product_type,
            _get_komodo_platname(), buildnum=buildnum)
    log.info("latest build is `%s'", basename(package_path))

    # If there is a current installation, abort if it is already the
    # latest, else uninstall it.
    install_info = _is_komodo_installed(version, product_type,
                                        pretty_product_type)
    if install_info:
        try:
            if not _is_latest_komodo_different(fullver, buildnum,
                                               pretty_product_type,
                                               install_info):
                log.info("already have latest Komodo installed, "
                         "skipping upgrade")
                return
        except Error, ex:
            preamble = """\
-------------
There was an error determining if your currently installed Komodo is
actually older than the latest (%s build %s).
Would you like to go ahead with the upgrade anyway?"""\
% (fullver, buildnum)
            answer = _query_user(preamble, "no", prompt="[yes|NO] ",
                                 validate="yes-or-no")
            normalized = {'y': 'yes', 'ye': 'yes', 'yes': 'yes',
                          'n': 'no',  'no': 'no'}
            answer = normalized[answer.lower()]
            if answer != "yes":
                log.info("aborting upgrade")
                return
        _uninstall_komodo(version, pretty_product_type,
                          install_info, dry_run=dry_run)

    _install_komodo(version, pretty_product_type,
                    fullver, buildnum, package_path,
                    install_info, dry_run=dry_run,
                    channel=channel)


#---- internal support remote path routines

def _capture_status(argv):
    import subprocess
    p = subprocess.Popen(argv,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    output = p.stdout.read()
    retval = p.wait()
    return retval

_remote_path_re = re.compile("(\w+@)?\w+:/(?!/)")
def _is_remote_path(rpath):
    return _remote_path_re.search(rpath) is not None

def _remote_exists(rpath, log=None):
    login, path = rpath.split(':', 1)
    if sys.platform == "win32":
        argv = ["plink", "-batch", login, "ls", path]
    else:
        # HACK: gimlet's ancient ssh can't handle BatchMode
        if socket.gethostname() == "gimlet":
            argv = ["ssh", login, "ls", path]
        else:
            argv = ["ssh", "-o", "BatchMode=yes", login, "ls", path]
    if log:
        log(' '.join(argv))
    status = _capture_status(argv)
    return status == 0

def _remote_cp(src, dst, log=None):
    if sys.platform == "win32":
        cmd = "pscp -q %s %s" % (src, dst)
    else:
        cmd = "scp -B %s %s" % (src, dst)
    if log:
        log(cmd)
    status = _run(cmd)

def _remote_glob(rpattern, log=None):
    login, pattern = rpattern.split(':', 1)
    if sys.platform == "win32":
        argv = ["plink", "-batch", login, "ls", '"%s"' % pattern]
    else:
        # HACK: gimlet's ancient ssh can't handle BatchMode
        if socket.gethostname() == "gimlet":
            argv = ["ssh", login, "ls", '"%s"' % pattern]
        else:
            argv = ["ssh", "-o", "BatchMode=yes", login, "ls",
                    '"%s"' % pattern]
    cmd = ' '.join(argv)
    if log:
        log(cmd)
    #TODO: if move to recipes, update _capture_output() to subprocess
    output = _capture_output(cmd)
    rpaths = ["%s:%s" % (login, p.strip()) 
              for p in output.splitlines(0) if p.strip()]
    return rpaths


#---- internal support functions

# Recipe: query_user (0.2+) in /home/trentm/tm/recipes/cookbook
def _query_user(preamble, default=None, prompt="> ", validate=None):
    """Ask the user a question using raw_input() and looking something
    like this:

        <preamble>
        <prompt>
        ...validate...

    Arguments:
        "preamble" is a string to display before the user is prompted
            (i.e. this is the question).
        "default" (optional) is a default value.
        "prompt" (optional) is the prompt string.
        "validate" (optional) is either a string naming a stock validator:\

                notempty        Ensure the user's answer is not empty.
                                (This is the default.)
                yes-or-no       Ensure the user's answer is 'yes' or 'no'.
                                ('y', 'n' and any capitalization are
                                also accepted)

            or a callback function with this signature:
                validate(answer) -> errmsg
            It should return None to indicate a valid answer.
            
            If not specified the default validator is used -- which just
            ensures that a non-empty value is entered.

    XXX Extend validation to be able to massage the answer. E.g., for
        "yes-or-no" validation it should be able to normalize 'y' to
        'yes'.
    """
    if isinstance(validate, (str, unicode)):
        if validate == "notempty":
            def validate_notempty(answer):
                if not answer:
                    return "You must enter some non-empty value."
            validate = validate_notempty
        elif validate == "yes-or-no":
            def validate_yes_or_no(answer):
                normalized = {'y': 'yes', 'ye': 'yes', 'yes': 'yes',
                              'n': 'no',  'no': 'no'}
                if answer.lower() not in normalized.keys():
                    return "Please enter 'yes' or 'no'."
            validate = validate_yes_or_no
        else:
            raise Error("unknown stock validator: '%s'" % validate)
    
    def indented(text, indent=' '*4):
        lines = text.splitlines(1)
        return indent + indent.join(lines)

    sys.stdout.write(preamble+'\n')
##    if default is not None:
##        sys.stdout.write("""\
##Default:
##%s
##Type <Enter> to use the default.
##""" % indented(default or "<empty>"))
    while True:
        if True:
            answer = raw_input(prompt)
        else:
            sys.stdout.write(prompt)
            sys.stdout.flush()
            answer = sys.stdout.readline()
        if not answer and default:
            answer = default
            #sys.stdout.write("using default: %s\n" % default)
        if validate is not None:
            errmsg = validate(answer)
            if errmsg:
                sys.stdout.write(errmsg+'\n')
                continue
        break
    return answer


def _create_tmp_dir():
    """Create a temporary directory and return the path to it."""
    if hasattr(tempfile, "mkdtemp"): # use the newer mkdtemp is available
        path = tempfile.mkdtemp()
    else:
        path = tempfile.mktemp()
        os.makedirs(path)
    return path


def _is_latest_komodo_different(latest_fullver, latest_buildnum,
                                pretty_product_type, install_info):
    if sys.platform == "win32":
        product_code = install_info
        # Just presume it is installed in default location.
        short_ver = '.'.join(latest_fullver.split('.')[:2])
        komodo_exe_path = r"C:\Program Files\ActiveState Komodo %s %s\ko.exe"\
                           % (pretty_product_type, short_ver)
        if not exists(komodo_exe_path):
            # "ko.exe" was added in Komodo 3.5.3b1 and is the only good
            # way to get the Komodo version from the command line. If
            # "ko.exe" isn't there, then just presume the latest *is*
            # new than this version.
            return True
    elif sys.platform == "darwin":
        install_dir = install_info
        komodo_exe_path = join(install_dir, "Contents", "MacOS", "komodo")
    else:
        install_dir = install_info
        komodo_exe_path = join(install_dir, "bin", "komodo")

    # Get the version of the currently installed Komodo.
    cmd = '"%s" --xml-version' % komodo_exe_path
    o = os.popen(cmd)
    ver_xml = o.read()
    retval = o.close()
    if retval:
        raise Error("error running '%s'" % cmd)
    dom = minidom.parseString(ver_xml)
    fullver_node = dom.getElementsByTagName("version")[0]
    current_fullver = ''.join(c.nodeValue for c in fullver_node.childNodes
                              if c.nodeType == c.TEXT_NODE)
    buildnum_node = dom.getElementsByTagName("build-number")[0]
    current_buildnum = ''.join(c.nodeValue
                               for c in buildnum_node.childNodes
                               if c.nodeType == c.TEXT_NODE)

    return (current_fullver, current_buildnum) \
           != (latest_fullver, latest_buildnum)

def _device_volumepath_from_hdiutil_attach(output):
    """
    Example output from an "hdiutil attach path/to/DMG" command:
        ...
        Finishing...
        Finishing...
        /dev/disk1              Apple_partition_scheme         
        /dev/disk1s1            Apple_partition_map            
        /dev/disk1s2            Apple_HFS                       /Volumes/Komodo-Professional-4.0
    """
    pat = re.compile(r"^(/dev/\w+)\s+Apple_HFS\s+(.+?)$", re.M)
    match = pat.search(output)
    return match.group(1), match.group(2)

def _install_komodo(version, pretty_product_type, 
                    fullver, buildnum, package_path,
                    install_info=None, dry_run=False,
                    channel=None):
    tmp_dir = _create_tmp_dir()
    log.debug("created working dir: '%s'" % tmp_dir)
    try:
        if sys.platform == "win32":
            log.info("install Komodo %s %s %s (to default install dir)",
                     pretty_product_type, fullver, buildnum)
            if not dry_run:
                tmp_package_path = join(tmp_dir, basename(package_path))
                if _is_remote_path(package_path):
                    _remote_cp(package_path, tmp_package_path, log.debug)
                else:
                    _run('copy /y "%s" "%s"' % (package_path, tmp_dir), 
                         log.debug)
                msiexec_exe = _get_msiexec_exe_path()
                _run("%s /q /i %s" % (msiexec_exe, tmp_package_path),
                     log.debug)

                if channel is not None:
                    install_dir = join(os.environ["ProgramFiles"],
                        "ActiveState Komodo %s %s" % (pretty_product_type, version))
                    _set_update_channel(install_dir, channel)

        elif sys.platform == "darwin":
            install_dir = "/Applications/Komodo %s %s.app"\
                          % (pretty_product_type, version)
            if exists(install_dir):
                raise Error("cannot install Komodo %s: `%s' exists"
                            % (fullver, install_dir))
            log.info("install Komodo %s %s %s to `%s'", pretty_product_type,
                     fullver, buildnum, install_dir)
            if not dry_run:
                tmp_package_path = join(tmp_dir, basename(package_path))
                if _is_remote_path(package_path):
                    _remote_cp(package_path, tmp_package_path, log.debug)
                else:
                    _run('cp "%s" "%s"' % (package_path, tmp_dir), log.debug)
                output = _capture_output('hdiutil attach "%s"'
                                         % tmp_package_path)
                device, volumepath \
                    = _device_volumepath_from_hdiutil_attach(output)
                src_path = glob(join(volumepath, "Komodo*.app"))[0]
                try:
                    _run('cp -R "%s" "%s"' % (src_path, install_dir),
                         log.debug)
                finally:
                    _run('hdiutil unmount "%s"' % volumepath)
                    _run('hdiutil detach "%s"' % device)
            
            if channel is not None:
                _set_update_channel(install_dir, channel)

        elif sys.platform.startswith("linux") \
             or sys.platform.startswith("sunos"):
            install_dir = expanduser("~/opt/Komodo-%s-%s"
                                     % (pretty_product_type, version))
            if not dry_run and exists(install_dir):
                raise Error("cannot install Komodo %s: `%s' exists"
                            % (fullver, install_dir))
            log.info("install Komodo %s %s %s to `%s'",
                     pretty_product_type, fullver, buildnum, install_dir)
            if not dry_run:
                tmp_package_path = join(tmp_dir, basename(package_path))
                if _is_remote_path(package_path):
                    _remote_cp(package_path, tmp_package_path, log.debug)
                else:
                    _run('cp "%s" "%s"' % (package_path, tmp_dir), log.debug)
                _run_in_dir("tar xzf %s" % basename(package_path),
                            tmp_dir, log.debug)
                install_sh_path \
                    = join(basename(package_path)[:-len(".tar.gz")],
                           "install.sh")
                _run_in_dir("sh %s -I %s" % (install_sh_path, install_dir),
                            tmp_dir, log.debug)

            if channel is not None:
                _set_update_channel(install_dir, channel)

        else:
            raise Error("unknown platform: `%s'" % sys.platform)
    finally:
        if not dry_run:
            log.debug("removing temporary working dir '%s'", tmp_dir)
            try:
                if sys.platform == "win32":
                    _run('rd /s/q "%s"' % tmp_dir, log.debug)
                else:
                    _run('rm -rf "%s"' % tmp_dir, log.debug)
            except EnvironmentError, ex:
                log.warn("could not remove temp working dir '%s': %s",
                         tmp_dir, ex)


def _set_update_channel(install_dir, channel):
    log.info("setting '%s' update channel to '%s'", install_dir, channel)
    if sys.platform == "darwin":
        channel_prefs_path = join(install_dir, "Contents", "MacOS", "defaults", 
                                  "pref", "channel-prefs.js")    
    else:
        channel_prefs_path = join(install_dir, "lib", "mozilla", "defaults", 
                                  "pref", "channel-prefs.js")    

    content = open(channel_prefs_path, 'r').read()
    content = re.sub(r'(pref\("app.update.channel",\s+")\w+("\))',
                     r'\1%s\2' % channel,
                     content)
    open(channel_prefs_path, 'w').write(content)


def _get_msiexec_exe_path():
    return join(os.environ["windir"], "system32", "msiexec.exe")


def _uninstall_komodo(version, pretty_product_type, install_info,
                      dry_run=False):
    if sys.platform == "win32":
        product_code = install_info
        log.info("uninstalling Komodo %s %s (ProductCode: %s)",
                 pretty_product_type, version, product_code)
        if not dry_run:
            msiexec_exe = _get_msiexec_exe_path()
            _run("%s /q /x %s" % (msiexec_exe, product_code), log.debug)

    else:
        install_dir = install_info
        log.info("uninstalling Komodo at `%s'", install_dir)
        if not dry_run:
            _run('rm -rf "%s"' % install_dir, log.debug)

def _capture_output(cmd):
    o = os.popen(cmd)
    output = o.read()
    retval = o.close()
    if retval:
        raise Error("error capturing output of `%s': %r" % (cmd, retval))
    return output

def _find_installed_komodo_registry_id(version, product_type):
    """Return the Windows registry id for the given Komodo, if it
    is installed. Otherwise, returns None.
    """
    candidate_registry_ids = [version, "%s-%s" % (version, product_type)]
    for registry_id in candidate_registry_ids:
        keyName = r"Software\ActiveState\Komodo\%s" % registry_id
        for base in (_winreg.HKEY_LOCAL_MACHINE, _winreg.HKEY_CURRENT_USER):
            try:
                key = _winreg.OpenKey(base, keyName)
                return registry_id
            except EnvironmentError:
                pass
    else:
        return None

def _is_komodo_installed(version, product_type, pretty_product_type):
    """If Komodo is installed return install info sufficient for
    uninstalling it. Otherwise, return None.
    """
    if sys.platform == "win32":
        # The right answer is to ask the MSI system, but (1) I can't
        # remember how to do that (answer is somewhere on WiX discuss
        # mailing list) and (2) that would likely imply dependencies.
        #
        # Instead we'll check Komodo's typical key in the registry.
        registry_id = _find_installed_komodo_registry_id(version, product_type)
        if registry_id is None:
            return None

        # Return the MSI ProductCode for this version of Komodo.
        product_code_from_registry_id = {
            "3.1": "{7238E62D-8657-4223-BBEC-BFCB43472267}",
            "3.5": "{DDB043A6-85F1-4B6D-85BE-D83DFB12F5C1}",
            "4.0": "{DAC6D1FF-A741-4F0D-AF57-FB4A08B417E9}",
            "4.0-ide": "{DAC6D1FF-A741-4F0D-AF57-FB4A08B417E9}",
            "4.0-edit": "{B34983C3-7BB8-4DA5-AF3C-F1F1C0ED6896}",
            "4.1-ide": "{e9067379-029a-480b-b89c-c9c5856d4aca}",
            "4.1-edit": "{8ec5e250-7b61-4e6f-88cb-eee0519f39ef}",
            "4.2-ide": "{f2fca603-6c72-447d-b79f-2eeb0a548d6a}",
            "4.2-edit": "{50e54ee6-75f5-4483-b73e-137b4207ca08}",
        }
        try:
            return product_code_from_registry_id[registry_id]
        except KeyError, ex:
            raise Error("don't know MSI ProductCode for Komodo %s %s: "
                        "you'll need to manually uninstall your Komodo "
                        "and then re-run this script"
                        % (pretty_product_type, version))

    elif sys.platform == "darwin":
        candidates = [
            "/Applications/Komodo %s %s.app" % (pretty_product_type, version),
            "/Applications/Komodo %s.app" % pretty_product_type,
            "/Applications/Komodo.app",
        ]
        for install_dir in candidates:
            if exists(install_dir):
                komodo = join(install_dir, "Contents", "MacOS", "komodo")
                installed_fullver = _capture_output('"%s" --version' % komodo)
                installed_ver = re.search(r"(\d+\.\d+)\.\d+",
                                          installed_fullver).group(1)
                if installed_ver == version:
                    return install_dir

    elif sys.platform.startswith("linux") or sys.platform.startswith("sunos"):
        candidates = [
            "~/opt/Komodo-%s-%s*" % (pretty_product_type, version),
#            "~/opt/Komodo-%s*" % version,
        ]
        for pattern in candidates:
            for install_dir in glob(expanduser(pattern)):
                if exists(install_dir):
                    return install_dir
        else:
            return None

    else:
        raise Error("unknown platform: `%s'" % sys.platform)


def _find_komodo_devbuilds_dir():
    """Find the plat-specific Komodo DevBuilds dir on crimper."""
    def gen_komodo_crimper_dirs():
        if sys.platform == "win32":
            yield r"\\crimper\apps\Komodo"
        else:
            yield "/nfs/crimper/home/apps/Komodo"
            yield "/mnt/crimper.home/apps/Komodo"
            yield "/mnt/crimper/apps/Komodo"
            yield "/mnt/crimper/home/apps/Komodo"
            yield "/mnt/crimper/Komodo"  # this is how JeffG mounts crimper
            yield "/Volumes/crimper/Komodo" # slightly diff't OSX mount - JeffG
            yield "/Volumes/crimper.activestate.com/Komodo"
        yield "crimper:/home/apps/Komodo"

    if sys.platform == "win32":
        platdir = "Windows"
    elif sys.platform.startswith("sunos"):
        platdir = "Solaris"
    elif sys.platform == "darwin":
        platdir = "MacOSX"
    elif sys.platform.startswith("linux"):
        platdir = "Linux"

    candidates = []
    for candidate in gen_komodo_crimper_dirs():
        candidates.append(candidate)
        if _is_remote_path(candidate) and _remote_exists(candidate):
            return urljoin(candidate, "DevBuilds", platdir)
        elif exists(candidate):
            return join(candidate, "DevBuilds", platdir)
    else:
        raise Error("could not find Komodo's crimper area: candidates='%s'"
                    % "', '".join(candidates))


def _find_latest_komodo_dev_build(version, pretty_product_type, platname,
                                  buildnum=None):
    """Find the latest Komodo dev build with the given details.

    "buildnum" can be a negative number to count back from end. E.g. -1
        is second lastest build.

    Returns a 3-tuple:
        (<komodo-full-version>, <komodo-build-num>, <path-to-installer>)
    """
    devbuilds_dir = _find_komodo_devbuilds_dir()

    if platname == "win32-x86":
        pattern = "Komodo-%s-%s.*-*.msi" % (pretty_product_type, version)
    elif platname.startswith("macosx"):
        pattern = "Komodo-%s-%s.*-*-%s.dmg" % (pretty_product_type, version, platname)
    else:
        pattern = "Komodo-%s-%s.*-*-%s.tar.gz" % (pretty_product_type, version, platname)

    if buildnum is None or buildnum < 0:
        buildnum_pat = r'(?P<buildnum>\d+)'
    else:
        buildnum_pat = r'(?P<buildnum>%s)' % buildnum

    package_pat = re.compile(
        r"""Komodo-%s
            -(?P<fullver>(?P<ver>.*?)(-\w+)?)
            -%s
            (-%s)?
            \.(msi|dmg|tar\.gz)$"""
        % (pretty_product_type, buildnum_pat, platname),
        re.VERBOSE
    )
    candidates = []
    if _is_remote_path(devbuilds_dir):
        matching_paths = _remote_glob(urljoin(devbuilds_dir, pattern))
    else:
        matching_paths = glob(join(devbuilds_dir, pattern))
    for path in matching_paths:
        matchResult = package_pat.match(basename(path))
        if matchResult:
            d = matchResult.groupdict()
            candidates.append(
                # "ver" excludes the optional "quality" part. We want to
                # ignore that part for sorting and use the build number to
                # differentiate the latest build of a particular version.
                (d["ver"], d["buildnum"], d["fullver"], path)
            )
    if not candidates:
        print "XXX buildnum: %r" % buildnum
        if buildnum is not None and buildnum >= 0:
            raise Error("could not find a Komodo %s dev build with "
                        "build number %s in `%s'"
                        % (version, buildnum, devbuilds_dir))
        else:
            raise Error("could not find a Komodo %s dev build: no packages "
                        "matching `%s' in `%s'"
                        % (version, pattern, devbuilds_dir))

    candidates.sort()
    if buildnum is None or buildnum >= 0:
        idx = -1
    else:
        idx = buildnum - 1
    return (candidates[idx][2],  # fullver
            candidates[idx][1],  # buildnum
            candidates[idx][3])  # path to installer package
    

def _get_komodo_platname():
    """Return the appropriate Komodo platform name for this machine.

    Avoid having a dependency on platinfo.py.
    """
    if sys.platform == "win32":
        platname = "win32-x86"
    elif sys.platform.startswith("sunos"):
        arch = os.uname()[4]
        assert arch == "sun4u", \
            "Komodo Solaris build don't support your architecture: '%s'" % arch
        platname = "solaris8-sparc"
    elif sys.platform == "darwin":
        arch = os.uname()[4]
        platname = {
            "Power Macintosh": "macosx-powerpc",
            "i386": "macosx-x86",
        }[arch]
    elif sys.platform.startswith("linux"):
        komodo_linux_libcpp_builds = [5, 6]
        avail_libcpps = [int(p[-1]) for p in glob("/usr/lib/libstdc++.so.?")]
        for libcpp in reversed(komodo_linux_libcpp_builds):
            if libcpp in avail_libcpps:
                break
        else:
            raise Error("there isn't a Komodo build for any of the available "
                        "libstdc++ libs on this Linux box (%s): Komodo "
                        "currently builds for libstc++ %s"
                        % (', '.join(map(str, avail_libcpps)),
                           ' and '.join(map(str, komodo_linux_libcpp_builds))))
        platname = "linux-libcpp%s-x86" % libcpp
    else:
        raise Error("unknown platform: '%s'" % sys.platform)
    return platname


def _get_latest_komodo_version():
    version_txt_url = "http://tl.activestate.com/p4unix/depot/main/Apps/Komodo-%s/src/version.txt" % g_ko_branch_name
    version = urllib.urlopen(version_txt_url).read()
    parts = re.split(r"[\.-]", version)
    return '.'.join(parts[:2])


# Recipe: run (0.5.3) in C:\trentm\tm\recipes\cookbook
_RUN_DEFAULT_LOGSTREAM = ("RUN", "DEFAULT", "LOGSTREAM")
def __run_log(logstream, msg, *args, **kwargs):
    if not logstream:
        pass
    elif logstream is _RUN_DEFAULT_LOGSTREAM:
        try:
            log
        except NameError:
            pass
        else:
            if hasattr(log, "debug"):
                log.debug(msg, *args, **kwargs)
    else:
        logstream(msg, *args, **kwargs)

def _run(cmd, logstream=_RUN_DEFAULT_LOGSTREAM):
    """Run the given command.

        "cmd" is the command to run
        "logstream" is an optional logging stream on which to log the 
            command. If None, no logging is done. If unspecifed, this 
            looks for a Logger instance named 'log' and logs the command 
            on log.debug().

    Raises OSError is the command returns a non-zero exit status.
    """
    __run_log(logstream, "running '%s'", cmd)
    retval = os.system(cmd)
    if hasattr(os, "WEXITSTATUS"):
        status = os.WEXITSTATUS(retval)
    else:
        status = retval
    if status:
        #TODO: add std OSError attributes or pick more approp. exception
        raise OSError("error running '%s': %r" % (cmd, status))

def _run_in_dir(cmd, cwd, logstream=_RUN_DEFAULT_LOGSTREAM):
    """Run the given command in the given working directory.

        "cmd" is the command to run
        "cwd" is the directory in which the commmand is run.
        "logstream" is an optional logging stream on which to log the 
            command. If None, no logging is done. If unspecifed, this 
            looks for a Logger instance named 'log' and logs the command 
            on log.debug().

    Raises OSError is the command returns a non-zero exit status.
    """
    old_dir = os.getcwd()
    try:
        os.chdir(cwd)
        __run_log(logstream, "running '%s' in '%s'", cmd, cwd)
        _run(cmd, logstream=None)
    finally:
        os.chdir(old_dir)


#---- mainline


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


def main(argv):
    usage = "usage: %prog [OPTIONS...]"
    version = "%prog "+__version__
    parser = optparse.OptionParser(prog="koup", usage=usage, version=version,
                                   description=__doc__)
    parser.add_option("-v", "--verbose", dest="log_level",
                      action="store_const", const=logging.DEBUG,
                      help="more verbose output")
    parser.add_option("-q", "--quiet", dest="log_level",
                      action="store_const", const=logging.WARNING,
                      help="quieter output")
    parser.add_option("-k", "--komodo-version",
                      help="Komodo version to install (e.g. 4.0). Defaults "
                           "to the version built out of the Komodo-%s branch."
                           % g_ko_branch_name)
    parser.add_option("-n", "--dry-run", action="store_true",
                      help="Don't upgrade, just describe what would be done")
    parser.add_option("-b", "--buildnum", type="int",
                      help="Restrict the search to the given Komodo "
                           "build number")
    parser.add_option("-c", "--channel",
                      help="Tweak update channel post-install to the given value.")
    parser.add_option("--ide", dest="product_type",
                      action="store_const", const="ide",
                      help="Install Komodo IDE (the default)")
    parser.add_option("--edit", dest="product_type",
                      action="store_const", const="edit",
                      help="Install Komodo Edit")
    parser.add_option("--all", dest="product_type",
                      action="store_const",
                      const=["edit", "ide"],
                      help="Install both Komodo Edit and IDE")
    parser.set_defaults(log_level=logging.INFO, komodo_version=None,
                        product_type="ide", buildnum=None, dry_run=False)
    opts, args = parser.parse_args()
    log.setLevel(opts.log_level)

    if isinstance(opts.product_type, list):
        for product_type in opts.product_type:
            koup(version=opts.komodo_version,
                 product_type=product_type,
                 buildnum=opts.buildnum,
                 dry_run=opts.dry_run,
                 channel=opts.channel)
    else:
        koup(version=opts.komodo_version,
             product_type=opts.product_type,
             buildnum=opts.buildnum,
             dry_run=opts.dry_run,
             channel=opts.channel)


if __name__ == "__main__":
    if sys.version_info[:2] <= (2,2): __file__ = sys.argv[0]
    _setup_logging()
    try:
        retval = main(sys.argv)
    except SystemExit:
        pass
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



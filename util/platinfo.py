#!/usr/bin/env python
# Copyright (c) 2004-2010 ActiveState Software Inc.
# Written by: Trent Mick <trentm@gmail.com>
# License: MIT License (http://www.opensource.org/licenses/mit-license.php)

"""
    platinfo.py -- standardized determination of platform info

        >>> from platinfo import PlatInfo
        >>> pi = PlatInfo()
        >>> pi.os
        'linux'
        >>> pi.arch
        'x86'

        # A number of pieces of info gathered (some of them plat-dependent).
        >>> pi.as_dict()
        {'arch': 'x86',
         'distro': 'SuSE',
         'distro_desc': 'SuSE Linux 9.0 (i586)',
         'distro_ver': '9.0',
         'libcpp': 'libcpp5',
         'lsb_version': '1.3',
         'name': 'linux-x86',
         'os': 'linux',
         'os_ver': '2.4.21'}

        # The default name is "<os>-<arch>"...
        >>> pi.name()   # default
        'linux-x86'
        >>> print pi
        linux-x86

        # ...but that can be customized with some rules.
        >>> pi.name('os', 'distro', 'arch')
        'linux-suse-x86'
        >>> pi.name('os', 'distro+distro_ver', 'arch')
        'linux-suse9-x86'
        >>> pi.name('os+os_ver[:2]', 'arch')
        'linux2.4-x86'
        >>> pi.name('os', 'arch', sep='/')
        'linux/x86'

        # The full name provide a little bit more info.
        >>> pi.fullname()
        'linux2.4-suse9-x86'

        # platname() is a shortcut for PlatInfo.name(...).
        >>> from platinfo import platname
        >>> platname('os', 'distro', 'arch')
        'linux-suse-x86'

    This module determines and returns standardized names for
    platforms, where the "standard" is Trent Mick's reasoning :)
    from experience building ActivePython on a fairly large number of
    platforms.
    
    The driving goal is to provide platform names that are:
    - relatively short
    - readable (as much as possible making matching the given name to an
      actually machine self-explanatory)
    - be capable enough to produce all names needed to distinguish all
      platform-specific application builds
    - generally safe for usage in filenames
    - not ugly (e.g. "MSWin32" is ugly)

    Generally some of these names match those used for ActiveTcl and
    ActivePerl where that makes sense (for example, "win32" is used
    instead of Perl's burdensome "MSWin32"). See the particular method
    docstrings for more details.
"""
# Development notes:
# - The name of this module is intentionally not "platform" to not
#   conflict with (Marc-Andre Lemburg's?) platform.py in the stdlib.
# - YAGNI: Having a "quick/terse" mode. Will always gather all possible
#   information unless come up with a case to NOT do so.

__version_info__ = (0, 14, 5)
__version__ = '.'.join(map(str, __version_info__))

import os
import sys
import re
import tempfile
import logging
import errno
import subprocess
from pprint import pprint
from os.path import exists
import warnings


log = logging.getLogger("platinfo")



#---- exceptions

class Error(Exception):
    pass

class InternalError(Error):
    def __str__(self):
        return Error.__str__(self) + """

* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
* Please report this error by adding a bug here:
*     http://code.google.com/p/platinfo/issues/list
* or, by sending an email to <trentm@gmail.com>.
*
* I'd like to keep improving `platinfo.py' to cover as many platforms
* as possible. Please be sure to include the error message above and
* any addition information you think might be relevant. Thanks!
* -- Trent
*
* platinfo version: %s
* python version: %s
* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *""" % (
    __version_info__, sys.version_info)

class LinuxDistroVersionWarning(RuntimeWarning):
    pass
warnings.simplefilter("once", LinuxDistroVersionWarning)



#---- public API

class PlatInfo(object):
    """Platform information for the current machine."""
    _known_oses = set(
        "win32 win64 hpux linux macosx aix solaris freebsd openbsd".split())
    _known_archs = set(
        "x86 powerpc ppc x64 x86_64 ia64 sparc sparc64 parisc".split())

    @classmethod
    def from_name(cls, name):
        """Create a PlatInfo instance from a platname string.

        This only knows how to deal with "os[os_ver]-arch[arch_ver]".
        For example:
            GOOD: win32-x86, hpux-parisc2.0, aix5-powerpc
            BAD:  linux-libcpp5-x86
        """
        parts = name.split('-')
        if len(parts) != 2:
            raise Error("cannot parse a platname that doesn't match "
                        "'os[os_ver]-arch[arch_ver]': %r" % name)
        data = {}
        if parts[0] in cls._known_oses:
            data["os"] = parts[0]
        else:
            for known_os in cls._known_oses:
                if parts[0].startswith(known_os):
                    data["os"] = known_os
                    data["os_ver"] = parts[0][len(known_os):]
                    break
            else:
                raise Error("could not part os-part of platform name: %r"
                            % parts[0])
        if parts[1] in cls._known_archs:
            data["arch"] = parts[1]
        else:
            for known_arch in cls._known_archs:
                if parts[1].startswith(known_arch):
                    data["arch"] = known_arch
                    data["arch_ver"] = parts[1][len(known_arch):]
                    break
            else:
                raise Error("could not part arch-part of platform name: %r"
                            % parts[1])
        return cls(**data)

    def __init__(self, **kwargs):
        """If created with no arguments, all available data for the current
        platform will be determine. If called with arguments, the PlatInfo
        will just use those as all platform info. E.g.,

            >>> p = PlatInfo(os='win32', arch='x86')
            >>> p.name()
            'win32-x86'
        """
        if kwargs:
            self.__dict__ = kwargs
        elif sys.platform == "win32":
            self._init_win32()
        elif sys.platform.startswith("linux"):
            self._init_linux()
        elif sys.platform.startswith("sunos"):
            self._init_solaris()
        elif sys.platform.startswith("hp-ux"):
            self._init_hpux()
        elif sys.platform.startswith("aix"):
            self._init_aix()
        elif sys.platform == "darwin":
            self._init_mac()
        elif sys.platform.startswith("freebsd"):
            self._init_freebsd()
        elif sys.platform.startswith("openbsd"):
            self._init_openbsd()
        elif sys.platform.startswith("netbsd"):
            self._init_netbsd()
        else:
            raise InternalError("unknown platform: '%s'" % sys.platform)

    def __str__(self):
        return self.name()

    def __repr__(self):
        args = ['%s=%r' % item for item in self.__dict__.items()]
        class_parts = [self.__class__.__name__]
        if self.__class__.__module__ != "__main__":
            class_parts.insert(0, self.__class__.__module__)
        return "%s(%s)" % ('.'.join(class_parts), ', '.join(args))

    def match(self, **kwargs):
        for name, value in kwargs.items():
            if getattr(self, name) != value:
                return False
        else:
            return True

    def name(self, *rules, **kwargs):
        """name([rules...]) --> platform name

        Return a string representation for this platform.

        Keyword args:
          'sep' is a string to use for joining platform data.
          'errors' is a string defining what to do if a given platform
              data does not exist for this platform. E.g. if the rule
              "distro" is given for Windows. Valid values are:
                  "ignore" - just skip that datum (this is the default)
                  "strict" - raise an Error
          'filesafe' is a boolean (default False) indicating if the
              returned name should be made safe for usage in a filename.
          'lower' is a boolean (default True) indicating if the returned
              name should be lowercased.

        Rule Syntax:
          os              # just a datum name
          os+os_ver       # use '+' to join without the 'sep'
        """
        sep = kwargs.get("sep", "-")
        errors = kwargs.get("errors", "ignore")
        filesafe = kwargs.get("filesafe", False)
        if filesafe:
            raise InternalError("name(..., filesafe=True) not yet implemented")
        lower = kwargs.get("lower", True)
        if not rules:
            rules = ("os", "arch")
        #print "RULES:", rules
        bits = []
        for rule in rules:
            bit = self._eval_rule(rule, errors=errors)
            if bit:
                bits.append(bit)
        if lower:
            return sep.join(bits).lower()
        else:
            return sep.join(bits)

    def fullname(self):
        parts = []
        if sys.platform == "win32":
            parts = ["os", "os_name"]
        else:
            parts = ["os+os_ver[:2]"]
        parts += ["distro+distro_ver", "libc", "glibc+glibc_ver[:2]",
                  "libcpp", "arch+arch_ver"]
        return self.name(*parts)

    _token_parser = re.compile(r"^([\w]+)(\[[\d:]+\])?$")
    def _eval_rule(self, rule, errors):
        assert errors in ("strict", "ignore")
        bits = []
        for token in rule.split('+'):
            m = self._token_parser.search(token)
            if not m:
                if errors == "strict":
                    raise Error("illegal token: '%s'" % token)
                elif errors == "ignore":
                    continue

            item_name, slice_str = m.groups()
            try:
                value = getattr(self, item_name)
            except AttributeError:
                if errors == "strict":
                    raise Error("no '%s' info for this platform" % item_name)
                elif errors == "ignore":
                    continue

            if slice_str and not item_name.endswith("_ver"):
                if errors == "strict":
                    raise Error("slicing only allowed on '*_ver' items: '%s'"
                                % token)
                elif errors == "ignore":
                    continue
            elif slice_str:
                parts = _split_ver(value)
                value = _join_ver( eval(str(parts)+slice_str) )

            bits.append(value)
        return ''.join(bits)

    def as_dict(self):
        """Return a dict representation of the platform info."""
        d = self.__dict__.copy()
        assert "name" not in d, "conflict with `name` datum"
        d["name"] = self.name()
        return d

    def as_xml(self):
        from xml.sax.saxutils import escape
        indent = ' '*2
        s = '<platinfo version="%s">\n' % __version__
        for key, value in self.as_dict().items():
            s += indent + '<%s>%s</%s>\n' % (key, escape(value), key)
        s += '</platinfo>'
        return s

    def as_yaml(self):
        # prefix with '---\n' YAML doc-separator?
        s = '--- platinfo version="%s"\n' % __version__
        parts = ["%s: %s" % i for i in self.as_dict().items()]
        s += '\n'.join(parts)
        return s

    def _init_win32(self):
        #XXX Right answer here is GetSystemInfo().
        #XXX Does this work on all Windows flavours?
        PROCESSOR_ARCHITECTURE = os.environ.get("PROCESSOR_ARCHITECTURE")
        if PROCESSOR_ARCHITECTURE == "IA64":
            self.os = "win64"
            self.arch = "ia64"
        elif PROCESSOR_ARCHITECTURE == "x86":
            self.os = "win32"
            self.arch = "x86"
        elif PROCESSOR_ARCHITECTURE == "AMD64":
            self.os = "win64"
            self.arch = "x64"
        else:
            raise InternalError("unknown Windows PROCESSOR_ARCHITECTURE: %r"
                                % PROCESSOR_ARCHITECTURE)

        # Get some additional info from Python's core platform.py, if
        # available.
        #XXX Would be nice to extend platform.py's win32_ver to use
        #    the extra OSVERSIONINFOEX structure elements (esp. service
        #    package version).
        try:
            import platform
        except ImportError:
            log.debug("cannot get extra windows os info: no platform.py")
        else:
            release, version, csd, ptype = platform.win32_ver()
            if not release:
                log.debug("platform.py could not get extra windows os info")
            if release: self.os_name = release
            if version: self.os_ver = version
            if csd:     self.os_csd = csd

    def _init_freebsd(self):
        self.os = "freebsd"
        uname = os.uname()
        self.os_ver = uname[2].split('-', 1)[0]

        arch = uname[-1]
        if re.match(r"i\d86", arch):
            self.arch = "x86"
        else:
            raise InternalError("unknown FreeBSD architecture: '%s'" % arch)

    def _init_openbsd(self):
        self.os = "openbsd"
        uname = os.uname()
        self.os_ver = uname[2].split('-', 1)[0]

        arch = uname[-1]
        if re.match(r"i\d86", arch):
            self.arch = "x86"
        elif arch == "amd64":
            self.arch = "x86_64"
        else:
            raise InternalError("unknown OpenBSD architecture: '%s'" % arch)

    def _init_netbsd(self):
        self.os = "netbsd"
        uname = os.uname()
        self.os_ver = uname[2].split('-', 1)[0]

        arch = uname[-1]
        if re.match(r"i\d86", arch):
            self.arch = "x86"
        else:
            raise InternalError("unknown NetBSD architecture: '%s'" % arch)

    def _init_linux(self):
        self.os = "linux"
        uname = os.uname()
        self.os_ver = uname[2].split('-', 1)[0]

        # Determine hardware type from 'uname -m' -- os.uname() is not
        # reliable: reports "i686" on iron (a Linux/IA64 box).
        o = os.popen('uname -m 2> /dev/null')
        arch = o.read().strip()
        o.close()
        if arch == "ia64":
            self.arch = "ia64"
        elif re.match("i\d86", arch):
            self.arch = "x86"
        elif arch == "x86_64":
            self.arch = "x86_64"
        elif arch == "ppc":
            self.arch = "ppc"
        else:
            raise InternalError("unknown Linux architecture: '%s'" % arch)
        self._set_linux_distro_info()
        lib_info = _get_linux_lib_info()
        if "libstdc++" in lib_info:
            self.libcpp = "libcpp" + lib_info["libstdc++"]
        if "libc" in lib_info:
            # For now, only the major 'libc' version number is used.
            self.libc = "libc" + lib_info["libc"].split('.')[0]
        if "glibc" in lib_info:
            self.glibc = "glibc"
            self.glibc_ver = lib_info["glibc"]

    def _init_solaris(self):
        self.os = "solaris"
        uname = os.uname()
        if uname[2].startswith("5."):
            self.os_ver = uname[2].split(".", 1)[1]
        else:
            raise InternalError("unknown Solaris version: '%s'" % uname[2])
        if uname[4].startswith("sun4"):
            self.arch = "sparc"
            arch_ver = _get_sparc_arch_ver()
            if arch_ver is not None:
                self.arch_ver = arch_ver
                if int(arch_ver) >= 9:
                    self.arch = "sparc64"
        elif uname[4].startswith("i86pc"):
            self.arch = "x86"
        else:
            raise InternalError("unknown Solaris architecture: '%s'" % uname[4])

    def _init_hpux(self):
        self.os = "hpux"
        uname = os.uname()

        if uname[4] == "ia64":
            self.arch = "ia64"
        elif uname[4] == "9000/800":
            self.arch = "parisc"
            self.arch_ver = _get_hpux_parisc_arch_ver()
        else:
            raise InternalError("unknown HP-UX architecture: '%s'" % uname[4])

        try:
            self.os_ver = uname[2].split('.', 1)[1]   # e.g. "B.11.00"
        except IndexError, ex:
            raise InternalError("unknown HP-UX version: could not "
                                "parse '%s' from uname" % uname[2])

    def _init_aix(self):
        uname = os.uname()
        self.os = "aix"
        self.os_ver = "%s.%s" % (uname[3], uname[2])

        # Determine processor type from 'uname -p' -- os.uname() does not
        # have this.
        o = os.popen('uname -p 2> /dev/null')
        self.arch = o.read().strip()
        o.close()

    def _init_mac(self):
        # Determine processor type from 'uname -p' -- os.uname() does not
        # have this.
        o = os.popen('uname -p 2> /dev/null')
        self.arch = {"powerpc": "powerpc",
                     "i386":    "x86"}[o.read().strip()]
        o.close()

        # Historically Python code (e.g. platform.py) has used the
        # Gestalt Manager to retrieve Mac OS system info. However, this
        # has problems on macosx-x86. As well,
        # <http://tinyurl.com/9ssrn> says this:
        #
        #   A better way to obtain version information in Mac OS X is to
        #   read the system version information from the following file:
        #
        #   /System/Library/CoreServices/SystemVersion.plist
        #
        # Note: If there end up being problems using this, then try
        # getting info from `sw_vers`.
        getters = [
            self._get_macos_ver_info_from_plist,
            self._get_macos_ver_info_from_gestalt,
        ]
        for getter in getters:
            ver_info = getter()
            if ver_info:
                assert "os_ver" in ver_info
                for n,v in ver_info.items():
                    setattr(self, n, v)
                if self.os_ver.startswith("10."):
                    self.os = "macosx"
                else:
                    self.os = "macos"
                break
        else:
            self.os = "macos"
            import warnings
            warnings.warn("could not determine Mac OS version info: "
                          "consider adding support for parsing `sw_vers`")

        self.darwin_ver = os.uname()[2] 

    def _get_macos_ver_info_from_gestalt(self):
        import gestalt
        import MacOS
        try:
            sysv = gestalt.gestalt("sysv")
        except MacOS.Error, ex:
            # On Mac OS X/Intel (at least on the early release dev
            # boxes) the Gestalt Manager does not seem to be intialized
            # with the standard selectors -- or the equivalent.
            # Requesting information on "sysv", "sysu", etc. all return:
            #   gestaltUndefSelectorErr (-5551)
            #   Specifies an undefined selector was passed to the
            #   Gestalt Manager.
            pass
        else:
            def bcd2int(bcd): return int(hex(bcd)[2:])
            major = bcd2int((sysv & 0xFF00) >> 8)
            minor = (sysv & 0x00F0) >> 4
            patch = (sysv & 0x000F)
            return {
                "os_ver": "%d.%d.%d" % (major, minor, patch),
            }

    def _get_macos_ver_info_from_plist(self):
        """Retrive Mac OS system information from
            /System/Library/CoreServices/SystemVersion.plist
        as suggested here:
            http://tinyurl.com/9ssrn
        """
        plist_path = "/System/Library/CoreServices/SystemVersion.plist"
        if not exists(plist_path):
            return
        try:
            from plistlib import Plist
        except ImportError:
            return
        plist = Plist.fromFile(plist_path)
        return {
            "os_ver": plist["ProductVersion"],
            "os_build": plist["ProductBuildVersion"],
            "os_name": plist["ProductName"],
        }

    def _get_linux_lsb_release_info(self):
        """Some Linux distros have a `lsb_release` that provides some
        data about the distro.
        """
        try:
            try:
                import subprocess
            except ImportError:
                i,o,e = os.popen3("lsb_release --all")
                i.close()
                stdout = o.read()
                stderr = e.read()
                o.close()
                retval = e.close()
            else:
                p = subprocess.Popen(["lsb_release", "--all"],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = p.communicate()
                retval = p.wait()
        except OSError:
            # Can happen if "lsb_release" did not exist, bug 82403.
            retval = 1   # an error

        d = {}
        if retval:
            return {} # Running lsb_release failed
        patterns = {
            "distro": re.compile("^Distributor ID:\s+(.*?)\s*$"),
            "distro_desc": re.compile("^Description:\s+(.*?)\s*$"),
            "distro_ver": re.compile("^Release:\s+(.*?)\s*$"),
            "distro_codename": re.compile("^Codename:\s+(.*?)\s*$"),
            "lsb_version": re.compile("^LSB Version:\s+(.*?)\s*$"),
        }
        for line in stdout.splitlines(0):
            for name, pattern in patterns.items():
                match = pattern.search(line)
                if match:
                    value = match.group(1)
                    if value != "n/a":
                        d[name] = value
        return d

    def _get_linux_release_file_info(self):
        try:
            etc_files = os.listdir("/etc")
        except EnvironmentError:
            return {}

        # A good list of release-files for various Linux distros is
        # here: http://linuxmafia.com/faq/Admin/release-files.html
        d = {}
        release_file_pat = re.compile(r'(\w+)[-_](release|version)')
        candidate_etc_files = []
        for etc_file in etc_files:
            m = release_file_pat.match(etc_file)
            if m:
                candidate_etc_files.append((m.group(1), "/etc/"+etc_file))
        if not candidate_etc_files:
            return {}

        patterns = {
            "redhat": re.compile("^Red Hat Linux release ([\d\.]+)"),
            # As of release 7, "Fedora Core" is not called "Fedora".
            "fedora": re.compile("^Fedora release ([\d\.]+)"),
            "fedoracore": re.compile("^Fedora Core release ([\d\.]+)"),
            "mandrake": re.compile("^Mandrake Linux release ([\d\.]+)"),
            # Ignoring the different RHEL flavours (AS, ES, WS) for now.
            "rhel": re.compile("^Red Hat Enterprise Linux \w{2} release ([\d\.]+)"),
            "suse": re.compile("^SuSE Linux ([\d\.]+)"),
            "opensuse": re.compile("^openSUSE ([\d\.]+)"),
            "debian": re.compile("^([\d\.]+)"),
            "slackware": re.compile("^Slackware ([\d\.]+)"),
            "gentoo": re.compile("^Gentoo Base System release ([\d\.]+)"),
        }

        errmsgs = []
        for distro_family, etc_path in candidate_etc_files:
            f = open(etc_path, 'r')
            first_line = f.readline().rstrip()
            f.close()
            for distro, pattern in patterns.items():
                m = pattern.search(first_line)
                if m:
                    d["distro_family"] = distro_family
                    d["distro"] = distro
                    d["distro_ver"] = m.group(1)
                    if first_line.strip() != m.group(1):
                        d["distro_desc"] = first_line.strip()
                    break
            errmsgs.append("first line of '%s' (%s)" % (etc_path, first_line))
            if d:
                break
        else:            
            # If we have a release-file, just fill in "distro_family"
            # and "distro" and move on. For example, Arch Linux's
            # release file is *empty*.
            if candidate_etc_files:
                d["distro_family"] = distro_family = candidate_etc_files[0][0]
                d["distro"] = distro_family.lower()
                warnings.warn("could not determine linux distro_ver %s"
                                % " or ".join(errmsgs),
                              LinuxDistroVersionWarning)
        return d

    def _set_linux_distro_info(self):
        """Determine the following Linux distribution information:

            distro
            distro_ver (maybe)
            distro_family (maybe)
                Distro families are "redhat", "debian", and "suse". For
                example, Mandrake Linux is a member of the "redhat"
                distro family, Ubuntu is a member of the "debian" family.
            distro_codename (maybe)
            distro_description (maybe)
        """
        assert sys.platform.startswith("linux")

        # First try to use `lsb_release`.
        # - Ubuntu Linux includes "/etc/debian_version" but has its
        #   useful version info in "/etc/lsb-release" (best parsed from
        #   `lsb_release`).
        # - Is there reason to prefer "/etc/foo[-_](release|version)"
        #   info over `lsb_release` for any Linux distro?
        d = self._get_linux_lsb_release_info()
        if "distro" in d and "distro_ver" in d:
            for k, v in d.items():
                setattr(self, k, v)
            return

        # Then try to find a release/version file in "/etc".
        # - Algorithm borrows from platform.py.
        d = self._get_linux_release_file_info()
        if "distro" in d:
            for k, v in d.items():
                setattr(self, k, v)
            return

        # Then try to use Python's platform.py to help.
        try:
            import platform
        except ImportError:
            pass
        else:
            distro, distro_ver, distro_id = platform.dist()
            if distro and distro_ver:
                self.distro = distro
                self.distro_ver = distro_ver
                return

        raise InternalError("unknown Linux distro: no `lsb_release`, "
                            "couldn't find a '/etc/*[-_](version|release)' "
                            "file, and Python's platform.py couldn't "
                            "identify the distro either")


def platname(*rules, **kwargs):
    """platname([rules...]) --> platform name

    Return a string representation for this platform.

    Keyword args:
      'sep' is a string to use for joining platform data.
      'errors' is a string defining what to do if a given platform
          data does not exist for this platform. E.g. if the rule
          "distro" is given for Windows. Valid values are:
              "ignore" - just skip that datum (this is the default)
              "strict" - raise an Error
      'filesafe' is a boolean (default False) indicating if the
          returned name should be made safe for usage in a filename.
      'lower' is a boolean (default True) indicating if the returned
          name should be lowercased.

    Rule Syntax:
      os              # just a datum name
      os+os_ver       # use '+' to join without the 'sep'
    """
    return PlatInfo().name(*rules, **kwargs)



#---- internal support stuff

# Note: Not using `subprocess.CalledProcessError` because that isn't in
# Python 2.4.
class RunError(Exception): pass
class ExecutableNotFoundError(RunError): pass
class NonZeroReturnCodeError(RunError): pass

def _run(args, ignore_stderr=False):
    """Run the given command.

    @param args {str|list} Command strong or sequence of program arguments. The
          program to execute is normally the first item in the args
          sequence or the string if a string is given.
    @param ignore_stderr {bool} If True, return only stdout; otherwise
        return both stdout and stderr combined (2>&1)
    @returns {str} The program output.
    @raises {RunError} `ExecutableNotFoundError` or `NonZeroReturnCodeError`.
    """
    if ignore_stderr:
        stderr_pipe = subprocess.PIPE
    else:
        stderr_pipe = subprocess.STDOUT
        
    try:
        p = subprocess.Popen(args=args, 
                shell=False, # prevent obtrusive shell warnings
                stdout=subprocess.PIPE, stderr=stderr_pipe)
    except OSError, e:
        if e.errno == errno.ENOENT:
            # `exe` not found
            raise ExecutableNotFoundError('The command "%s" cannot be run: %s'
                % (args, e))
        raise

    stdout, stderr = p.communicate()
    if p.returncode:
        raise NonZeroReturnCodeError('"%s" returned non-zero return code (%d)' 
            % (args, p.returncode))
    return stdout


# Recipe: ver (0.1) in C:\trentm\tm\recipes\cookbook
def _split_ver(ver_str):
    """Parse the given version into a tuple of "significant" parts.
   
        >>> _split_ver("4.1.0")
        ('4', '1', '0')
        >>> _split_ver("1.3a2")
        ('1', '3', 'a', '2')
    """
    bits = [b for b in re.split("(\.|[a-z])", ver_str) if b != '.']
    return tuple(bits)

def _join_ver(ver_tuple):
    """Join the given version-tuple, inserting '.' as appropriate.
    
        >>> _join_ver( ('4', '1', '0') )
        "4.1.0"
        >>> _join_ver( ('1', '3', 'a', '2') )
        "1.3a2"
    """
    def isint(s):
        try:
            int(s)
        except ValueError:
            return False
        else:
            return True

    dotted = []
    for bit in ver_tuple:
        if dotted and isint(dotted[-1]) and isint(bit):
            dotted.append('.')
        dotted.append(str(bit))
    return ''.join(dotted)

def _get_linux_lib_info():
    """Return a dict of default lib versions for a build on linux.
    
    For example:
        {"libstdc++": "5", "libc": "6", "glibc": "2.3.3"}
    
    The 'glibc' version is only returned if 'libc' is >=6.
    
    Some notes on Linux libc versions
    ---------------------------------
    
    From http://sourceware.org/glibc/glibc-faq.html#s-2.1
        libc-4      a.out libc
        libc-5      original ELF libc
        libc-6      GNU libc
    
    But what are libc.so.7 and libc.so.8 that I see in Google searches (but
    not yet in any Linux installs I have access to)?
    """
    assert sys.platform.startswith("linux")
    tmpdir = _create_temp_dir()
    try:
        # Compile a test C++ file and get its object dump.
        cxxfile = os.path.join(tmpdir, "lib-info.cxx")
        f = open(cxxfile, 'w')
        try:
            f.write("""
#include <stdio.h>
#include <stdlib.h>
int main(int argc, char **argv) { exit(0); }
""")
        finally:
            f.close()
        currdir = os.getcwd()
        os.chdir(tmpdir)
        try:
            try:
                _run(['g++', cxxfile], ignore_stderr=True)
            except RunError, e:
                log.debug("could not compile test C++ file with g++: %s", e)
                return {}
            objdump = os.popen('objdump -p a.out').read()
        finally:
            os.chdir(currdir)

        # Parse the lib versions from the object dump.
        # e.g.: libstdc++-libc6.2-2.so.3
        patterns = {
            "libstdc++": re.compile(r'NEEDED\s+libstdc\+\+(-libc\d+\.\d+\-\d+)?\.so\.(?P<ver>.*)'),
            "libc": re.compile(r'NEEDED\s+libc\.so\.(?P<ver>.*)'),
        }
        lib_info = {}
        for name, pattern in patterns.items():
            match = pattern.search(objdump)
            if not match:
                raise InternalError("could not find 'NEEDED %s...' in "
                                    "objdump of compiled test C++ file"
                                    % name)
            lib_info[name] = match.group("ver")
    finally:
        _rmtree(tmpdir)

    # If this is glibc, get its version.
    if int(_split_ver(lib_info["libc"])[0]) >= 6:
        libc_so = os.path.join("/lib", "libc.so."+lib_info["libc"])
        o = os.popen(libc_so)
        try:
            libc_so_ver_line = o.readline().strip()
        finally:
            retval = o.close()
        if retval:
            raise InternalError("error running '%s'" % libc_so)
        # e.g.:
        #   GNU C Library stable release version 2.3.3 (20040917), by R...
        #   GNU C Library stable release version 2.5, by Roland McGrath et al.
        pattern = re.compile(r"^GNU C Library.*?(\d+\.\d+(\.\d+)?)")
        match = pattern.search(libc_so_ver_line)
        if not match:
            raise InternalError("error determining glibc version from '%s'"
                                % libc_so_ver_line)
        lib_info["glibc"] = match.group(1)

    return lib_info

def _get_sparc_arch_ver():
    # http://developers.sun.com/solaris/developer/support/driver/64bit-faqs.html#QA12.12
    # http://docs.sun.com/app/docs/doc/816-5175/isalist-5
    o = os.popen("isalist")
    instruct_sets = o.read().split()
    retval = o.close()
    if retval:
        raise InternalError("error determining SPARC architecture version")
    first = instruct_sets[0]
    if first.startswith("sparcv9"):
        return '9'
    elif first.startswith("sparcv8"):
        return '8'
    elif first.startswith("sparcv7"):
        return '7'
    elif first == "sparc":
        return '8'
    else:
        import warnings
        warnings.warn("could not determine SPARC architecture version "
                      "from first `isalist` output: %r" % first)
        return None

def _get_hpux_parisc_arch_ver():
    assert sys.platform.startswith("hp-ux")
    # Get the model name from `model` and parse out the model name, e.g:
    #   9000/800/L2000-44  ->  L2000-44
    #   9000/800/A180c     ->  A180c
    o = os.popen("model")
    model = o.read().strip()
    retval = o.close()
    if retval:
        raise InternalError("error determining HP-UX PA-RISC model name")
    model = model.split('/')[-1]

    # Lookup the model name in sched.models model database.
    sched_models_paths = [
        "/usr/sam/lib/mo/sched.models",
        "/opt/langtools/lib/sched.models"
    ]
    for sched_models_path in sched_models_paths:
        fin = open(sched_models_path, 'r')
        try:
            for line in fin:
                if line.lstrip().startswith("/*"): continue
                db_model, db_arch, db_paname = line.split()
                if db_model.lower() == model.lower():
                    # e.g. "1.1e" -> "1.1"
                    arch_ver_pat = re.compile(r"^(\d\.\d)")
                    return arch_ver_pat.search(db_arch).group(1)
        finally:
            fin.close()
    raise InternalError("could not find '%s' model name in HP-UX "
                        "PA-RISC model database, '%s'" 
                        % (model, sched_models_path))


def _create_temp_dir():
    """Create a temporary directory and return the path to it."""
    if hasattr(tempfile, "mkdtemp"): # use the newer mkdtemp is available
        path = tempfile.mkdtemp()
    else:
        path = tempfile.mktemp()
        os.makedirs(path)
    return path

def _rmtree_on_error(rmFunction, filePath, excInfo):
    if excInfo[0] == OSError:
        # presuming because file is read-only
        os.chmod(filePath, 0777)
        rmFunction(filePath)

def _rmtree(dirname):
    import shutil
    shutil.rmtree(dirname, 0, _rmtree_on_error)



#---- mainline

# Recipe: banner (1.0) in C:\trentm\tm\recipes\cookbook
def _banner(text, ch='=', length=78):
    """Return a banner line centering the given text.
    
        "text" is the text to show in the banner. None can be given to have
            no text.
        "ch" (optional, default '=') is the banner line character (can
            also be a short string to repeat).
        "length" (optional, default 78) is the length of banner to make.

    Examples:
        >>> banner("Peggy Sue")
        '================================= Peggy Sue =================================='
        >>> banner("Peggy Sue", ch='-', length=50)
        '------------------- Peggy Sue --------------------'
        >>> banner("Pretty pretty pretty pretty Peggy Sue", length=40)
        'Pretty pretty pretty pretty Peggy Sue'
    """
    if text is None:
        return ch * length
    elif len(text) + 2 + len(ch)*2 > length:
        # Not enough space for even one line char (plus space) around text.
        return text
    else:
        remain = length - (len(text) + 2)
        prefix_len = remain / 2
        suffix_len = remain - prefix_len
        if len(ch) == 1:
            prefix = ch * prefix_len
            suffix = ch * suffix_len
        else:
            prefix = ch * (prefix_len/len(ch)) + ch[:prefix_len%len(ch)]
            suffix = ch * (suffix_len/len(ch)) + ch[:suffix_len%len(ch)]
        return prefix + ' ' + text + ' ' + suffix


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

def main(argv=None):
    import optparse
    
    if argv is None:
        argv = sys.argv

    _setup_logging()
    usage = "usage: %prog [NAME-RULES...]"
    version = "%prog "+__version__
    desc = """\
Determine and display platform information. 'platinfo' is really
designed to be used as a Python module. See the module docstring for
more information."""
    parser = optparse.OptionParser(prog="platinfo", usage=usage,
                                   version=version,
                                   description=desc)
    parser.add_option("-v", "--verbose", dest="log_level",
                      action="store_const", const=logging.DEBUG,
                      help="more verbose output")
    parser.add_option("-q", "--quiet", dest="log_level",
                      action="store_const", const=logging.WARNING,
                      help="quieter output")
    parser.add_option("-n", "--name", action="store_const",
                      dest="format", const="name",
                      help="output string name")
    parser.add_option("-f", "--full-name", action="store_const",
                      dest="format", const="fullname",
                      help="a more detailed string name")
    parser.add_option("-d", "--dict", action="store_const",
                      dest="format", const="dict",
                      help="output Python dict representation")
    parser.add_option("-x", "--xml", action="store_const",
                      dest="format", const="xml",
                      help="output XML representation")
    parser.add_option("-y", "--yaml", action="store_const",
                      dest="format", const="yaml",
                      help="output YAML representation")
    parser.add_option("-a", "--all", action="store_const",
                      dest="format", const="all",
                      help="output all representations")
    parser.set_defaults(log_level=logging.INFO)
    opts, rules = parser.parse_args()
    log.setLevel(opts.log_level)

    pi = PlatInfo()
    WIDTH=75
    if opts.format is None:
        if rules:
            print pi.name(*rules)
        else:
            print "%s (%s)" % (pi.name(), pi.fullname())
    if opts.format == "name":
        print pi.name(*rules)
    if opts.format == "fullname":
        print pi.fullname()
    elif opts.format == "dict":
        if sys.version_info[:2] >= (2,4):
            pprint(pi.as_dict(), width=WIDTH)
        else:
            from pprint import PrettyPrinter
            pp = PrettyPrinter(width=WIDTH)
            pp.pprint(pi.as_dict())
    elif opts.format == "xml":
        print pi.as_xml()
    elif opts.format == "yaml":
        print pi.as_yaml()
    elif opts.format == "all":
        print _banner("platform info", length=WIDTH)
        print pi.name(*rules)
        print _banner("as_dict", '-', length=WIDTH)
        if sys.version_info[:2] >= (2,4):
            pprint(pi.as_dict(), width=WIDTH)
        else:
            from pprint import PrettyPrinter
            pp = PrettyPrinter(width=WIDTH)
            pp.pprint(pi.as_dict())
        print _banner("as_xml", '-', length=WIDTH)
        print pi.as_xml()
        print _banner("as_yaml", '-', length=WIDTH)
        print pi.as_yaml()
        print _banner(None, length=WIDTH)


if __name__ == "__main__":
    sys.exit(main(sys.argv))


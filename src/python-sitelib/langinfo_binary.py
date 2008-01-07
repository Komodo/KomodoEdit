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

"""LangInfo definitions for some binary file types."""

from langinfo import LangInfo



class ELFLangInfo(LangInfo):
    """ELF-format binary (e.g. a standard executable on Linux)"""
    name = "ELF"

    # From '/usr/share/file/magic':
    #   0	string		\177ELF		ELF
    magic_numbers = [(0, 'string', '\177ELF')]

class MachOUniversalLangInfo(LangInfo):
    name = "Mach-O universal"

    # See '/usr/share/file/magic' for the full details on collision
    # between compiled Java class data and Mach-O universal binaries and
    # the hack to distinguish them.
    #   0	belong		0xcafebabe
    #TODO: check with a 64-bit Mach-O universal
    magic_numbers = [(0, '>L', int('0xcafebabe', 16))]

class MachOLangInfo(LangInfo):
    name = "Mach-O"

    # From '/usr/share/file/magic':
    #   0	lelong&0xfffffffe	0xfeedface	Mach-O
    #   0	belong&0xfffffffe	0xfeedface	Mach-O
    # Note: We are not current handling the '&0xfffffffe'.
    #
    #TODO: check with a 64-bit Mach-O
    magic_numbers = [(0, '<L', int('0xfeedface', 16)),
                     (0, '>L', int('0xfeedface', 16))]

class WindowsExeLangInfo(LangInfo):
    name = "Windows executable"
    exts = [".exe", ".dll"]

    # From '/usr/share/file/magic':
    #   0	string	MZ		MS-DOS executable (EXE)
    magic_numbers = [(0, "string", "MZ")]

class CompiledJavaClassLangInfo(LangInfo):
    name = "compiled Java class"
    exts = [".class"]
    # See MachOUniversalLangInfo above. There is a collision in the
    # magic number of Mach-O universal binaries and Java .class files.
    # For now we rely on the '.class' extension to properly identify
    # before magic number checking is done.
    magic_numbers = None

class ZipLangInfo(LangInfo):
    name = "Zip archive"
    exts = [".zip"]
    magic_numbers = [(0, "string", "PK\003\004")]

class JarLangInfo(ZipLangInfo):
    name = "Jar archive"
    exts = [".jar"]

class IcoLangInfo(LangInfo):
    name = "Windows icon"
    exts = [".ico"]

class IcnsLangInfo(LangInfo):
    name = "Mac icon"
    exts = [".icns"]

class XPMLangInfo(LangInfo):
    name = "XPM"
    exts = [".xpm"]
    magic_numbers = [(0, "string", "/* XPM */")]

class PSDLangInfo(LangInfo):
    name = "Adobe Photoshop Document"
    exts = [".psd"]
    magic_numbers = [(0, "string", "8BPS")]

class PNGLangInfo(LangInfo):
    name = "PNG"
    exts = [".png"]
    magic_numbers = [(0, "string", "\x89PNG")]

class GIFLangInfo(LangInfo):
    name = "GIF"
    exts = [".gif"]
    magic_numbers = [(0, "string", "GIF8")]

class JPEGLangInfo(LangInfo):
    name = "JPEG"
    exts = [".jpg", ".jpeg"]
    # From '/usr/share/file/magic':
    #   0	beshort		0xffd8		JPEG image data
    magic_numbers = [(0, ">H", int("0xffd8", 16))]

class BMPLangInfo(LangInfo):
    name = "Bitmap image"
    exts = [".bmp"]
    magic_numbers = [(0, "string", "BM")]


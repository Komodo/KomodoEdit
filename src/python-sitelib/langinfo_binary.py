# Copyright (c) 2007 ActiveState Software Inc.

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


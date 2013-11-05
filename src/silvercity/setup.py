#!/usr/bin/env python 
 
from distutils.core import setup, Extension 
from distutils.command.build_ext import build_ext
from distutils.command.install_data import install_data
import sys 
import os

class komodo_build_ext(build_ext):
    def build_extensions(self):
        if sys.platform.startswith("linux"):
            # Allow a custom C compiler through the environment variables. This
            # allows Komodo to build using a gcc compiler that's not first on
            # the path.
            compiler = os.environ.get('CC')
            if compiler is not None:
                import sysconfig
                (ccshared,cflags) = sysconfig.get_config_vars('CCSHARED','CFLAGS')
                args = {}
                args['compiler_so'] = compiler + ' ' + ccshared + ' ' + cflags
                self.compiler.set_executables(**args)
        elif sys.platform == "darwin":
            compiler = os.environ.get('CC')
            if compiler is not None:
                import sysconfig
                (ccshared,cflags) = sysconfig.get_config_vars('CCSHARED','CFLAGS')
                args = {}
                # clang does not support the '-std=gnu99' option - so remove it.
                cflags = cflags.replace('-std=gnu99', '')
                args['compiler_so'] = compiler + ' ' + ccshared + ' ' + cflags
                self.compiler.set_executables(**args)
            
        build_ext.build_extensions(self)

class fixed_install_data(install_data):
    """Sets install_dir to be install directory of extension
    modules, instead of the root Python directory"""
    
    def finalize_options(self):
        if self.install_dir is None:
            installobj = self.distribution.get_command_obj('install')
            self.install_dir = installobj.install_platlib
        install_data.finalize_options(self)

src_files = []

# Add Python extension source files
src_files.extend(
        [os.path.join('PySilverCity/Src', file) for file in
            ["PyLexerModule.cxx",
           "PyPropSet.cxx",
           "PySilverCity.cxx",
           "PyWordList.cxx"]
        ]
    )

# Add library source files
src_files.extend(
        [os.path.join('Lib/Src', file) for file in
            ["BufferAccessor.cxx",
             "LexState.cxx",
             "LineVector.cxx",
             "SC_PropSet.cxx",
             "Platform.cxx"]
         ]
    )

# Add Scintilla support files
scintilla_scr = '../scintilla/src'
scintilla_include = '../scintilla/include'
scintilla_lexlib = '../scintilla/lexlib'
scintilla_lexers = '../scintilla/lexers'
src_files.extend(
        [os.path.join(scintilla_scr, file) for file in
            ["KeyMap.cxx",
             "Catalogue.cxx",
            "UniConversion.cxx"]
        ]
    )
src_files.extend(
        [os.path.join(scintilla_lexlib, file) for file in
            ["WordList.cxx",
             "PropSetSimple.cxx",
             "Accessor.cxx",
             "CharacterCategory.cxx",
             "CharacterSet.cxx",
             "LexerBase.cxx",
             "LexerNoExceptions.cxx",
             "LexerSimple.cxx",
             "LexerModule.cxx",
             "StyleContext.cxx",]
        ]
    )

# Add Scintilla lexers
for file in os.listdir(scintilla_lexers):
    file = os.path.join(scintilla_lexers, file)
    if os.path.basename(file).startswith('Lex') and \
       os.path.splitext(file)[1] == '.cxx':
        src_files.append(file)
        
include_dirs = [scintilla_scr,
                scintilla_include,
                scintilla_lexlib,
                scintilla_lexers,
                'Lib/Src']

data_files = ['CSS/default.css']
libraries = []
defines = []
extra_compile_args = []
extra_link_args = []
extra_objects = []

scripts = [os.path.join('PySilverCity','Scripts', script) for script in
           ['source2html.py',
            'cgi-styler.py',
            'cgi-styler-form.py']]


# Windows specific definitions
if sys.platform.startswith("win32"):
    defines.append(('WIN32',None))
    libraries.append('kernel32')
    extra_objects = ['libpcre.lib']
    # Build debug symbols, even for release (they're not shipped)
    extra_compile_args.append("-Zi")
    extra_link_args.append("-DEBUG")
elif sys.platform.startswith("sunos"):
    os.environ['CC'] = 'CC'
    libraries.append('Crun')            # C++ runtime
    extra_compile_args.append('-KPIC')  # for making shared .o's
    # These would be for g++, but APy links with CC -G, so build with CC
    #libraries.append('stdc++')
    #extra_compile_args.append('-fPIC')
    #extra_link_args.append('-shared')
    extra_objects = ['libpcre.a']
else:
    if sys.platform.startswith("linux"):
        if not os.environ.get('CC'):
            os.environ['CC'] = 'g++'
        defines.append(('GTK',None)) 
    extra_objects = ['libpcre.a']

    # Depending on your gcc and Python version, one of both of the following lines might
    # be necessary
    
    # libraries.append('gcc')
    # libraries.append('stdc++')

# KOMODO - define special UDL debug environment variables when necessary.
if "UDL_DEBUG" in os.environ:
    defines.append(('UDL_DEBUG','1'))
if "UDL_DEBUG_TIME" in os.environ:
    defines.append(('UDL_DEBUG_TIME','1'))

setup(  name = "SilverCity", 
        version = "0.9.5", 
        description = "Python interface to Scintilla lexers", 
        author = "Brian Quinlan",
        long_description =
"""SilverCity is a lexing package, based on Scintilla, that can provide lexical
analysis for over 20 programming and markup langauges. Included in the package
are modules to convert source code to syntax-styled HTML.""",
        
        author_email = "brian@sweetapp.com", 
        url = "http://silvercity.sourceforge.net",
        licence = "BSD-style",
        ext_package = "SilverCity",
        cmdclass = {'install_data': fixed_install_data,
                    'build_ext': komodo_build_ext},
        ext_modules = [Extension("_SilverCity", src_files,   
                        define_macros = defines, 
                        include_dirs = include_dirs,
                        libraries = libraries,
                        extra_compile_args = extra_compile_args,
                        extra_link_args = extra_link_args,
                        extra_objects = extra_objects,
                                 )],
        data_files = [('SilverCity', data_files)],
        scripts = scripts,
        package_dir = {'': 'PySilverCity'},
        py_modules =["SilverCity.__init__",
                     "SilverCity.DispatchHandler",
                     "SilverCity.HTMLGenerator",
                     "SilverCity.Keywords",
                     "SilverCity.LanguageInfo",
                     "SilverCity.Lexer",
                     "SilverCity.ScintillaConstants",
                     "SilverCity.Utils",
                     # Lexers
                     "SilverCity.CPP",
                     "SilverCity.CSS",
                     "SilverCity.HyperText",
                     "SilverCity.JavaScript",
                     "SilverCity.NULL",
                     "SilverCity.Perl",
                     "SilverCity.PostScript",
                     "SilverCity.Python",
                     "SilverCity.Ruby",
                     "SilverCity.SQL",
                     "SilverCity.XML",
                     "SilverCity.XSLT",
                     "SilverCity.YAML",
                     ])

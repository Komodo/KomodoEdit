from xpcom import components

from koLanguageServiceBase import KoLanguageBase, KoLexerLanguageService

class koCMakeLanguage(KoLanguageBase):
    name = "CMake"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" % (name)
    _reg_clsid_ = "{6d6fc84a-1bcf-4dac-af4d-dc5ddde8317b}"
    _reg_categories_ = [("komodo-language", name)]

    defaultExtension = ".cmake"
    commentDelimiterInfo = {
        "line": [ "#" ],
    }

    # Sample file.
    sample = """
set  (PRJ      ${DESKTOP}/common )
set  (FILELIST ${PRJ}/src/source.txt )

message(STATUS "SYSTEM_NAME     : ${CMAKE_SYSTEM_NAME}")

project(project_name)

include_directories(
  ${PRJ}/src
  ${PRJ}/includes
)

# Load SRC Variable from file
file(READ ${FILELIST} SRC)
string(REGEX REPLACE  "#.*$"  ""  SRC  ${SRC})
string(REPLACE        "\n"    ";" SRC  ${SRC})

add_executable(${PROJECT_NAME} ${SRC} )

foreach (f ${SRC})
  set_source_files_properties(${f} PROPERTIES LANGUAGE       CXX)
endforeach(f)
 """

    # Commands:
    cmake_commands = [
        "add_custom_command",
        "add_custom_target",
        "add_definitions",
        "add_dependencies",
        "add_executable",
        "add_library",
        "add_subdirectory",
        "add_test",
        "aux_source_directory",
        "build_command",
        "build_name",
        "cmake_minimum_required",
        "configure_file",
        "create_test_sourcelist",
        "else",
        "elseif",
        "enable_language",
        "enable_testing",
        "endforeach",
        "endif",
        "endmacro",
        "endwhile",
        "exec_program",
        "execute_process",
        "export_library_dependencies",
        "file",
        "find_file",
        "find_library",
        "find_package",
        "find_path",
        "find_program",
        "fltk_wrap_ui",
        "foreach",
        "get_cmake_property",
        "get_directory_property",
        "get_filename_component",
        "get_source_file_property",
        "get_target_property",
        "get_test_property",
        "if",
        "include",
        "include_directories",
        "include_external_msproject",
        "include_regular_expression",
        "install",
        "install_files",
        "install_programs",
        "install_targets",
        "link_directories",
        "link_libraries",
        "list",
        "load_cache",
        "load_command",
        "macro",
        "make_directory",
        "mark_as_advanced",
        "math",
        "message",
        "option",
        "output_required_files",
        "project",
        "qt_wrap_cpp",
        "qt_wrap_ui",
        "remove",
        "remove_definitions",
        "separate_arguments",
        "set",
        "set_directory_properties",
        "set_source_files_properties",
        "set_target_properties",
        "set_tests_properties",
        "site_name",
        "source_group",
        "string",
        "subdir_depends",
        "subdirs",
        "target_link_libraries",
        "try_compile",
        "try_run",
        "use_mangled_mesa",
        "utility_source",
        "variable_requires",
        "vtk_make_instantiator",
        "vtk_wrap_java",
        "vtk_wrap_python",
        "vtk_wrap_tcl",
        "while",
        "write_file",
    ]

    # Variables:
    cmake_variables = [
        "ABSOLUTE",
        "ABSTRACT",
        "ADDITIONAL_MAKE_CLEAN_FILES",
        "ALL",
        "AND",
        "APPEND",
        "ARGS",
        "ASCII",
        "BEFORE",
        "CACHE",
        "CACHE_VARIABLES",
        "CLEAR",
        "COMMAND",
        "COMMANDS",
        "COMMAND_NAME",
        "COMMENT",
        "COMPARE",
        "COMPILE_FLAGS",
        "COPYONLY",
        "DEFINED",
        "DEFINE_SYMBOL",
        "DEPENDS",
        "DOC",
        "EQUAL",
        "ESCAPE_QUOTES",
        "EXCLUDE",
        "EXCLUDE_FROM_ALL",
        "EXISTS",
        "EXPORT_MACRO",
        "EXT",
        "EXTRA_INCLUDE",
        "FATAL_ERROR",
        "FILE",
        "FILES",
        "FORCE",
        "FUNCTION",
        "GENERATED",
        "GLOB",
        "GLOB_RECURSE",
        "GREATER",
        "GROUP_SIZE",
        "HEADER_FILE_ONLY",
        "HEADER_LOCATION",
        "IMMEDIATE",
        "INCLUDES",
        "INCLUDE_DIRECTORIES",
        "INCLUDE_INTERNALS",
        "INCLUDE_REGULAR_EXPRESSION",
        "LESS",
        "LINK_DIRECTORIES",
        "LINK_FLAGS",
        "LOCATION",
        "MACOSX_BUNDLE",
        "MACROS",
        "MAIN_DEPENDENCY",
        "MAKE_DIRECTORY",
        "MATCH",
        "MATCHALL",
        "MATCHES",
        "MODULE",
        "NAME",
        "NAME_WE",
        "NOT",
        "NOTEQUAL",
        "NO_SYSTEM_PATH",
        "OBJECT_DEPENDS",
        "OPTIONAL",
        "OR",
        "OUTPUT",
        "OUTPUT_VARIABLE",
        "PATH",
        "PATHS",
        "POST_BUILD",
        "POST_INSTALL_SCRIPT",
        "PREFIX",
        "PREORDER",
        "PRE_BUILD",
        "PRE_INSTALL_SCRIPT",
        "PRE_LINK",
        "PROGRAM",
        "PROGRAM_ARGS",
        "PROPERTIES",
        "QUIET",
        "RANGE",
        "READ",
        "REGEX",
        "REGULAR_EXPRESSION",
        "REPLACE",
        "REQUIRED",
        "RETURN_VALUE",
        "RUNTIME_DIRECTORY",
        "SEND_ERROR",
        "SHARED",
        "SOURCES",
        "STATIC",
        "STATUS",
        "STREQUAL",
        "STRGREATER",
        "STRLESS",
        "SUFFIX",
        "TARGET",
        "TOLOWER",
        "TOUPPER",
        "VAR",
        "VARIABLES",
        "VERSION",
        "WIN32",
        "WRAP_EXCLUDE",
        "WRITE",
        # Platform specifics.
        "APPLE",
        "MINGW",
        "MSYS",
        "CYGWIN",
        "BORLAND",
        "WATCOM",
        "MSVC",
        "MSVC_IDE",
        "MSVC60",
        "MSVC70",
        "MSVC71",
        "MSVC80",
        "CMAKE_COMPILER_2005",
        "OFF",
        "ON",
    ]

    def get_lexer(self):
        if self._lexer is None:
            # Initialize styling information.
            cmake_style_map = {
                'default': ('SCE_CMAKE_DEFAULT',),
                'comments': ('SCE_CMAKE_COMMENT',),
                'keywords': ('SCE_CMAKE_COMMANDS',),
                'keywords2': ('SCE_CMAKE_PARAMETERS',),
                'variables': ('SCE_CMAKE_VARIABLE', 'SCE_CMAKE_STRINGVAR'),
                'strings': ('SCE_CMAKE_STRINGDQ', 'SCE_CMAKE_STRINGLQ', 'SCE_CMAKE_STRINGRQ'),
                'numbers': ('SCE_CMAKE_NUMBER',),
                'macro': ('SCE_CMAKE_MACRODEF',),
                'section': ('SCE_CMAKE_WHILEDEF', 'SCE_CMAKE_FOREACHDEF', 'SCE_CMAKE_IFDEFINEDEF'),
                'user': ('SCE_CMAKE_USERDEFINED',),
            }
            # Set style mapping.
            import styles
            styles.addSharedStyles(cmake_style_map)
            styles.StateMap[self.name] = cmake_style_map

            # Initalize the lexer.
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_CMAKE)
            self._lexer.setKeywords(0, self.cmake_commands)
            self._lexer.setKeywords(1, self.cmake_variables)
        return self._lexer

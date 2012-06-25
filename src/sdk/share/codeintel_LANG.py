#!/usr/bin/env python

"""${lang} support for codeintel.

This file will be imported by the codeintel system on startup and the
register() function called to register this language with the system. All
Code Intelligence for this language is controlled through this module.
"""

import os
import sys
import logging

from codeintel2.common import *
from codeintel2.citadel import CitadelBuffer
from codeintel2.langintel import LangIntel
from codeintel2.udl import UDLBuffer, UDLCILEDriver, UDLLexer
from codeintel2.util import CompareNPunctLast

from SilverCity.ScintillaConstants import (
    SCE_UDL_SSL_DEFAULT, SCE_UDL_SSL_IDENTIFIER,
    SCE_UDL_SSL_OPERATOR, SCE_UDL_SSL_VARIABLE, SCE_UDL_SSL_WORD,
)

try:
    from xpcom.server import UnwrapObject
    _xpcom_ = True
except ImportError:
    _xpcom_ = False



#---- globals

lang = "${lang}"
log = logging.getLogger("codeintel.${safe_lang_lower}")
#log.setLevel(logging.DEBUG)


# These keywords are copied from "${lang}-mainlex.udl" - be sure to keep both
# of them in sync.
keywords = [
    # Keywords
]

#---- Lexer class

# Dev Notes:
# Komodo's editing component is based on scintilla (scintilla.org). This
# project provides C++-based lexers for a number of languages -- these
# lexers are used for syntax coloring and folding in Komodo. Komodo also
# has a UDL system for writing UDL-based lexers that is simpler than
# writing C++-based lexers and has support for multi-language files.
#
# The codeintel system has a Lexer class that is a wrapper around these
# lexers. You must define a Lexer class for lang ${lang}. If Komodo's
# scintilla lexer for ${lang} is UDL-based, then this is simply:
#
#   from codeintel2.udl import UDLLexer
#   class ${safe_lang}Lexer(UDLLexer):
#       lang = lang
#
# Otherwise (the lexer for ${lang} is one of Komodo's existing C++ lexers
# then this is something like the following. See lang_python.py or
# lang_perl.py in your Komodo installation for an example. "SilverCity"
# is the name of a package that provides Python module APIs for Scintilla
# lexers.
#
#   import SilverCity
#   from SilverCity.Lexer import Lexer
#   from SilverCity import ScintillaConstants
#   class ${safe_lang}Lexer(Lexer):
#       lang = lang
#       def __init__(self):
#           self._properties = SilverCity.PropertySet()
#           self._lexer = SilverCity.find_lexer_module_by_id(ScintillaConstants.SCLEX_${safe_lang_upper})
#           self._keyword_lists = [
#               # Dev Notes: What goes here depends on the C++ lexer
#               # implementation.
#           ]

# LexerClass

#---- LangIntel class

# Dev Notes:
# All language should define a LangIntel class. (In some rare cases it
# isn't needed but there is little reason not to have the empty subclass.)
#
# One instance of the LangIntel class will be created for each codeintel
# language. Code browser functionality and some buffer functionality
# often defers to the LangIntel singleton.
#
# This is especially important for multi-lang files. For example, an
# HTML buffer uses the JavaScriptLangIntel and the CSSLangIntel for
# handling codeintel functionality in <script> and <style> tags.
#
# See other lang_*.py and codeintel_*.py files in your Komodo installation for
# examples of usage.
class ${safe_lang}LangIntel(LangIntel):
    lang = lang

    ##
    # Implicit codeintel triggering event, i.e. when typing in the editor.
    #
    # @param buf {components.interfaces.koICodeIntelBuffer}
    # @param pos {int} The cursor position in the editor/text.
    # @param implicit {bool} Automatically called, else manually called?
    #
    def trg_from_pos(self, buf, pos, implicit=True, DEBUG=False, ac=None):
        #DEBUG = True
        if pos < 1:
            return None

        # accessor {codeintel2.accessor.Accessor} - Examine text and styling.
        accessor = buf.accessor
        last_pos = pos-1
        char = accessor.char_at_pos(last_pos)
        style = accessor.style_at_pos(last_pos)
        if DEBUG:
            print "trg_from_pos: char: %r, style: %d" % (char, accessor.style_at_pos(last_pos), )
        if style in (SCE_UDL_SSL_WORD, SCE_UDL_SSL_IDENTIFIER):
            # Functions/builtins completion trigger.
            start, end = accessor.contiguous_style_range_from_pos(last_pos)
            if DEBUG:
                print "identifier style, start: %d, end: %d" % (start, end)
            # Trigger when two characters have been typed.
            if (last_pos - start) == 1:
                if DEBUG:
                    print "triggered:: complete identifiers"
                return Trigger(self.lang, TRG_FORM_CPLN, "identifiers",
                               start, implicit,
                               word_start=start, word_end=end)
        return None

    ##
    # Explicit triggering event, i.e. Ctrl+J.
    #
    # @param buf {components.interfaces.koICodeIntelBuffer}
    # @param pos {int} The cursor position in the editor/text.
    # @param implicit {bool} Automatically called, else manually called?
    #
    def preceding_trg_from_pos(self, buf, pos, curr_pos,
                               preceding_trg_terminators=None, DEBUG=False):
        #DEBUG = True
        if pos < 1:
            return None

        # accessor {codeintel2.accessor.Accessor} - Examine text and styling.
        accessor = buf.accessor
        last_pos = pos-1
        char = accessor.char_at_pos(last_pos)
        style = accessor.style_at_pos(last_pos)
        if DEBUG:
            print "pos: %d, curr_pos: %d" % (pos, curr_pos)
            print "char: %r, style: %d" % (char, style)
        if style in (SCE_UDL_SSL_WORD, SCE_UDL_SSL_IDENTIFIER):
            # Functions/builtins completion trigger.
            start, end = accessor.contiguous_style_range_from_pos(last_pos)
            if DEBUG:
                print "triggered:: complete identifiers"
            return Trigger(self.lang, TRG_FORM_CPLN, "identifiers",
                           start, implicit=False,
                           word_start=start, word_end=end)
        return None

    ##
    # Provide the list of completions or the calltip string.
    # Completions are a list of tuple (type, name) items.
    #
    # Note: This example is *not* asynchronous.
    def async_eval_at_trg(self, buf, trg, ctlr):
        if _xpcom_:
            trg = UnwrapObject(trg)
            ctlr = UnwrapObject(ctlr)
        pos = trg.pos
        ctlr.start(buf, trg)

        if trg.id == (self.lang, TRG_FORM_CPLN, "identifiers"):
            word_start = trg.extra.get("word_start")
            word_end = trg.extra.get("word_end")
            if word_start is not None and word_end is not None:
                # Only return keywords that start with the given 2-char prefix.
                prefix = buf.accessor.text_range(word_start, word_end)[:2]
                cplns = [x for x in keywords if x.startswith(prefix)]
                cplns = [("keyword", x) for x in sorted(cplns, cmp=CompareNPunctLast)]
                ctlr.set_cplns(cplns)
                ctlr.done("success")
                return

        ctlr.error("Unknown trigger type: %r" % (trg, ))
        ctlr.done("error")


#---- Buffer class

# Dev Notes:
# Every language must define a Buffer class. An instance of this class
# is created for every file of this language opened in Komodo. Most of
# that APIs for scanning, looking for autocomplete/calltip trigger points
# and determining the appropriate completions and calltips are called on
# this class.
#
# Currently a full explanation of these API is beyond the scope of this
# stub. Resources for more info are:
# - the base class definitions (Buffer, CitadelBuffer, UDLBuffer) for
#   descriptions of the APIs
# - lang_*.py files in your Komodo installation as examples
# - the upcoming "Anatomy of a Komodo Extension" tutorial
# - the Komodo community forums:
#   http://community.activestate.com/products/Komodo
# - the Komodo discussion lists:
#   http://listserv.activestate.com/mailman/listinfo/komodo-discuss
#   http://listserv.activestate.com/mailman/listinfo/komodo-beta
#
class ${safe_lang}Buffer(${buffer_subclass}):
    # Dev Note: What to sub-class from?
    # - If this is a UDL-based language: codeintel2.udl.UDLBuffer
    # - Else if this is a programming language (it has functions,
    #   variables, classes, etc.): codeintel2.citadel.CitadelBuffer
    # - Otherwise: codeintel2.buffer.Buffer
    lang = lang

    # Uncomment and assign the appropriate languages - these are used to
    # determine which language controls the completions for a given UDL family.
    #m_lang = "HTML"
    #m_lang = "XML"
    #css_lang = "CSS"
    #csl_lang = "JavaScript"
    #ssl_lang = "${lang}"
    #tpl_lang = "${lang}"

    cb_show_if_empty = True

    # Close the completion dialog when encountering any of these chars.
    cpln_stop_chars = " ()*-=+<>{}[]^&|;:'\",.?~`!@#%\\/"


#---- CILE Driver class

# Dev Notes:
# A CILE (Code Intelligence Language Engine) is the code that scans
# ${lang} content and returns a description of the code in that file.
# See "cile_${safe_lang_lower}.py" for more details.
#
# The CILE Driver is a class that calls this CILE. If ${lang} is
# multi-lang (i.e. can contain sections of different language content,
# e.g. HTML can contain markup, JavaScript and CSS), then you will need
# to also implement "scan_multilang()".
class ${safe_lang}CILEDriver(${cile_subclass}):
    lang = lang

    def scan_purelang(self, buf):
        import cile_${safe_lang_lower}
        return cile_${safe_lang_lower}.scan_buf(buf)




#---- registration

def register(mgr):
    """Register language support with the Manager."""
    mgr.set_lang_info(
        lang,
        silvercity_lexer=${safe_lang}Lexer(),
        buf_class=${safe_lang}Buffer,
        langintel_class=${safe_lang}LangIntel,
        import_handler_class=None,
        cile_driver_class=${safe_lang}CILEDriver,
        # Dev Note: set to false if this language does not support
        # autocomplete/calltips.
        is_cpln_lang=True)


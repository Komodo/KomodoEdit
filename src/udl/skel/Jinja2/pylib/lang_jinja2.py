#!/usr/bin/env python

"""Jinja2 support for codeintel.

This file will be imported by the codeintel system on startup and the
register() function called to register this language with the system. All
Code Intelligence for this language is controlled through this module.
"""

import logging

from codeintel2.common import TRG_FORM_CPLN, Trigger
from codeintel2.langintel import LangIntel
from codeintel2.udl import UDLBuffer, UDLCILEDriver, UDLLexer, XMLParsingBufferMixin

from SilverCity.ScintillaConstants import SCE_UDL_TPL_DEFAULT, \
    SCE_UDL_TPL_IDENTIFIER, SCE_UDL_TPL_WORD, SCE_UDL_TPL_OPERATOR

try:
    from xpcom.server import UnwrapObject
    _xpcom_ = True
except ImportError:
    _xpcom_ = False



#---- globals

lang = "Jinja2"
log = logging.getLogger("codeintel.jinja2")
# log.setLevel(logging.DEBUG)


# These keywords are copied from "jinja2lex.udl" - be sure to keep both
# of them in sync.
jj_nontag_keywords = tuple(sorted((
    # Keywords
    'and'
    'as',
    'break',
    'context',
    'continue',
    'false',
    'if',
    'elif',
    'ignore',
    'import',
    'in',
    'is',
    'missing',
    'not',
    'or',
    'true',
    'with',
    'without',
)))

jj_tags = tuple(sorted((
    'autoescape',
    'endautoescape',
    'block',
    'endblock',
    'call',
    'endcall',
    'do',
    'extends',
    'filter',
    'endfilter',
    'for',
    'endfor',
    'from',
    'if',
    'elif',
    'import',
    'else',
    'endif',
    'include',
    'macro',
    'endmacro',
    'pluralize',
    'trans',
    'endtrans',
    'raw',
    'endraw',
    'set',
    'endset',
    'with',
    'endwith'
)))

jj_filters = tuple(sorted((
    'abs',
    'attr',
    'batch',
    'capitalize',
    'center',
    'default',
    'dictsort',
    'escape',
    'filesizeformat',
    'first',
    'float',
    'forceescape',
    'format',
    'groupby',
    'indent',
    'int',
    'join',
    'last',
    'length',
    'list',
    'lower',
    'map',
    'pprint',
    'random',
    'reject',
    'rejectattr',
    'replace',
    'reverse',
    'round',
    'safe',
    'select',
    'selectattr',
    'slice',
    'sort',
    'string',
    'striptags',
    'sum',
    'title',
    'trim',
    'truncate',
    'upper',
    'urlencode',
    'urlize',
    'wordcount',
    'wordwrap',
    'xmlattr'
)))

#---- Lexer class

# Dev Notes:
# Komodo's editing component is based on scintilla (scintilla.org). This
# project provides C++-based lexers for a number of languages -- these
# lexers are used for syntax coloring and folding in Komodo. Komodo also
# has a UDL system for writing UDL-based lexers that is simpler than
# writing C++-based lexers and has support for multi-language files.
#
# The codeintel system has a Lexer class that is a wrapper around these
# lexers. You must define a Lexer class for lang Jinja2. If Komodo's
# scintilla lexer for Jinja2 is UDL-based, then this is simply:
#
#   from codeintel2.udl import UDLLexer
#   class Jinja2Lexer(UDLLexer):
#       lang = lang
#
# Otherwise (the lexer for Jinja2 is one of Komodo's existing C++ lexers
# then this is something like the following. See lang_python.py or
# lang_perl.py in your Komodo installation for an example. "SilverCity"
# is the name of a package that provides Python module APIs for Scintilla
# lexers.
#
#   import SilverCity
#   from SilverCity.Lexer import Lexer
#   from SilverCity import ScintillaConstants
#   class Jinja2Lexer(Lexer):
#       lang = lang
#       def __init__(self):
#           self._properties = SilverCity.PropertySet()
#           self._lexer = SilverCity.find_lexer_module_by_id(ScintillaConstants.SCLEX_JINJA2)
#           self._keyword_lists = [
#               # Dev Notes: What goes here depends on the C++ lexer
#               # implementation.
#           ]


class Jinja2Lexer(UDLLexer):
    lang = lang


#---- LangIntel class

# Mostly copy from lang_twig.py
class Jinja2LangIntel(LangIntel):
    lang = lang

    jj_tag_completion = tuple(('element', t) for t in jj_tags)
    jj_filter_completion = tuple(('function', f) for f in jj_filters)

    ##
    # Implicit codeintel triggering event, i.e. when typing in the editor.
    #
    # @param buf {components.interfaces.koICodeIntelBuffer}
    # @param pos {int} The cursor position in the editor/text.
    # @param implicit {bool} Automatically called, else manually called?
    #
    def trg_from_pos(self, buf, pos, implicit=True, DEBUG=False, ac=None):
        """
            CODE       CONTEXT      RESULT
            '{<|>'     anywhere     tag names, i.e. {% if %}
            'foo|<|>'  filters      filter names, i.e. {{ foo|capfirst }}
        """
        if pos < 2:
            return
        DEBUG = True

        # accessor {codeintel2.accessor.Accessor} - Examine text and styling.
        accessor = buf.accessor
        last_pos = pos - 1
        char = accessor.char_at_pos(last_pos)
        style = accessor.style_at_pos(last_pos)
        if DEBUG:
            log.debug("trg_from_pos: char: %r, style: %d",
                      char, accessor.style_at_pos(last_pos))

        if style in (SCE_UDL_TPL_WORD, SCE_UDL_TPL_IDENTIFIER):
            # Keywords completion trigger.
            start, end = accessor.contiguous_style_range_from_pos(last_pos)
            if DEBUG:
                log.debug("identifier style, start: %d, end: %d", start, end)
            # Trigger when two characters have been typed.
            if (last_pos - start) == 1:
                if DEBUG:
                    log.debug("  triggered: complete identifiers")
                return Trigger(self.lang, TRG_FORM_CPLN, "identifiers",
                               start, implicit,
                               word_start=start, word_end=end)

        if style not in (SCE_UDL_TPL_DEFAULT, SCE_UDL_TPL_OPERATOR):
            return

        # When last char is SCE_UDL_TPL_DEFAULT style
        if char == " " and \
           accessor.text_range(last_pos-2, last_pos) == "{%":
            if DEBUG:
                log.debug("  triggered: 'complete-tags'")
            return Trigger(lang, TRG_FORM_CPLN,
                           "complete-tags", pos, implicit)

        # When last char is SCE_UDL_TPL_OPERATOR style
        if char == "|":
            if DEBUG:
                log.debug("  triggered: 'complete-filters'")
            return Trigger(lang, TRG_FORM_CPLN,
                           "complete-filters", pos, implicit)

    ##
    # Provide the list of completions or the calltip string.
    # Completions are a list of tuple (type, name) items.
    #
    # Note: This example is *not* asynchronous.
    def async_eval_at_trg(self, buf, trg, ctlr):
        if _xpcom_:
            trg = UnwrapObject(trg)
            ctlr = UnwrapObject(ctlr)
        ctlr.start(buf, trg)

        if trg.id == (self.lang, TRG_FORM_CPLN, "complete-tags"):
            ctlr.set_cplns(self.jj_tag_completion)
            ctlr.done("success")
            return
        if trg.id == (self.lang, TRG_FORM_CPLN, "complete-filters"):
            ctlr.set_cplns(self.jj_filter_completion)
            ctlr.done("success")
            return

        if trg.id == (self.lang, TRG_FORM_CPLN, "identifiers"):
            word_start = trg.extra.get("word_start")
            word_end = trg.extra.get("word_end")
            if word_start is not None and word_end is not None:
                # Only return keywords that start with the given 2-char prefix.
                prefix = buf.accessor.text_range(word_start, word_end)[:2]
                words = tuple(x for x in jj_nontag_keywords if x.startswith(prefix))
                source = tuple(('keyword', x) for x in words)
                ctlr.set_cplns(source)
                ctlr.done("success")
                return

        ctlr.done("success")


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
class Jinja2Buffer(UDLBuffer, XMLParsingBufferMixin):
    # Dev Note: What to sub-class from?
    # - If this is a UDL-based language: codeintel2.udl.UDLBuffer
    # - Else if this is a programming language (it has functions,
    #   variables, classes, etc.): codeintel2.citadel.CitadelBuffer
    # - Otherwise: codeintel2.buffer.Buffer
    lang = lang

    # Uncomment and assign the appropriate languages - these are used to
    # determine which language controls the completions for a given UDL family.
    m_lang = "HTML"
    m_lang = "XML"
    css_lang = "CSS"
    csl_lang = "JavaScript"
    ssl_lang = "Jinja2"
    tpl_lang = "Jinja2"

    cb_show_if_empty = True

    # Close the completion dialog when encountering any of these chars.
    cpln_stop_chars = "'\" (;},~`@#%^&*()=+{}]|\\;,.<>?/"


#---- CILE Driver class
#
# The CILE Driver is a class that calls this CILE. If Jinja2 is
# multi-lang (i.e. can contain sections of different language content,
# e.g. HTML can contain markup, JavaScript and CSS), then you will need
# to also implement "scan_multilang()".
class Jinja2CILEDriver(UDLCILEDriver):
    lang = lang
    csl_lang = "JavaScript"
    tpl_lang = "Jinja2"
    css_lang = "CSS"



#---- registration

def register(mgr):
    """Register language support with the Manager."""
    mgr.set_lang_info(
        lang,
        silvercity_lexer=Jinja2Lexer(),
        buf_class=Jinja2Buffer,
        langintel_class=Jinja2LangIntel,
        import_handler_class=None,
        cile_driver_class=Jinja2CILEDriver,
        is_cpln_lang=True)


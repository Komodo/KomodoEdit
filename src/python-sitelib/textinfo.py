#!/usr/bin/env python
# Copyright (c) 2007 ActiveState Software Inc.

r"""Determine information about text files.

    >> import textinfo
    >> textinfo.textinfo_from_path('textinfo.py')
    {'encoding': 'ascii',
     'file_type': 0100000,
     'file_type_name': 'regular file',
     'has_bom': False,
     'is_text': True,
     'lang': 'Python',
     'langinfo': <Python LangInfo>,
     'text': ... # the decoded unicode text of the file
     ...}

This module efficiently determines the encoding of text files (see
_classify_encoding for details), accurately identifies binary files, and
provides detailed meta information of text files.

Note: This module requires at least Python 2.5 to use
`codecs.lookup(<encname>).name`.
"""

_cmdln_doc = """Determine information about text files.
"""

# ----------------
# Current Komodo (4.2) Encoding Determination Notes (used for reference,
# but not absolutely followed):
#
# Working through koDocumentBase._detectEncoding:
#   encoding_name = pref:encodingDefault (on first start is set
#       to encoding from locale.getdefaultlocale() typically,
#       fallback to iso8859-1; default locale typically ends up being:
#           Windows: cp1252
#           Mac OS X: mac-roman
#           (modern) Linux: UTF-8)
#   encoding = the python name for this
#   tryencoding = pref:encoding (no default, explicitly set
#       encoding) -- i.e. if there are doc prefs for this
#       path, then give this encoding a try. If not given,
#       then utf-8 for XML/XSLT/VisualBasic and
#       pref:encodingDefault for others (though this is
#       all prefable via the 'languages' pref struct).
#   tryxmldecl
#   trymeta (HTML meta)
#   trymodeline
#   autodetect (whether to try at all)
#
#   if autodetect or tryencoding:
#       koUnicodeEncoding.autoDetectEncoding()
#   else:
#       if encoding.startswith('utf'): # note this is pref:encodingDefault
#           check bom
#           presume encoding is right (give up if conversion fails)
#       else:
#           presume encoding is right (given up if fails)
#
# Working through koUnicodeEncoding.autoDetectEncoding:
#   if tryxmldecl: ...
#   if tryhtmlmeta: ...
#   if trymodeline: ...
#   use bom: ...
# ----------------

__version_info__ = (0, 1, 0)
__version__ = '.'.join(map(str, __version_info__))

import os
from os.path import join, dirname, abspath, basename, exists
import sys
import re
from pprint import pprint
import traceback
import warnings
import logging
import optparse
import codecs
import locale



#---- exceptions and warnings

class TextInfoError(Exception):
    pass

class TextInfoConfigError(TextInfoError):
    pass

class ChardetImportWarning(ImportWarning):
    pass
warnings.simplefilter("once", ChardetImportWarning)



#---- globals

log = logging.getLogger("textinfo")

# For debugging:
DEBUG_CHARDET_INFO = False  # gather chardet info



#---- module API

def textinfo_from_filename(path):
    """Determine test info for the given path **using the filename only**.
    
    No attempt is made to stat or read the file.
    """
    return TextInfo.init_from_filename(path)

def textinfo_from_path(path, encoding=None):
    """Determine text info for the given path.
    
    This raises EnvironmentError if the path doesn't not exist or could
    not be read.
    """
    return TextInfo.init_from_path(path, encoding=encoding)



#---- main TextInfo class

class TextInfo(object):
    file_type_name = None # e.g. "regular file", "directory", ...
    file_type = None      # stat.S_IFMT(os.stat(path).st_mode)
    file_mode = None      # stat.S_IMODE(os.stat(path).st_mode)
    is_text = None

    encoding = None
    has_bom = None   # whether the text has a BOM (Byte Order Marker)
    encoding_bozo = False
    encoding_bozo_reasons = None

    lang = None         # e.g. "Python", "Perl", ...
    langinfo = None     # langinfo.LangInfo instance or None

    # Enable chardet-based heuristic guessing of encoding as a last
    # resort for file types known to not be binary.
    CHARDET_ENABLED = True
    CHARDET_THRESHHOLD = 0.9  # >=90% confidence to avoid false positives.

    @classmethod
    def init_from_filename(cls, path, lidb=None):
        """Create an instance using only the filename to initialize."""
        if lidb is None:
            lidb = get_default_lidb()
        self = cls()
        self.path = path
        self._classify_from_filename(lidb)
        return self

    @classmethod
    def init_from_path(cls, path, encoding=None, lidb=None):
        """Create an instance using the filename and stat/read info
        from the given path to initialize.
        """
        if lidb is None:
            lidb = get_default_lidb()
        self = cls()
        self.path = path
        self._accessor = PathAccessor(path)
        try:
            #TODO: pref: Is a preference specified for this path?

            self._classify_from_stat(lidb)
            if self.file_type_name != "regular file":
                # Don't continue if not a regular file.
                return self

            #TODO: add 'pref:treat_as_text' a la TextMate (or
            #      perhaps that is handled in _classify_from_filename())

            self._classify_from_filename(lidb)
            if self.is_text is False:
                return self

            if not self.lang:
                self._classify_from_magic(lidb)
                if self.is_text is False:
                    return self

            self._classify_encoding(lidb, suggested_encoding=encoding)
            if self.is_text is None and self.encoding:
                self.is_text = True
            if self.is_text is False:
                return self
            self.text = self._accessor.text #TODO: make this optional (mem usage)?

            self._classify_from_content(lidb)
            return self
        finally:
            # Free the memory used by the accessor.
            del self._accessor 

    def __repr__(self):
        if self.path:
            return "<TextInfo %r>" % self.path
        else:
            return "<TextInfo %r>"\
                   % _one_line_summary_from_text(self.content, 30)

    def as_dict(self):
        return dict((k,v) for k,v in self.__dict__.items()
                    if not k.startswith('_'))

    def as_summary(self):
        """One-liner string summary of text info."""
        d = self.as_dict()
        info = []
        if self.file_type_name and self.file_type_name != "regular file":
            info.append(self.file_type_name)
        else:
            info.append(self.lang or "???")
            if not self.is_text:
                info.append("binary")
            elif self.encoding:
                enc = self.encoding
                if self.has_bom:
                    enc += " (bom)"
                info.append(enc)
            if DEBUG_CHARDET_INFO and hasattr(self, "chardet_info") \
               and self.chardet_info["encoding"]:
                info.append("chardet:%s/%.1f%%"
                            % (self.chardet_info["encoding"],
                               self.chardet_info["confidence"] * 100.0))
        return "%s: %s" % (self.path, ', '.join(info))

    def _classify_from_content(self, lidb):
        log.debug("XXX:TODO: _classify_from_content")

    def _classify_from_magic(self, lidb):
        """Attempt to classify from the file's magic number/shebang
        line, etc.

        Note that this is done before determining the encoding, so we are
        working with the *bytes*, not chars.
        """
        self.has_bom, bom_encoding = self._get_bom_info()
        if self.has_bom:
            # If this file has a BOM then, unless something funny is
            # happening, this will be a text file encoded with
            # `bom_encoding`. We leave that to `_classify_encoding()`.
            return

        # Without a BOM we assume this is an 8-bit encoding, for the
        # purposes of looking at, e.g. a shebang line.
        #
        # UTF-16 and UTF-32 without a BOM is rare; we won't pick up on,
        # e.g. Python encoded as UCS-2 or UCS-4 here (but
        # `_classify_encoding()` should catch most of those cases).
        head_bytes = self._accessor.head_bytes
        li = lidb.langinfo_from_magic(head_bytes)
        if li:
            log.debug("lang from magic: %s", li.name)
            self.langinfo = li
            self.lang = li.name
            self.is_text = li.is_text
            return

    def _classify_encoding(self, lidb, suggested_encoding=None):
        """To classify from the content we need to separate text from
        binary, and figure out the encoding. This is an imperfect task.
        The algorithm here is to go through the following heroics to attempt
        to determine an encoding that works to decode the content. If all
        such attempts fail, we presume it is binary.

        1. Use the BOM, if it has one.
        2. Try the given suggested encoding (if any).
        3. Check for EBCDIC encoding.
        4. Lang-specific (if we know the lang already):
            * if this is Python, look for coding: decl and try that
            * if this is Perl, look for use encoding decl and try that
            * ...
        5. XML: According to the XML spec the rule is the XML prolog
           specifies the encoding, or it is UTF-8.
        6. HTML: Attempt to use Content-Type meta tag. Try the given
           charset, if any.
        7. Emacs-style "coding" local var.
        8. Vi[m]-style "fileencoding" local var.
        9. Lang-specific fallback. E.g., UTF-8 for XML, ascii for Python.
        10. Heuristic checks for UTF-16 without BOM.
        11. locale.getpreferredencoding()
        12. chardet (http://chardet.feedparser.org/)
        13. Give UTF-8 a try (it is a pretty common fallback).

        XXX:TODO: shouldn't we attempt to decode the *whole* buffer? Because
        what happens when we pick one and the first 8kB decode, but
        another part of it doesn't?

        Notes:
        - A la Universal Feed Parser, if some
          supposed-to-be-authoritative encoding indicator is wrong (e.g.
          the BOM, the Python 'coding:' decl for Python),
          `self.encoding_bozo` is set True and a reason is appended to
          the `self.encoding_bozo_reasons` list.

        Dev Notes:
        - "Trying" an encoding means: attempt to decode the first 8kB.
        - Many binary types could possibly be ruled out ahead of time if
          this module attempted to support binary content, but it
          doesn't.  This module's bias is text files so we'll presume
          text unless all text decoding proves otherwise.
        """
        # 1. Try the BOM.
        if self.has_bom is not False:  # Was set in `_classify_from_magic()`.
            self.has_bom, bom_encoding = self._get_bom_info()
            if self.has_bom:
                # Python doesn't currently include a UTF-32 codec. For now
                # we'll *presume* that a UTF-32 BOM is correct. The
                # limitation is that `self.text' will NOT get set
                # because we cannot decode it.
                if bom_encoding in ("utf-32-le", "utf-32-be") \
                   or self._accessor.decode(bom_encoding):
                    log.debug("encoding: encoding from BOM: %r", bom_encoding)
                    self.encoding = bom_encoding
                    return
                else:
                    log.debug("encoding: BOM encoding (%r) was *wrong*",
                              bom_encoding)
                    self._encoding_bozo(
                        u"BOM encoding (%s) could not decode %s"
                         % (bom_encoding, self._accessor))

        head_bytes = self._accessor.head_bytes
        if DEBUG_CHARDET_INFO:
            sys.path.insert(0, os.path.expanduser("~/tm/check/contrib/chardet"))
            import chardet
            del sys.path[0]
            self.chardet_info = chardet.detect(head_bytes)

        # 2. Try the suggested encoding.
        if suggested_encoding is not None:
            norm_suggested_encoding = _norm_encoding(suggested_encoding)
            if self._accessor.decode(suggested_encoding):
                self.encoding = norm_suggested_encoding
                return
            else:
                log.debug("encoding: suggested %r encoding didn't work for %s",
                          suggested_encoding, self._accessor)

        # 3. Check for EBCDIC.
        #TODO: Not sure this should be included, chardet may be better
        #      at this given different kinds of EBCDIC.
        EBCDIC_MAGIC = '\x4c\x6f\xa7\x94'
        if self._accessor.head_4_bytes == EBCDIC_MAGIC:
            # This is EBCDIC, but I don't know if there are multiple kinds
            # of EBCDIC. Python has a 'ebcdic-cp-us' codec. We'll use
            # that for now.
            norm_ebcdic_encoding = _norm_encoding("ebcdic-cp-us")
            if self._accessor.decode(norm_ebcdic_encoding):
                log.debug("EBCDIC encoding: %r", norm_ebcdic_encoding)
                self.encoding = norm_ebcdic_encoding
                return
            else:
                log.debug("EBCDIC encoding didn't work for %s",
                          self._accessor)

        # 4. Lang-specific (if we know the lang already).
        if self.langinfo and self.langinfo.conformant_attr("encoding_decl_pattern"):
            m = self.langinfo.conformant_attr("encoding_decl_pattern") \
                    .search(head_bytes)
            if m:
                lang_encoding = m.group("encoding")
                norm_lang_encoding = _norm_encoding(lang_encoding)
                if self._accessor.decode(norm_lang_encoding):
                    log.debug("encoding: encoding from lang-spec: %r",
                              norm_lang_encoding)
                    self.encoding = norm_lang_encoding
                    return
                else:
                    log.debug("encoding: lang-spec encoding (%r) was *wrong*",
                              lang_encoding)
                    self._encoding_bozo(
                        u"lang-spec encoding (%s) could not decode %s"
                         % (lang_encoding, self._accessor))

        # 5. XML prolog
        if self.langinfo and self.langinfo.conforms_to("XML"):
            has_xml_prolog, xml_version, xml_encoding \
                = self._get_xml_prolog_info(head_bytes)
            if xml_encoding is not None:
                norm_xml_encoding = _norm_encoding(xml_encoding)
                if self._accessor.decode(norm_xml_encoding):
                    log.debug("encoding: encoding from XML prolog: %r",
                              norm_xml_encoding)
                    self.encoding = norm_xml_encoding
                    return
                else:
                    log.debug("encoding: XML prolog encoding (%r) was *wrong*",
                              norm_xml_encoding)
                    self._encoding_bozo(
                        u"XML prolog encoding (%s) could not decode %s"
                         % (norm_xml_encoding, self._accessor))
            
        # 6. HTML: Attempt to use Content-Type meta tag.
        if self.langinfo and self.langinfo.conforms_to("HTML"):
            has_http_content_type_info, http_content_type, http_encoding \
                = self._get_http_content_type_info(head_bytes)
            if has_http_content_type_info and http_encoding:
                norm_http_encoding = _norm_encoding(http_encoding)
                if self._accessor.decode(norm_http_encoding):
                    log.debug("encoding: encoding from HTTP content-type: %r",
                              norm_http_encoding)
                    self.encoding = norm_http_encoding
                    return
                else:
                    log.debug("encoding: HTTP content-type encoding (%r) was *wrong*",
                              norm_http_encoding)
                    self._encoding_bozo(
                        u"HTML content-type encoding (%s) could not decode %s"
                         % (norm_http_encoding, self._accessor))

        # 7. Emacs-style local vars.
        emacs_head_vars = self._get_emacs_head_vars(head_bytes)
        emacs_encoding = emacs_head_vars.get("coding")
        if not emacs_encoding:
            tail_bytes = self._accessor.tail_bytes
            emacs_tail_vars = self._get_emacs_tail_vars(tail_bytes)
            emacs_encoding = emacs_tail_vars.get("coding")
        if emacs_encoding:
            norm_emacs_encoding = _norm_encoding(emacs_encoding)
            if self._accessor.decode(norm_emacs_encoding):
                log.debug("encoding: encoding from Emacs coding var: %r",
                          norm_emacs_encoding)
                self.encoding = norm_emacs_encoding
                return
            else:
                log.debug("encoding: Emacs coding var (%r) was *wrong*",
                          norm_emacs_encoding)
                self._encoding_bozo(
                    u"Emacs coding var (%s) could not decode %s"
                     % (norm_emacs_encoding, self._accessor))

        # 8. Vi[m]-style local vars.
        vi_vars = self._get_vi_vars(head_bytes)
        vi_encoding = vi_vars.get("fileencoding") or vi_vars.get("fenc")
        if not vi_encoding:
            vi_vars = self._get_vi_vars(self._accessor.tail_bytes)
            vi_encoding = vi_vars.get("fileencoding") or vi_vars.get("fenc")
        if vi_encoding:
            norm_vi_encoding = _norm_encoding(vi_encoding)
            if self._accessor.decode(norm_vi_encoding):
                log.debug("encoding: encoding from Vi[m] coding var: %r",
                          norm_vi_encoding)
                self.encoding = norm_vi_encoding
                return
            else:
                log.debug("encoding: Vi[m] coding var (%r) was *wrong*",
                          norm_vi_encoding)
                self._encoding_bozo(
                    u"Vi[m] coding var (%s) could not decode %s"
                     % (norm_vi_encoding, self._accessor))

        # 9. Lang-specific fallback (e.g. XML -> utf-8, Python -> ascii, ...).
        fallback_encoding = None
        fallback_lang = None
        if self.langinfo:
            fallback_lang = self.langinfo.name
            fallback_encoding = self.langinfo.conformant_attr("default_encoding")
        if fallback_encoding:
            if self._accessor.decode(fallback_encoding):
                log.debug("encoding: fallback encoding for %s: %r",
                          fallback_lang, fallback_encoding)
                self.encoding = fallback_encoding
                return
            else:
                log.debug("encoding: %s fallback encoding (%r) was *wrong*",
                          fallback_lang, fallback_encoding)
                self._encoding_bozo(
                    u"%s fallback encoding (%s) could not decode %s"
                     % (fallback_lang, fallback_encoding, self._accessor))

        # 10. Heuristic checks for UTF-16 without BOM.
        utf16_encoding = None
        head_odd_bytes  = head_bytes[0::2]
        head_even_bytes = head_bytes[1::2]
        head_markers = ["<?xml", "#!"]
        for head_marker in head_markers:
            length = len(head_marker)
            if head_odd_bytes.startswith(head_marker) \
               and head_even_bytes[0:length] == '\x00'*length:
                utf16_encoding = "utf-16-le"
                break
            elif head_even_bytes.startswith(head_marker) \
               and head_odd_bytes[0:length] == '\x00'*length:
                utf16_encoding = "utf-16-be"
                break
        internal_markers = ["coding"]
        for internal_marker in internal_markers:
            length = len(internal_marker)
            try:
                idx = head_odd_bytes.index(internal_marker)
            except ValueError:
                pass
            else:
                if head_even_bytes[idx:idx+length] == '\x00'*length:
                    utf16_encoding = "utf-16-le"
            try:
                idx = head_even_bytes.index(internal_marker)
            except ValueError:
                pass
            else:
                if head_odd_bytes[idx:idx+length] == '\x00'*length:
                    utf16_encoding = "utf-16-be"
        if utf16_encoding:
            if self._accessor.decode(utf16_encoding):
                log.debug("encoding: guessed encoding: %r", utf16_encoding)
                self.encoding = utf16_encoding
                return

        # 11. locale.getpreferredencoding()
        # Typical values for this:
        #   Windows:    cp1252 (aka windows-1252)
        #   Mac OS X:   mac-roman
        #   Linux:      UTF-8 (modern Linux anyway)
        #   Solaris 8:  464 (aka ASCII)
        locale_encoding = locale.getpreferredencoding()
        if locale_encoding:
            norm_locale_encoding = _norm_encoding(locale_encoding)
            if self._accessor.decode(norm_locale_encoding):
                log.debug("encoding: locale preferred encoding: %r",
                          locale_encoding)
                self.encoding = norm_locale_encoding
                return

        # 12. chardet (http://chardet.feedparser.org/)
        # Note: I'm leary of using this b/c (a) it's a sizeable perf
        # hit and (b) false positives -- for example, the first 8kB of
        # /usr/bin/php on Mac OS X 10.4.10 is ISO-8859-2 with 44%
        # confidence. :)
        # Solution: (a) Only allow for content we know is not binary
        # (from langinfo association); and (b) can be disabled via
        # CHARDET_ENABLED class attribute.
        if self.CHARDET_ENABLED and self.langinfo and self.langinfo.is_text:
            try:
                import chardet
            except ImportError:
                warnings.warn("no chardet module to aid in guessing encoding",
                              ChardetImportWarning)
            else:
                chardet_info = chardet.detect(head_bytes)
                if chardet_info["encoding"] \
                   and chardet_info["confidence"] > self.CHARDET_THRESHHOLD:
                    chardet_encoding = chardet_info["encoding"]
                    norm_chardet_encoding = _norm_encoding(chardet_encoding)
                    if self._accessor.decode(norm_chardet_encoding):
                        log.debug("chardet encoding: %r", chardet_encoding)
                        self.encoding = norm_chardet_encoding
                        return

        # 13. Give UTF-8 a try (it is a pretty common fallback).
        norm_utf8_encoding = _norm_encoding("utf-8")
        if self._accessor.decode(norm_utf8_encoding):
            log.debug("fallback encoding: %r", norm_utf8_encoding)
            self.encoding = norm_utf8_encoding
            return        

        # We couldn't find an encoding that works. Give up and presume
        # this is binary content.
        self.is_text = False

    def _encoding_bozo(self, reason):
        self.encoding_bozo = True
        if self.encoding_bozo_reasons is None:
            self.encoding_bozo_reasons = []
        self.encoding_bozo_reasons.append(reason)

    # c.f. http://www.xml.com/axml/target.html#NT-prolog
    _xml_prolog_pat = re.compile(
        r'''<\?xml
            (   # strict ordering is reqd but we'll be liberal here
                \s+version=['"](?P<ver>.*?)['"]
            |   \s+encoding=['"](?P<enc>.*?)['"]
            )+
            .*? # other possible junk
            \s*\?>
        ''',
        re.VERBOSE | re.DOTALL
    )
    def _get_xml_prolog_info(self, head_bytes):
        """Parse out info from the '<?xml version=...' prolog, if any.
        
        Returns (<has-xml-prolog>, <xml-version>, <xml-encoding>). Examples:

            (False, None, None)
            (True, "1.0", None)
            (True, "1.0", "UTF-16")
        """
        # Presuming an 8-bit encoding. If it is UTF-16 or UTF-32, then
        # that should have been picked up by an earlier BOM check or via
        # the subsequent heuristic check for UTF-16 without a BOM.
        if not head_bytes.startswith("<?xml"):
            return  (False, None, None)

        # Try to extract more info from the prolog.
        match = self._xml_prolog_pat.match(head_bytes)
        if not match:
            log.debug("`%s' could not match XML prolog: '%s'", path,
                      _one_line_summary_from_text(head_bytes, 40))
            return (False, None, None)
        xml_version = match.group("ver")
        xml_encoding = match.group("enc")
        return (True, xml_version, xml_encoding)

    _html_meta_tag_pat = re.compile("""
        (<meta
        (?:\s+[\w-]+\s*=\s*(?:".*?"|'.*?'))+  # attributes
        \s*/?>)
        """,
        re.IGNORECASE | re.VERBOSE
    )
    _html_attr_pat = re.compile(
        # Currently requiring XML attrs (i.e. quoted value).
        '''(?:\s+([\w-]+)\s*=\s*(".*?"|'.*?'))'''
    )
    _http_content_type_splitter = re.compile(";\s*")
    def _get_http_content_type_info(self, head_bytes):
        """Returns info extracted from an HTML content-type meta tag if any.
        Returns (<has-http-content-type-info>, <content-type>, <charset>).

        For example:
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        yields:
            (True, "text/html", "utf-8")
        """
        # Presuming an 8-bit encoding. If it is UTF-16 or UTF-32, then
        # that should have been picked up by an earlier BOM check.
        # Otherwise we rely on `chardet` to cover us.

        # Parse out '<meta ...>' tags, then the attributes in them.
        for meta_tag in self._html_meta_tag_pat.findall(head_bytes):
            meta = dict( (k.lower(), v[1:-1])
                for k,v in self._html_attr_pat.findall(meta_tag))
            if "http-equiv" in meta \
               and meta["http-equiv"].lower() == "content-type":
                content = meta.get("content", "")
                break
        else:
            return (False, None, None)

        # We found a http-equiv="Content-Type" tag, parse its content
        # attribute value.
        parts = [p.strip() for p in self._http_content_type_splitter.split(content)]
        if not parts:
            return (False, None, None)
        content_type = parts[0] or None
        for p in parts[1:]:
            if p.lower().startswith("charset="):
                charset = p[len("charset="):]
                if charset and charset[0] in ('"', "'"):
                    charset = charset[1:]
                if charset and charset[-1] in ('"', "'"):
                    charset = charset[:-1]
                break
        else:
            charset = None

        return (True, content_type, charset)

    _html_doctype_pat = re.compile(
        '<!DOCTYPE html(\s*.*?//DTD (?P<doctype>.*?)//EN")?',
        re.IGNORECASE | re.DOTALL
    )
    def _get_html_doctype_info(self, head_bytes):
        XXX

    def XXX_content_info_via_xml(self, path, path_cache):
        """Extract content info if this is an XML or HTML file.

        Some HTML DOCTYPE info from:
            http://www.htmlhelp.com/tools/validator/doctype.htm

        HTML 4.01 Strict
            <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
                "http://www.w3.org/TR/html4/strict.dtd">
        HTML 4.01 Transitional
            <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
                "http://www.w3.org/TR/html4/loose.dtd">
            <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
        HTML 4.01 Frameset
            <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN"
                "http://www.w3.org/TR/html4/frameset.dtd">
        XHTML 1.0 Strict
            <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
                "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
        XHTML 1.0 Transitional
            <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
                "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        XHTML 1.0 Frameset
            <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Frameset//EN"
                "http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd">
        HTML 3.2
            <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
        HTML 2.0
            <!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN">

        Returns a 3-tuple:
            (<content-type-guess>, <tags>, <content-info-dict>)
        Any of the three can be None if no such info was gathered.
        """
        #XXX It may turn out to be more helpful to have the only
        #    content-types be 'html' and 'xml' and do the rest with
        #    tags rather than have 'rdf', 'xslt', 'xhtml' et al main
        #    content-types and having 'xml' and 'html' tags.
        content_type_guess = None
        tags = set()
        content_info = {}

        head = path_cache.readhead(1024)

        # See if it uses the encouraged '<?xml version=...' prolog for
        # XML files.
        #XXX check out PaulP's XML encoding recipe:
        #    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52257
        if head.startswith("<?xml"):
            content_type_guess = "xml"
            
            # Try to extract more info from the prolog.
            match = self._xml_prolog_pat.search(head)
            if not match:
                log.warn("`%s' could not match XML prolog: '%s'", path,
                         _one_line_summary_from_text(head, 40))
            else:
                d = match.groupdict()
                if "ver" in d:
                    content_info["xml-version"] = d["ver"]
                if "enc" in d:
                    content_info["xml-encoding"] = d["enc"]

        # See if it looks like HTML.
        match = self._html_doctype_pat.search(head)
        if match:
            if content_type_guess:
                tags.add(content_type_guess)
            content_type_guess = "html"
            if not match.group(1):
                # Eventually I will lower this log level (or remove it
                # altogether) as I become more confident that a good %
                # of HTML doctypes are being matched.
                log.warn("`%s' could not match tail in HTML doctype: '%s'",
                         path,
                         _one_line_summary_from_text(head[match.start():], 40))
            else:
                html_doctype = match.group("doctype")
                html_doctype = { # translate std html doctypes
                    "HTML": "HTML 2.0",
                    "HTML 3.2 Final": "HTML 3.2",
                }.get(html_doctype, html_doctype)
                content_info["html-doctype"] = html_doctype

                if "xhtml" in html_doctype.lower():
                    tags.add("xml")

        # See if recognize a popular XML flavour.
        # C.f. Don't Invent XML Languages
        #      http://www.tbray.org/ongoing/When/200x/2006/01/08/No-New-XML-Languages
        # Namely: XHTML, DocBook, ODF, UBL, Atom
        #
        # The list I consider tier 1:
        # XHTML (done above), RDF, XUL, Atom, RSS (various versions?),
        # DocBook, RelaxNG, XML Schema, XSLT.
        if content_type_guess == "xml":
            log.warn("XXX add XML flavour detection")

        return content_type_guess, tags, content_info

    _emacs_vars_head_pat = re.compile("-\*-\s*(.*?)\s*-\*-")

    def _get_emacs_head_vars(self, head_bytes):
        """Return a dictionary of emacs-style local variables in the head.

        "Head" emacs vars on the ones in the '-*- ... -*-' one-liner.
        
        Parsing is done loosely according to this spec (and according to
        some in-practice deviations from this):
        http://www.gnu.org/software/emacs/manual/html_node/emacs/Specifying-File-Variables.html#Specifying-File-Variables
        """
        # Presuming an 8-bit encoding. If it is UTF-16 or UTF-32, then
        # that should have been picked up by an earlier BOM check.
        # Otherwise we rely on `chardet` to cover us.

        # Search the head for a '-*-'-style one-liner of variables.
        emacs_vars = {}
        if "-*-" in head_bytes:
            match = self._emacs_vars_head_pat.search(head_bytes)
            if match:
                emacs_vars_str = match.group(1)
                if '\n' in emacs_vars_str:
                    raise ValueError("local variables error: -*- not "
                                     "terminated before end of line")
                emacs_var_strs = [s.strip() for s in emacs_vars_str.split(';')
                                  if s.strip()]
                if len(emacs_var_strs) == 1 and ':' not in emacs_var_strs[0]:
                    # While not in the spec, this form is allowed by emacs:
                    #   -*- Tcl -*-
                    # where the implied "variable" is "mode". This form
                    # is only allowed if there are no other variables.
                    emacs_vars["mode"] = emacs_var_strs[0].strip()
                else:
                    for emacs_var_str in emacs_var_strs:
                        try:
                            variable, value = emacs_var_str.strip().split(':', 1)
                        except ValueError:
                            log.debug("emacs variables error: malformed -*- "
                                      "line: %r", emacs_var_str)
                            continue
                        # Lowercase the variable name because Emacs allows "Mode"
                        # or "mode" or "MoDe", etc.
                        emacs_vars[variable.lower()] = value.strip()

        # Unquote values.
        for var, val in emacs_vars.items():
            if len(val) > 1 and (val.startswith('"') and val.endswith('"')
               or val.startswith('"') and val.endswith('"')):
                emacs_vars[var] = val[1:-1]

        return emacs_vars

    # This regular expression is intended to match blocks like this:
    #    PREFIX Local Variables: SUFFIX
    #    PREFIX mode: Tcl SUFFIX
    #    PREFIX End: SUFFIX
    # Some notes:
    # - "[ \t]" is used instead of "\s" to specifically exclude newlines
    # - "(\r\n|\n|\r)" is used instead of "$" because the sre engine does
    #   not like anything other than Unix-style line terminators.
    _emacs_vars_tail_pat = re.compile(r"""^
        (?P<prefix>(?:[^\r\n|\n|\r])*?)
        [\ \t]*Local\ Variables:[\ \t]*
        (?P<suffix>.*?)(?:\r\n|\n|\r)
        (?P<content>.*?\1End:)
        """, re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE)

    def _get_emacs_tail_vars(self, tail_bytes):
        r"""Return a dictionary of emacs-style local variables in the tail.

        "Tail" emacs vars on the ones in the multi-line "Local
        Variables:" block.

        >>> ti = TextInfo()
        >>> ti._get_emacs_tail_vars('# Local Variables:\n# foo: bar\n# End:')
        {'foo': 'bar'}
        >>> ti._get_emacs_tail_vars('# Local Variables:\n# foo: bar\\\n#  baz\n# End:')
        {'foo': 'bar baz'}
        >>> ti._get_emacs_tail_vars('# Local Variables:\n# quoted: "bar "\n# End:')
        {'quoted': 'bar '}
    
        Parsing is done according to this spec (and according to some
        in-practice deviations from this):
            http://www.gnu.org/software/emacs/manual/html_chapter/emacs_33.html#SEC485
        """
        # Presuming an 8-bit encoding. If it is UTF-16 or UTF-32, then
        # that should have been picked up by an earlier BOM check.
        # Otherwise we rely on `chardet` to cover us.
        emacs_vars = {}

        match = self._emacs_vars_tail_pat.search(tail_bytes)
        if match:
            prefix = match.group("prefix")
            suffix = match.group("suffix")
            lines = match.group("content").splitlines(0)
            #print "prefix=%r, suffix=%r, content=%r, lines: %s"\
            #      % (prefix, suffix, match.group("content"), lines)

            # Validate the Local Variables block: proper prefix and suffix
            # usage.
            for i, line in enumerate(lines):
                if not line.startswith(prefix):
                    log.debug("emacs variables error: line '%s' "
                              "does not use proper prefix '%s'"
                              % (line, prefix))
                    return {}
                # Don't validate suffix on last line. Emacs doesn't care,
                # neither should we.
                if i != len(lines)-1 and not line.endswith(suffix):
                    log.debug("emacs variables error: line '%s' "
                              "does not use proper suffix '%s'"
                              % (line, suffix))
                    return {}

            # Parse out one emacs var per line.
            continued_for = None
            for line in lines[:-1]: # no var on the last line ("PREFIX End:")
                if prefix: line = line[len(prefix):] # strip prefix
                if suffix: line = line[:-len(suffix)] # strip suffix
                line = line.strip()
                if continued_for:
                    variable = continued_for
                    if line.endswith('\\'):
                        line = line[:-1].rstrip()
                    else:
                        continued_for = None
                    emacs_vars[variable] += ' ' + line
                else:
                    try:
                        variable, value = line.split(':', 1)
                    except ValueError:
                        log.debug("local variables error: missing colon "
                                  "in local variables entry: '%s'" % line)
                        continue
                    # Do NOT lowercase the variable name, because Emacs only
                    # allows "mode" (and not "Mode", "MoDe", etc.) in this block.
                    value = value.strip()
                    if value.endswith('\\'):
                        value = value[:-1].rstrip()
                        continued_for = variable
                    else:
                        continued_for = None
                    emacs_vars[variable] = value

        # Unquote values.
        for var, val in emacs_vars.items():
            if len(val) > 1 and (val.startswith('"') and val.endswith('"')
               or val.startswith('"') and val.endswith('"')):
                emacs_vars[var] = val[1:-1]

        return emacs_vars

    #TODO: nice if parser also gave which of 'vi, vim, ex'
    #      and the range in the accessor.
    _vi_vars_pats_and_splitters = [
        (re.compile(r'[ \t]+(?:vi|vim|ex):\s*set? (.*?):', re.M),
         re.compile(r'[ \t]+')),
        (re.compile(r'[ \t]+(?:vi|vim|ex):\s*(.*?)$', re.M),
         re.compile(r'[ \t:]+')),
        (re.compile(r'^(?:vi|vim):\s*set? (.*?):', re.M),
         re.compile(r'[ \t]+')),
    ]
    def _get_vi_vars(self, bytes):
        """Return a dict of Vi[m] modeline vars.

        See ":help modeline" in Vim for a spec.

            >>> ti = TextInfo()
            >>> ti._get_vi_vars("/* vim: set ai tw=75: */")
            {'ai': None, 'tw': 75}
            >>> ti._get_vi_vars("vim: set ai tw=75: bar")
            {'ai': None, 'tw': 75}

            >>> ti._get_vi_vars("vi: set foo:bar")
            {'foo': None}
            >>> ti._get_vi_vars(" vi: se foo:bar")
            {'foo': None}
            >>> ti._get_vi_vars(" ex: se foo:bar")
            {'foo': None}

            >>> ti._get_vi_vars(" vi:noai:sw=3 tw=75")
            {'tw': 75, 'sw': 3, 'noai': None}
            >>> ti._get_vi_vars(" vi:noai:sw=3 tw=75")
            {'tw': 75, 'sw': 3, 'noai': None}

            >>> ti._get_vi_vars("ex: se foo:bar")
            {}
        """
        # Presume 8-bit encoding... yada yada.
        vi_vars = {}
        for pat, splitter in self._vi_vars_pats_and_splitters:
            match = pat.search(bytes)
            if match:
                for var_str in splitter.split(match.group(1)):
                    if '=' in var_str:
                        name, value = var_str.split('=', 1)
                        vi_vars[name] = _intify(value)
                    else:
                        vi_vars[var_str] = None
                break
        return vi_vars

    def _get_bom_info(self):
        """Returns (<has-bom>, <bom-encoding>). Examples:

            (True, "utf-8") 
            (True, "utf-16-le") 
            (False, None)
        """
        boms_and_encodings = [ # in order from longest to shortest
            (codecs.BOM_UTF32_LE, "utf-32-le"),
            (codecs.BOM_UTF32_BE, "utf-32-be"),
            (codecs.BOM_UTF8, "utf-8"),
            (codecs.BOM_UTF16_LE, "utf-16-le"),
            (codecs.BOM_UTF16_BE, "utf-16-be"),
        ]
        head_4 = self._accessor.head_4_bytes
        for bom, encoding in boms_and_encodings:
            if head_4.startswith(bom):
                return (True, encoding)
                break
        else:
            return (False, None)

    def _classify_from_filename(self, lidb):
        """Classify from the path *filename* only.
        
        Sets `lang' and `langinfo', if can be determined.
        """
        #TODO Add support for binary/not-binary in contentinfo.conf.
        filename = basename(self.path)

        # ...from the ext
        idx = 0
        while True:
            idx = filename.find('.', idx)
            if idx == -1:
                break
            ext = filename[idx:]
            li = lidb.langinfo_from_ext(ext)
            if li:
                log.debug("lang from ext: `%s' -> `%s'", ext, li.name)
                self.langinfo = li
                self.lang = li.name
                self.is_text = li.is_text
                return
            idx += 1

        # ...from file basename
        li = lidb.langinfo_from_filename(filename)
        if li:
            log.debug("lang from filename: `%s' -> `%s'", filename, li.name)
            self.langinfo = li
            self.lang = li.name
            self.is_text = li.is_text
            return

    def _classify_from_stat(self, lidb):
        """Set some `file_*' attributes from stat mode."""
        from stat import S_ISREG, S_ISDIR, S_ISLNK, S_ISFIFO, S_ISSOCK, \
                         S_ISBLK, S_ISCHR, S_IMODE, S_IFMT
        stat = self._accessor.stat
        st_mode = stat.st_mode
        self.file_type = S_IFMT(st_mode)
        self.file_mode = S_IMODE(st_mode)
        self.file_stat = stat
        if S_ISREG(st_mode):
            self.file_type_name = "regular file"
        elif S_ISDIR(st_mode):
            self.file_type_name = "directory"
        elif S_ISLNK(st_mode):
            self.file_type_name = "symbolic link"
        elif S_ISFIFO(st_mode):
            self.file_type_name = "fifo"
        elif S_ISSOCK(st_mode):
            self.file_type_name = "socket"
        elif S_ISBLK(st_mode):
            self.file_type_name = "block special"
        elif S_ISCHR(st_mode):
            self.file_type_name = "character special"


def _norm_encoding(encoding):
    """Normalize the encoding name -- where "normalized" is what
    Python's codec's module calls it.

    Interesting link:
        The IANA-registered set of character sets.
        http://www.iana.org/assignments/character-sets

    TODO: use encodings.aliases.aliases dict to normalize
    """
    try:
        # This requires Python >=2.5.
        return codecs.lookup(encoding).name
    except LookupError:
        return encoding


#---- accessor API
# The idea here is to abstract accessing the text file content being
# classified to allow, e.g. classifying content without a file, from
# a Komodo buffer, etc.
#
#TODO: improve this, spec it. It is currently lame.

class Accessor(object):
    """Virtual base class defining Accessor API for accessing
    text content.
    """
    # API:
    #   prop head_bytes -> head 8k bytes
    #   prop head_4_bytes -> head 4 bytes (useful for BOM detection) 
    #   prop tail_bytes -> tail 8k bytes
    #   def bytes_range(start, end) -> bytes in that range

    HEAD_SIZE = pow(2, 13) # 8k
    TAIL_SIZE = pow(2, 13) # 8k

    encoding = None
    text = None
    _unsuccessful_encodings = None
    def decode(self, encoding):
        """Decodes bytes with the given encoding and, if successful,
        sets `self.text` with the decoded result and returns True.
        Otherwise, returns False.

        Side-effects: On success, sets `self.text` and `self.encoding`.
       
        Optimization: First an attempt is made to decode
        `self.head_bytes` instead of all of `self.bytes`. This allows
        for the normal usage in `TextInfo._classify_encoding()` to *not*
        bother fully reading binary files that could not be decoded.

        Optimization: Decoding attempts are cached to not bother
        attempting a failed decode twice.
        """
        if self._unsuccessful_encodings is None:
            self._unsuccessful_encodings = set()
        if encoding in self._unsuccessful_encodings:
            return False
        elif encoding == self.encoding:
            return True

        head_bytes = self.head_bytes
        try:
            head_bytes.decode(encoding, 'strict')
        except LookupError, ex:
            log.debug("encoding lookup error: %r", encoding)
            self._unsuccessful_encodings.add(encoding)
            return False
        except UnicodeError, ex:
            # If the decode failed in the last few bytes, it might be
            # because a multi-surrogate was cutoff by the head. Ignore
            # the error here, if it is truly not of this encoding, the
            # full file decode will fail.
            if ex.start >= self.HEAD_SIZE - 5:
                # '5' because the max num bytes to encode a single char
                # in any encoding is 6 bytes (in UTF-8).
                pass
            else:
                self._unsuccessful_encodings.add(encoding)
                return False
        try:
            self.text = self.bytes.decode(encoding, 'strict')
        except UnicodeError, ex:
            self._unsuccessful_encodings.add(encoding)
            return False
        self.encoding = encoding
        return True


class PathAccessor(Accessor):
    """Accessor API for a path."""
    (READ_NONE,             # _file==None, file not opened yet
     READ_HEAD,             # _bytes==<head bytes>
     READ_TAIL,             # _bytes==<head>, _bytes_tail==<tail>
     READ_ALL) = range(4)   # _bytes==<all>, _bytes_tail==None, _file closed
    _read_state = READ_NONE # one of the READ_* states
    _file = None
    _bytes = None
    _bytes_tail = None

    def __init__(self, path):
        self.path = path

    def __str__(self):
        return "path `%s'" % self.path 

    _stat_cache = None
    @property
    def stat(self):
        if self._stat_cache is None:
            self._stat_cache = os.stat(self.path)
        return self._stat_cache

    @property
    def size(self):
        return self.stat.st_size

    def __del__(self):
        self.close()

    def close(self):
        if self._file and not self._file.closed:
            self._file.close()

    def _read(self, state):
        """Read up to at least `state`."""
        # It is the job of the caller to only call _read() if necessary.
        assert self._read_state < state

        if self._read_state == self.READ_NONE:
            assert self._file is None and self._bytes is None
            self._file = open(self.path, 'rb')
            if state == self.READ_HEAD:
                self._bytes = self._file.read(self.HEAD_SIZE)
                self._read_state = (self.size <= self.HEAD_SIZE
                    and self.READ_ALL or self.READ_HEAD)
            elif state == self.READ_TAIL:
                if self.size <= self.HEAD_SIZE + self.TAIL_SIZE:
                    self._bytes = self._file.read()
                    self._read_state = self.READ_ALL
                else:
                    self._bytes = self._file.read(self.HEAD_SIZE)
                    self._file.seek(-self.TAIL_SIZE, 2) # 2 == relative to end
                    self._bytes_tail = self._file.read(self.TAIL_SIZE)
                    self._read_state = self.READ_TAIL
            elif state == self.READ_ALL:
                self._bytes = self._file.read()
                self._read_state = self.READ_ALL

        elif self._read_state == self.READ_HEAD:
            if state == self.READ_TAIL:
                if self.size <= self.HEAD_SIZE + self.TAIL_SIZE:
                    self._bytes += self._file.read()
                    self._read_state = self.READ_ALL
                else:
                    self._file.seek(-self.TAIL_SIZE, 2) # 2 == relative to end
                    self._bytes_tail = self._file.read(self.TAIL_SIZE)
                    self._read_state = self.READ_TAIL
            elif state == self.READ_ALL:
                self._bytes += self._file.read()
                self._read_state = self.READ_ALL
                
        elif self._read_state == self.READ_TAIL:
            assert state == self.READ_ALL
            self._file.seek(self.HEAD_SIZE, 0) # 0 == relative to start
            remaining_size = self.size - self.HEAD_SIZE - self.TAIL_SIZE
            assert remaining_size > 0, \
                "negative remaining bytes to read from '%s': %d" \
                % (self.path, self.size)
            self._bytes += self._file.read(remaining_size)
            self._bytes += self._bytes_tail
            self._bytes_tail = None
            self._read_state = self.READ_ALL
                
        if self._read_state == self.READ_ALL:
            self.close()

    @property
    def head_bytes(self):
        """The first 8k raw bytes of the document."""
        if self._read_state < self.READ_HEAD:
            self._read(self.READ_HEAD)
        return self._bytes[:self.HEAD_SIZE]

    @property
    def head_4_bytes(self):
        if self._read_state < self.READ_HEAD:
            self._read(self.READ_HEAD)
        return self._bytes[:4]

    @property
    def tail_bytes(self):
        if self._read_state < self.READ_TAIL:
            self._read(self.READ_TAIL)
        if self._read_state == self.READ_ALL:
            return self._bytes[-self.TAIL_SIZE:]
        else:
            return self._bytes_tail

    def bytes_range(self, start, end):
        if self._read_state < self.READ_ALL:
            self._read(self.READ_ALL)
        return self._bytes[start:end]

    @property
    def bytes(self):
        if self._read_state < self.READ_ALL:
            self._read(self.READ_ALL)
        return self._bytes



#---- internal support stuff

_default_lidb = None
def get_default_lidb():
    global _default_lidb
    if _default_lidb is None:
        import langinfo
        _default_lidb = langinfo.Database()
    return _default_lidb


def _intify(s):
    try:
        return int(s)
    except ValueError:
        return s

# Recipe: regex_from_encoded_pattern (1.0)
def _regex_from_encoded_pattern(s):
    """'foo'    -> re.compile(re.escape('foo'))
       '/foo/'  -> re.compile('foo')
       '/foo/i' -> re.compile('foo', re.I)
    """
    if s.startswith('/') and s.rfind('/') != 0:
        # Parse it: /PATTERN/FLAGS
        idx = s.rfind('/')
        pattern, flags_str = s[1:idx], s[idx+1:]
        flag_from_char = {
            "i": re.IGNORECASE,
            "l": re.LOCALE,
            "s": re.DOTALL,
            "m": re.MULTILINE,
            "u": re.UNICODE,
        }
        flags = 0
        for char in flags_str:
            try:
                flags |= flag_from_char[char]
            except KeyError:
                raise ValueError("unsupported regex flag: '%s' in '%s' "
                                 "(must be one of '%s')"
                                 % (char, s, ''.join(flag_from_char.keys())))
        return re.compile(s[1:idx], flags)
    else: # not an encoded regex
        return re.compile(re.escape(s))

# Recipe: paths_from_path_patterns (0.3.7)
def _should_include_path(path, includes, excludes):
    """Return True iff the given path should be included."""
    from os.path import basename
    from fnmatch import fnmatch

    base = basename(path)
    if includes:
        for include in includes:
            if fnmatch(base, include):
                try:
                    log.debug("include `%s' (matches `%s')", path, include)
                except (NameError, AttributeError):
                    pass
                break
        else:
            try:
                log.debug("exclude `%s' (matches no includes)", path)
            except (NameError, AttributeError):
                pass
            return False
    for exclude in excludes:
        if fnmatch(base, exclude):
            try:
                log.debug("exclude `%s' (matches `%s')", path, exclude)
            except (NameError, AttributeError):
                pass
            return False
    return True

_NOT_SPECIFIED = ("NOT", "SPECIFIED")
def _paths_from_path_patterns(path_patterns, files=True, dirs="never",
                              recursive=True, includes=[], excludes=[],
                              on_error=_NOT_SPECIFIED):
    """_paths_from_path_patterns([<path-patterns>, ...]) -> file paths

    Generate a list of paths (files and/or dirs) represented by the given path
    patterns.

        "path_patterns" is a list of paths optionally using the '*', '?' and
            '[seq]' glob patterns.
        "files" is boolean (default True) indicating if file paths
            should be yielded
        "dirs" is string indicating under what conditions dirs are
            yielded. It must be one of:
              never             (default) never yield dirs
              always            yield all dirs matching given patterns
              if-not-recursive  only yield dirs for invocations when
                                recursive=False
            See use cases below for more details.
        "recursive" is boolean (default True) indicating if paths should
            be recursively yielded under given dirs.
        "includes" is a list of file patterns to include in recursive
            searches.
        "excludes" is a list of file and dir patterns to exclude.
            (Note: This is slightly different than GNU grep's --exclude
            option which only excludes *files*.  I.e. you cannot exclude
            a ".svn" dir.)
        "on_error" is an error callback called when a given path pattern
            matches nothing:
                on_error(PATH_PATTERN)
            If not specified, the default is look for a "log" global and
            call:
                log.error("`%s': No such file or directory")
            Specify None to do nothing.

    Typically this is useful for a command-line tool that takes a list
    of paths as arguments. (For Unix-heads: the shell on Windows does
    NOT expand glob chars, that is left to the app.)

    Use case #1: like `grep -r`
      {files=True, dirs='never', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield nothing
        script PATH*    # yield all files matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files (not dirs) recursively under DIR
        script -r PATH* # yield files matching PATH* and files recursively
                        # under dirs matching PATH*; if none, call
                        # on_error(PATH*) callback

    Use case #2: like `file -r` (if it had a recursive option)
      {files=True, dirs='if-not-recursive', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield DIR, else call on_error(DIR)
        script PATH*    # yield all files and dirs matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files (not dirs) recursively under DIR
        script -r PATH* # yield files matching PATH* and files recursively
                        # under dirs matching PATH*; if none, call
                        # on_error(PATH*) callback

    Use case #3: kind of like `find .`
      {files=True, dirs='always', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield DIR, else call on_error(DIR)
        script PATH*    # yield all files and dirs matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files and dirs recursively under DIR
                        # (including DIR)
        script -r PATH* # yield files and dirs matching PATH* and recursively
                        # under dirs; if none, call on_error(PATH*)
                        # callback
    """
    from os.path import basename, exists, isdir, join
    from glob import glob

    assert not isinstance(path_patterns, basestring), \
        "'path_patterns' must be a sequence, not a string: %r" % path_patterns
    GLOB_CHARS = '*?['

    for path_pattern in path_patterns:
        # Determine the set of paths matching this path_pattern.
        for glob_char in GLOB_CHARS:
            if glob_char in path_pattern:
                paths = glob(path_pattern)
                break
        else:
            paths = exists(path_pattern) and [path_pattern] or []
        if not paths:
            if on_error is None:
                pass
            elif on_error is _NOT_SPECIFIED:
                try:
                    log.error("`%s': No such file or directory", path_pattern)
                except (NameError, AttributeError):
                    pass
            else:
                on_error(path_pattern)

        for path in paths:
            if isdir(path):
                # 'includes' SHOULD affect whether a dir is yielded.
                if (dirs == "always"
                    or (dirs == "if-not-recursive" and not recursive)
                   ) and _should_include_path(path, includes, excludes):
                    yield path

                # However, if recursive, 'includes' should NOT affect
                # whether a dir is recursed into. Otherwise you could
                # not:
                #   script -r --include="*.py" DIR
                if recursive and _should_include_path(path, [], excludes):
                    for dirpath, dirnames, filenames in os.walk(path):
                        dir_indeces_to_remove = []
                        for i, dirname in enumerate(dirnames):
                            d = join(dirpath, dirname)
                            if dirs == "always" \
                               and _should_include_path(d, includes, excludes):
                                yield d
                            if not _should_include_path(d, [], excludes):
                                dir_indeces_to_remove.append(i)
                        for i in reversed(dir_indeces_to_remove):
                            del dirnames[i]
                        if files:
                            for filename in sorted(filenames):
                                f = join(dirpath, filename)
                                if _should_include_path(f, includes, excludes):
                                    yield f

            elif files and _should_include_path(path, includes, excludes):
                yield path

class _NoReflowFormatter(optparse.IndentedHelpFormatter):
    """An optparse formatter that does NOT reflow the description."""
    def format_description(self, description):
        return description or ""

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
        record.lowerlevelname = record.levelname.lower()
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

def _setup_logging(stream=None):
    """Do logging setup:

    We want a prettier default format:
         do: level: ...
    Spacing. Lower case. Skip " level:" if INFO-level. 
    """
    hdlr = logging.StreamHandler(stream)
    defaultFmt = "%(name)s: %(levelname)s: %(message)s"
    infoFmt = "%(name)s: %(message)s"
    fmtr = _PerLevelFormatter(fmt=defaultFmt,
                              fmtFromLevel={logging.INFO: infoFmt})
    hdlr.setFormatter(fmtr)
    logging.root.addHandler(hdlr)
    log.setLevel(logging.INFO)


#---- mainline

def main(argv):
    usage = "usage: %prog PATHS..."
    version = "%prog "+__version__
    parser = optparse.OptionParser(usage=usage,
        version=version, description=_cmdln_doc,
        formatter=_NoReflowFormatter())
    parser.add_option("-v", "--verbose", dest="log_level",
                      action="store_const", const=logging.DEBUG,
                      help="more verbose output")
    parser.add_option("-q", "--quiet", dest="log_level",
                      action="store_const", const=logging.WARNING,
                      help="quieter output")
    parser.add_option("-r", "--recursive", action="store_true",
                      help="recursively descend into given paths")
    parser.add_option("--encoding", help="suggested encoding for input files")
    parser.add_option("-f", "--format",
                      help="format of output: summary (default), dict")
    parser.add_option("-x", "--exclude", dest="excludes", action="append",
        metavar="PATTERN",
        help="path pattern to exclude for recursive search (by default SCC "
             "control dirs are skipped)")
    parser.set_defaults(log_level=logging.INFO, encoding=None, recursive=False,
                        format="summary", excludes=[".svn", "CVS", ".hg"])
    opts, args = parser.parse_args()
    log.setLevel(opts.log_level)
    if opts.log_level > logging.INFO:
        warnings.simplefilter("ignore", ChardetImportWarning)

    if not args:
        parser.print_help()
        return 0

    for path in _paths_from_path_patterns(args, excludes=opts.excludes,
                    recursive=opts.recursive, dirs="if-not-recursive"):
        ti = textinfo_from_path(path, encoding=opts.encoding)
        if opts.format == "summary":
            print ti.as_summary()
        elif opts.format == "dict":
            d = ti.as_dict()
            if "text" in d:
                del d["text"]
            pprint(d)
        else:
            raise Error("unknown output format: %r" % opts.format)


if __name__ == "__main__":
    _setup_logging()
    try:
        retval = main(sys.argv)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        sys.exit(1)
    except:
        exc_info = sys.exc_info()
        if log.level <= logging.DEBUG:
            import traceback
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

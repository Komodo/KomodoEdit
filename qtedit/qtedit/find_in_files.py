"""Pure multi-file search/replace logic -- no Qt, no XPCOM.

Komodo's legacy multi-file engine (src/find/findlib2.py, ~1822 LOC) is
actually XPCOM-free pure Python 2 (os/re/glob/fnmatch/codecs/cPickle only)
-- unlike Toolbox/Projects it would be technically separable. Kept
consistent with the rest of this rewrite anyway (see e.g. the UDL luddite
compiler, which also stays a Python-2-only dev-time tool rather than being
bridged): the actual search/replace algorithm here is simple enough
(os.walk + fnmatch + re) that a clean Python 3 rewrite is less work and
less risk than a second Python-2-subprocess bridge (which codeintel2 needs
only because of its much deeper language-intelligence logic).

Legacy's regex dialect for multi-file search is already plain Python `re`
(findlib2.py's regex_info_from_str), not Scintilla's own dialect or PCRE --
so this module's use of `re` directly is already format-compatible, no
translation layer needed.
"""
import fnmatch
import os
import re
from dataclasses import dataclass, field

# Simple heuristics, not Komodo's real encoding-detection machinery: a
# fixed size cap and a null-byte sniff on the first chunk are enough to
# keep an MVP multi-file search fast and avoid choking on binaries.
MAX_FILE_SIZE = 5 * 1024 * 1024
SNIFF_SIZE = 1024

# Tried in order after a strict UTF-8 decode fails, first one that decodes
# without error wins -- not real encoding detection (no chardet dependency
# added for this), just enough to not silently mangle common non-UTF-8
# single-byte text (Windows-1252/Latin-1) instead of replacing every
# non-ASCII byte with U+FFFD. Deliberately excludes UTF-16/32 without a
# BOM: those are handled separately via an explicit byte-prefix check
# below, since blindly *trying* UTF-16 on arbitrary bytes rarely raises
# UnicodeDecodeError -- it just silently produces garbage instead of
# failing, so it can't be used as a "try and see if it raises" fallback.
_FALLBACK_ENCODINGS = ["cp1252", "latin-1"]

_BOM_ENCODINGS = [
    (b"\xff\xfe\x00\x00", "utf-32-le"),
    (b"\x00\x00\xfe\xff", "utf-32-be"),
    (b"\xff\xfe", "utf-16-le"),
    (b"\xfe\xff", "utf-16-be"),
]


@dataclass
class FileHit:
    path: str
    line_no: int  # 1-based, matches editor gotoLine's 0-based line minus 1 at call site
    column: int  # 0-based character offset into the line
    line_text: str
    match_start: int
    match_end: int
    abs_start: int = 0  # 0-based character offset into the whole file's text
    abs_end: int = 0


@dataclass
class PlannedReplacement:
    """One FileHit paired with the exact text that would replace it --
    already expanded (backreferences resolved for regex mode) so the UI can
    show a real preview and the caller can apply any subset of hits without
    needing to re-run the regex."""
    hit: FileHit
    replacement_text: str
    selected: bool = True


@dataclass
class FileReplacement:
    path: str
    original_text: str
    planned: list  # list[PlannedReplacement]


def _is_binary(path):
    try:
        with open(path, "rb") as f:
            chunk = f.read(SNIFF_SIZE)
    except OSError:
        return True
    return b"\x00" in chunk


def _compile_pattern(pattern, case_sensitive, whole_word, use_regex):
    text = pattern if use_regex else re.escape(pattern)
    if whole_word:
        text = rf"\b{text}\b"
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(text, flags)


def _iter_paths(root_dir, recursive, include_glob, exclude_glob):
    include_glob = include_glob or "*"
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for name in sorted(filenames):
            if not fnmatch.fnmatch(name, include_glob):
                continue
            if exclude_glob and fnmatch.fnmatch(name, exclude_glob):
                continue
            yield os.path.join(dirpath, name)
        if not recursive:
            dirnames[:] = []
        else:
            dirnames.sort()


def read_text(path):
    """Read `path` as text, trying UTF-8 first and falling back to a short
    list of common encodings (see _FALLBACK_ENCODINGS) before giving up and
    replacing undecodable bytes. Returns None for binaries/oversized/
    unreadable files."""
    if os.path.getsize(path) > MAX_FILE_SIZE or _is_binary(path):
        return None
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError:
        return None
    for bom, encoding in _BOM_ENCODINGS:
        if raw.startswith(bom):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                break  # had the BOM but corrupt content -- fall through
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass
    for encoding in _FALLBACK_ENCODINGS:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _hits_in_text(path, text, regex):
    """Yield FileHit for every match of `regex` in `text`, with absolute
    file offsets as well as line/column (for the editor jump-to-hit and for
    precise splicing in apply_selected_replacements)."""
    line_no = 1
    line_start = 0
    for m in regex.finditer(text):
        # Advance line_no/line_start up to (not past) the match -- text is
        # scanned once overall since finditer() already yields matches in
        # order, so this stays O(len(text)) across the whole file rather
        # than O(matches * len(text)).
        while True:
            next_nl = text.find("\n", line_start)
            if next_nl == -1 or next_nl >= m.start():
                break
            line_no += 1
            line_start = next_nl + 1
        line_end = text.find("\n", line_start)
        if line_end == -1:
            line_end = len(text)
        yield FileHit(
            path=path,
            line_no=line_no,
            column=m.start() - line_start,
            line_text=text[line_start:line_end],
            match_start=m.start() - line_start,
            match_end=m.end() - line_start,
            abs_start=m.start(),
            abs_end=m.end(),
        ), m


def search_files(
    paths,
    pattern,
    *,
    case_sensitive=False,
    whole_word=False,
    use_regex=False,
    is_cancelled=None,
):
    """Yield a FileHit for every match of `pattern` in each of `paths`
    (an iterable of file paths -- see search_dir()/list_paths_for_scope()
    for building that list from a directory, open tabs, or a project).
    `is_cancelled`, if given, is polled between files and stops the search
    early (a plain callable returning bool, not a threading.Event, so
    callers on a background QThread can back it with a simple flag)."""
    if not pattern:
        return
    regex = _compile_pattern(pattern, case_sensitive, whole_word, use_regex)
    for path in paths:
        if is_cancelled is not None and is_cancelled():
            return
        text = read_text(path)
        if text is None:
            continue
        for hit, _m in _hits_in_text(path, text, regex):
            yield hit


def search_dir(root_dir, recursive=True, include_glob="*", exclude_glob=""):
    """Path list for the classic "search a directory tree" scope."""
    return list(_iter_paths(root_dir, recursive, include_glob, exclude_glob))


def plan_replacements(
    paths,
    pattern,
    replacement,
    *,
    case_sensitive=False,
    whole_word=False,
    use_regex=False,
    is_cancelled=None,
):
    """Build the list of files that would change, without writing anything
    -- callers should let the user review/select individual hits (see
    PlannedReplacement.selected) and then call apply_selected_replacements()
    on the result."""
    if not pattern:
        return []
    regex = _compile_pattern(pattern, case_sensitive, whole_word, use_regex)
    results = []
    for path in paths:
        if is_cancelled is not None and is_cancelled():
            break
        text = read_text(path)
        if text is None:
            continue
        planned = []
        for hit, m in _hits_in_text(path, text, regex):
            repl_text = m.expand(replacement) if use_regex else replacement
            planned.append(PlannedReplacement(hit=hit, replacement_text=repl_text))
        if planned:
            results.append(FileReplacement(path=path, original_text=text, planned=planned))
    return results


def apply_selected_replacements(replacements):
    """Write each FileReplacement's selected PlannedReplacements to disk,
    splicing each hit's replacement_text into the original text at its
    absolute offsets (processed back-to-front so earlier offsets stay
    valid). Files with nothing selected are left untouched. Returns an
    undo record: list[(path, original_text)] for files actually written,
    suitable for passing to undo_replacements()."""
    undo_record = []
    for repl in replacements:
        selected = [p for p in repl.planned if p.selected]
        if not selected:
            continue
        selected.sort(key=lambda p: p.hit.abs_start, reverse=True)
        new_text = repl.original_text
        for planned in selected:
            new_text = (
                new_text[: planned.hit.abs_start]
                + planned.replacement_text
                + new_text[planned.hit.abs_end :]
            )
        with open(repl.path, "w", encoding="utf-8") as f:
            f.write(new_text)
        undo_record.append((repl.path, repl.original_text))
    return undo_record


def undo_replacements(undo_record):
    """Restore each (path, original_text) pair written by
    apply_selected_replacements(). Best-effort: a file that's since been
    deleted or moved is skipped rather than raising."""
    for path, original_text in undo_record:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(original_text)
        except OSError:
            continue

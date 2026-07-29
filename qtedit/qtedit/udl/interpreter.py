"""Python port of LexUDL.cxx's colorizing runtime (`ColouriseTemplate1Doc` +
`doActions` + `doColorAction` + `doLookBackTest`), driving Scintilla's
container-lexing mode instead of a compiled C++ lexer. See lexres.py's
docstring for context.

`compute_fold_levels` ports `FoldUDLDoc`/`MainInfo::GetFoldChangeForLine`
(LexUDL.cxx:3491-3625, 1949-2225) -- the generic "flipper" mechanism only
(a global, style-keyed table of literal strings that open/close a fold
level, e.g. `fold ">" M_STAGC +` / `fold ">" M_ETAGC -" in the .udl
source). The HTML/markup-specific optional-close-tag stack heuristic
(GetFoldChangeForLine's `p_tagStack` handling, only active for XML-flavored
lexers) is NOT ported -- it's a hand-coded HTML tag-omission heuristic
layered on top of the generic mechanism, not part of the core UDL bytecode
format, and every non-markup UDL language (templates, embedded script
families) only needs the generic flipper mechanism.

Deliberately out of scope for this pass (see plan doc): incremental re-lex
(`synchronizeDocStart` in the original) -- this always re-lexes the whole
document from position 0, which is the same tradeoff editor.py's
Pygments-based highlighting already makes.
"""
import re

from . import lexres as L

_REDO_LIMIT = 1000

# Port of getOpposite() (LexUDL.cxx:3048-3057), used by the "match the
# opposite bracket" form of delimiter capture (e.g. a captured "(" means
# the closing delimiter to scan for is ")").
_OPPOSITE_BRACKET = {"[": "]", "{": "}", "(": ")", "<": ">"}

# SC_FOLDLEVEL* (Scintilla.h) -- same numeric values as
# Scintilla.FoldLevel.{Base,WhiteFlag,HeaderFlag} in pyside6-scintilla, so
# the ints this module returns can be passed to setFoldLevel() as-is
# without editor.py needing to import/translate anything UDL-specific.
FOLD_LEVEL_BASE = 0x400
FOLD_LEVEL_WHITE_FLAG = 0x1000
FOLD_LEVEL_HEADER_FLAG = 0x2000


class UDLInterpreter:
    def __init__(self, parsed: L.LexRes):
        self.lexres = parsed
        for state in parsed.states:
            transitions = list(state.transitions)
            if state.eof_transition:
                transitions.append(state.eof_transition)
            if state.empty_transition:
                transitions.append(state.empty_transition)
            for tran in transitions:
                if tran.search_type == L.TRAN_SEARCH_REGEX:
                    # MULTILINE so `$`/`^` mean line boundaries, not just the
                    # start/end of the whole buffer -- the original matched
                    # against a per-line PCRE subject (LexUDL.cxx's
                    # `LexString *p_CurrTextLine`), where `$` naturally meant
                    # "end of this line"; matching against the full document
                    # string here needs the flag to get the same meaning.
                    flags = re.MULTILINE
                    if tran.ignore_case:
                        flags |= re.IGNORECASE
                    tran.compiled_regex = re.compile(tran.search_string, flags)

    def colorize(self, text):
        """Return a list of (start, end, style_id) spans covering `text`."""
        spans = []
        length_doc = len(text)
        states = self.lexres.states
        istate = self.lexres.family_default_state.get(L.FAMILY_MARKUP, 1)
        curr_family = L.FAMILY_MARKUP
        state_stack = []
        current_delimiter = ""
        last_styled = 0
        redo_count = 0
        # Pending (state,family) pair to jump to once the current line ends
        # -- port of BufferStateInfo::curr_eol_transition (LexUDL.cxx:1263).
        # 0 means "nothing pending"; once set, nothing can override it until
        # it fires (see the at_eol handling in the main loop below).
        curr_eol_transition = 0

        def line_start_after(pos):
            """Position of the start of the line following the one
            containing `pos` -- port of styler.LineStart(GetLine(pos)+1)."""
            nl = text.find("\n", pos)
            return length_doc if nl == -1 else nl + 1

        def paint(upto_pos, style_num, no_keyword):
            nonlocal last_styled
            if style_num < 0 or upto_pos <= last_styled:
                return
            fam_info = self.lexres.family_info.get(curr_family)
            actual_style = style_num
            if (
                fam_info is not None
                and not no_keyword
                and style_num == fam_info.identifier_style
                and fam_info.keyword_style >= 0
            ):
                token_text = text[last_styled:upto_pos]
                if token_text in fam_info.keywords:
                    actual_style = fam_info.keyword_style
            spans.append((last_styled, upto_pos, actual_style))
            last_styled = upto_pos

        def style_at(pos):
            for s, e, st in reversed(spans):
                if s <= pos < e:
                    return st
                if e <= pos:
                    break
            return None

        def segment_text(pos, style):
            """Text of the contiguous same-style run ending at (and
            including) `pos`, merging adjacent same-style spans -- mirrors
            getSegmentParts (LexUDL.cxx:2852)."""
            idx = len(spans) - 1
            while idx >= 0 and not (spans[idx][0] <= pos < spans[idx][1]):
                idx -= 1
            if idx < 0:
                return pos, text[pos : pos + 1]
            seg_start = spans[idx][0]
            idx -= 1
            while idx >= 0 and spans[idx][2] == style:
                seg_start = spans[idx][0]
                idx -= 1
            return seg_start, text[seg_start : pos + 1]

        def lookback_test_passes(tran, old_pos):
            """Port of doLookBackTest (LexUDL.cxx:2889)."""
            if old_pos <= 0 or not tran.token_check:
                return True
            fam_info = self.lexres.family_info.get(curr_family)
            if fam_info is None:
                return True
            # The original colors the "upto" span here unconditionally, even
            # though this candidate transition may still be rejected below
            # (it needs the text-to-the-left already committed to inspect
            # it) -- paint() is idempotent for a given position so repeating
            # this across several rejected candidates is harmless.
            paint(old_pos, tran.upto_color, tran.no_keyword)
            lbtests = fam_info.lookback_tests
            if lbtests is None:
                return True
            pos = old_pos - 1
            while pos > 0:
                this_style = style_at(pos)
                if this_style is None or not lbtests.style_in_range(this_style):
                    return True
                seg_start, seg_text = segment_text(pos, this_style)
                action = -1
                for t in lbtests.tests:
                    if t.style != this_style:
                        continue
                    if t.test_type == L.LBTEST_LIST_ALL:
                        action = t.action
                    elif t.test_type == L.LBTEST_LIST_KEYWORDS:
                        if t.keywords and seg_text in t.keywords:
                            action = t.action
                    elif t.test_type == L.LBTEST_LIST_STRINGS:
                        if t.strings and any(
                            seg_text.endswith(s) for s in t.strings
                        ):
                            action = t.action
                    if action != -1:
                        break
                if action == -1:
                    action = lbtests.get_default(this_style)
                if action == L.LBTEST_ACTION_REJECT:
                    return False
                elif action == L.LBTEST_ACTION_ACCEPT:
                    return True
                else:  # SKIP -- keep walking further back
                    pos = seg_start - 1
            return True

        i = 0
        while i < length_doc:
            if istate >= len(states):
                break
            state_info = states[istate]

            matched_tran = None
            matched_regex = None
            new_pos = i
            for tran in state_info.transitions:
                m_end = None
                m = None
                if tran.search_type == L.TRAN_SEARCH_STRING:
                    if text.startswith(tran.search_string, i):
                        m_end = i + len(tran.search_string)
                elif tran.search_type == L.TRAN_SEARCH_REGEX:
                    m = tran.compiled_regex.match(text, i)
                    if m:
                        m_end = m.end()
                elif tran.search_type == L.TRAN_SEARCH_DELIMITER:
                    if current_delimiter and text.startswith(current_delimiter, i):
                        m_end = i + len(current_delimiter)
                        # Not undoable even if the lookback test below
                        # rejects this candidate -- matches LexUDL.cxx's
                        # main loop (3372-3384), which clears it here too.
                        if not tran.keep_current_delimiter:
                            current_delimiter = ""
                if m_end is not None and lookback_test_passes(tran, i):
                    matched_tran = tran
                    matched_regex = m
                    new_pos = m_end
                    break

            if matched_tran is None:
                matched_tran = state_info.empty_transition
                new_pos = i
            if matched_tran is None:
                # No rule matches at all -- shouldn't happen with a complete
                # grammar; consume one char unstyled so we can't hang.
                i += 1
                redo_count = 0
                continue

            # ---- doActions (LexUDL.cxx:2717) ----
            if not matched_tran.token_check and i > 0:
                paint(i, matched_tran.upto_color, matched_tran.no_keyword)
            paint(new_pos, matched_tran.include_color, matched_tran.no_keyword)

            # LexUDL.cxx sets BufferStateInfo::do_redo from the *current*
            # transition immediately before calling doActions (main loop,
            # LexUDL.cxx:3419), so doActions' own do_redo check always
            # reflects this transition, not the previous one.
            do_redo = matched_tran.do_redo
            orig_old_pos = i
            if matched_tran.search_type == L.TRAN_SEARCH_EMPTY:
                pass
            elif do_redo:
                pass
            else:
                i = new_pos

            if matched_tran.clear_current_delimiter:
                current_delimiter = ""
            if (
                matched_tran.search_type == L.TRAN_SEARCH_REGEX
                and matched_tran.target_delimiter
                and matched_regex is not None
            ):
                # Port of setNewDelimiter (LexUDL.cxx:3076-3107). Packed as
                # (use_opposite, group_num) via the same SF_MAKE_PAIR scheme
                # as push_pop_state/eol_target_state -- group_num=0 means
                # "the whole match" (re.Match.group(0)), same as PCRE's
                # ovector[0]; a specific N captures that numbered group
                # instead of always taking the whole matched text.
                use_opposite = L.sf_get_state(matched_tran.target_delimiter)
                group_num = L.sf_get_family(matched_tran.target_delimiter)
                try:
                    captured = matched_regex.group(group_num)
                except IndexError:
                    # group_num beyond what this pattern actually captures
                    # -- malformed grammar; LexUDL.cxx's equivalent bounds
                    # check (group_num <= num_captured_groups) just leaves
                    # current_delimiter unchanged in this case too.
                    captured = None
                if captured is not None:
                    if use_opposite:
                        if len(captured) == 1:
                            current_delimiter = _OPPOSITE_BRACKET.get(
                                captured, captured
                            )
                        # else: malformed grammar (opposite-delimiter capture
                        # must be exactly 1 char) -- LexUDL.cxx just logs and
                        # leaves current_delimiter unchanged; same here.
                    else:
                        current_delimiter = captured

            # ---- at_eol: determine whether a previously-staged pending
            # transition fires now (LexUDL.cxx:2749-2773, 2795-2803) ----
            eol_fired = False
            new_state = 0
            new_family = curr_family
            if curr_eol_transition:
                start_line = text.count("\n", 0, orig_old_pos)
                end_line = text.count("\n", 0, new_pos)
                next_line_start = line_start_after(orig_old_pos)
                if end_line > start_line or (
                    orig_old_pos >= next_line_start - 1 and new_pos >= next_line_start
                ):
                    eol_fired = True
                    new_state = L.sf_get_state(curr_eol_transition)
                    new_family = L.sf_get_family(curr_eol_transition)
                    curr_eol_transition = 0
                    # Snap the resume position to the start of the next
                    # line, overriding wherever the triggering transition's
                    # own match actually ended (LexUDL.cxx:2755-2759).
                    i = next_line_start

            # ---- stage a new pending eol-transition, if this transition
            # carries one (LexUDL.cxx:2783-2794) -- "once one is set,
            # nothing can override it" until it fires above. ----
            if matched_tran.eol_target_state and not curr_eol_transition:
                curr_eol_transition = matched_tran.eol_target_state

            # eol firing deliberately squelches any push/pop/replace that
            # this same transition would otherwise have done
            # (LexUDL.cxx:2795-2812).
            push_pop = matched_tran.push_pop_state
            if eol_fired:
                pass
            elif push_pop > 0:
                state_stack.append(push_pop)
            elif push_pop == -1:
                popped = state_stack.pop() if state_stack else 0
                new_state = L.sf_get_state(popped)
                new_family = L.sf_get_family(popped)
            elif matched_tran.replace_sstate_top > 0:
                if state_stack:
                    state_stack[-1] = matched_tran.replace_sstate_top

            if not new_state:
                new_state = matched_tran.new_state
                if new_state >= 1:
                    new_family = matched_tran.new_family

            if 1 <= new_state < len(states):
                istate = new_state
                if new_family >= 0 and curr_family != new_family:
                    curr_family = new_family

            if orig_old_pos != i:
                redo_count = 0
            else:
                redo_count += 1
                if redo_count > _REDO_LIMIT:
                    # Runaway redo loop -- force progress, mirroring
                    # LexUDL.cxx's redoLimit guard (LexUDL.cxx:3404-3416).
                    do_redo = False
                    i += 1
                    redo_count = 0

        if istate < len(states) and states[istate].eof_transition:
            tran = states[istate].eof_transition
            if not tran.token_check and i > 0:
                paint(i, tran.upto_color, tran.no_keyword)
            paint(length_doc, tran.include_color, tran.no_keyword)

        if last_styled < length_doc:
            spans.append((last_styled, length_doc, 0))
        return spans

    def compute_fold_levels(self, text, spans, fold_at_else=True, fold_compact=True):
        """Return one Scintilla fold-level int per line of `text`, given the
        (start, end, style) spans already produced by `colorize()`. Port of
        FoldUDLDoc's per-line loop (LexUDL.cxx:3578-3611) plus the generic
        flipper-scan half of GetFoldChangeForLine (LexUDL.cxx:2172-2221) --
        see the module docstring for what's not ported.
        """
        flippers_by_style = {}
        for fl in self.lexres.flippers:
            if fl is not None:
                flippers_by_style.setdefault(fl.style, []).append(fl)

        lines = text.split("\n")
        num_lines = len(lines)
        line_starts = [0] * num_lines
        pos = 0
        for idx, line in enumerate(lines):
            line_starts[idx] = pos
            pos += len(line) + 1
        has_non_space = [bool(line.strip()) for line in lines]

        # net_change/min_change are per-line quantities (reset at each line
        # boundary, LexUDL.cxx re-creates them per GetFoldChangeForLine
        # call) -- computed here in one forward pass over `spans` rather
        # than one pass per line, tracking which line we're currently in.
        net_changes = [0] * num_lines
        min_changes = [0] * num_lines
        cur_line = 0
        net_change = 0
        min_change = 0

        def flush_line():
            net_changes[cur_line] = net_change
            min_changes[cur_line] = min_change

        for start, end, style in spans:
            flippers = flippers_by_style.get(style)
            p = start
            while p < end:
                while cur_line + 1 < num_lines and p >= line_starts[cur_line + 1]:
                    flush_line()
                    cur_line += 1
                    net_change = 0
                    min_change = 0
                matched = None
                if flippers:
                    for fl in flippers:
                        fstr = fl.string
                        if text.startswith(fstr, p) and p + len(fstr) <= end:
                            matched = fl
                            break
                if matched is not None:
                    if matched.direction > 0:
                        min_change = min(min_change, net_change)
                    net_change += matched.direction
                    p += len(matched.string)
                else:
                    p += 1
        flush_line()

        levels = []
        level_prev = 0
        for ln in range(num_lines):
            level_current = max(0, level_prev + net_changes[ln])
            level_use = max(0, level_prev + min_changes[ln]) if fold_at_else else level_prev
            lev = level_use
            if fold_compact and not has_non_space[ln]:
                lev |= FOLD_LEVEL_WHITE_FLAG
            if level_current > level_use and has_non_space[ln]:
                lev |= FOLD_LEVEL_HEADER_FLAG
            levels.append(lev | FOLD_LEVEL_BASE)
            level_prev = level_current
        return levels

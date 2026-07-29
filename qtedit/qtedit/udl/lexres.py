"""Parser for Komodo's `.lexres` compiled-UDL-lexer format.

find_lexres_for_language() below expects the prebuilt .lexres files sitting
under build/release/udl/build/ (see qtedit/qtedit/codeintel_client.py's
DEFAULT_IMPORT_PATHS docstring for the same "reuse a prior partial build's
artifacts" pattern) -- a fresh checkout without that directory just won't
find any UDL languages, falling back to the Pygments highlighter.

`.lexres` files are produced by src/udl/ludditelib (`luddite compile`) from
`.udl` language-definition sources, and were historically consumed by
Komodo's own C++ Scintilla lexer at src/scintilla/lexers/LexUDL.cxx. That
lexer doesn't exist in modern/upstream Scintilla, so this module -- together
with interpreter.py -- reimplements just enough of LexUDL.cxx's reader
(`MainInfo::Init`) and runtime (`ColouriseTemplate1Doc`) to drive Scintilla's
container-lexing mode in pure Python 3. No XPCOM, no Python 2, no C++.

Format: a line-oriented `opcode:arg1:arg2:...` stream (opcode names/values
below are the `ASTC_*` constants at LexUDL.cxx:244-297, reader version 1.2).
String-valued opcodes (keyword lists, patterns, language names) are built
via a small "scratch buffer" protocol: ASTC_SCRATCH_BUFFER_START announces a
string is coming, one or more ASTC_SCRATCH_BUFFER_APPEND lines supply its
content (a string can span multiple lines), and the *next* opcode that needs
a string argument (e.g. ASTC_LANGUAGE_NAME, ASTC_CREATE_NEW_TRAN) consumes
whatever is currently in the scratch buffer.
"""
import os
from dataclasses import dataclass, field

KOMODO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# ASTC_* opcodes (LexUDL.cxx:244-297)
ASTC_META_COMMENTS = 1
ASTC_META_VERSION_MAJOR = 2
ASTC_META_VERSION_MINOR = 3
ASTC_META_VERSION_SUBMINOR = 4
ASTC_SCRATCH_BUFFER_START = 11
ASTC_SCRATCH_BUFFER_APPEND = 12
ASTC_LANGUAGE_NAME = 13
ASTC_F_COLOR = 14
ASTC_F_STYLE = 15
ASTC_F_OPERATOR = 16
ASTC_FLIPPER_COUNT = 17
ASTC_CURRENT_FAMILY = 18
ASTC_F_DEFAULT_STATE = 19
ASTC_F_FLIPPER = 20
ASTC_F_WORDLIST = 21
ASTC_F_KEYWORD_STYLE = 22
ASTC_F_LOOKBACK_TESTS_CREATE = 23
ASTC_F_LOOKBACK_TESTS_INIT = 24
ASTC_F_LOOKBACK_TESTS_COUNT = 25
ASTC_LBT_GET = 26
ASTC_LBT_ACTION_STYLE = 27
ASTC_LBT_STRINGS = 28
ASTC_LBT_WORDLIST = 29
ASTC_LBT_DEFAULT = 30
ASTC_LBT_TEST = 31
ASTC_TTABLE_NUM_UNIQUE_STATES = 32
ASTC_TTABLE_UNIQUE_STATE = 33
ASTC_TTABLE_CREATE_TRANS = 34
ASTC_TTABLE_GET_TBLOCK = 35
ASTC_CREATE_NEW_TRAN = 36
ASTC_TRAN_SET_F = 37
ASTC_TRAN_PUSH_STATE = 38
ASTC_TRAN_POP_STATE = 39
ASTC_TBLOCK_APPEND_TRAN = 40
ASTC_TBLOCK_EOF_TRAN = 41
ASTC_TBLOCK_EMPTY_TRAN = 42
ASTC_SUBLANGUAGE_NAME = 43
ASTC_EXTENSION = 44
ASTC_TRAN_EOL_STATE = 45
ASTC_TRAN_SET_DELIMITER = 46
ASTC_TRAN_KEEP_DELIMITER = 47
ASTC_TRAN_WRITER_VERSION = 48
ASTC_TRAN_CLEAR_DELIMITER = 49
ASTC_TRAN_REPLACE_STATE = 50

# Opcodes whose sole argument is a raw string (not colon-delimited numbers) --
# mirrors MainInfo::Init's `switch` that special-cases these before calling
# GetNumsFromLine (LexUDL.cxx:1357-1367).
_STRING_ARG_OPCODES = {
    ASTC_META_COMMENTS,
    ASTC_SCRATCH_BUFFER_APPEND,
    ASTC_LANGUAGE_NAME,
    ASTC_SUBLANGUAGE_NAME,
}

# TRAN_SEARCH_* (LexUDL.cxx:201-205)
TRAN_SEARCH_STRING = 1
TRAN_SEARCH_REGEX = 2
TRAN_SEARCH_EMPTY = 3
TRAN_SEARCH_EOF = 4
TRAN_SEARCH_DELIMITER = 5

# LBTEST_ACTION_* (LexUDL.cxx:212-215)
LBTEST_ACTION_SKIP = 0
LBTEST_ACTION_ACCEPT = 1
LBTEST_ACTION_REJECT = 2

# LBTEST_LIST_* (LexUDL.cxx:217-219)
LBTEST_LIST_ALL = 1
LBTEST_LIST_KEYWORDS = 2
LBTEST_LIST_STRINGS = 3

# TRAN_FAMILY_* (LexUDL.cxx:223-227)
FAMILY_MARKUP = 0
FAMILY_CSS = 1
FAMILY_CSL = 2
FAMILY_SSL = 3
FAMILY_TEMPLATE = 4
NUM_FAMILIES = 5


def sf_make_pair(state, family):
    """LexUDL.cxx SF_MAKE_PAIR: pack (state, family) into one int."""
    return (family << 24) | (state & 0xFFFFFF)


def sf_get_state(packed):
    return packed & 0x00FFFFFF


def sf_get_family(packed):
    return (packed & ~0x00FFFFFF) >> 24


@dataclass
class Transition:
    search_type: int
    search_string: str
    upto_color: int
    include_color: int
    do_redo: bool
    new_state: int
    token_check: int
    ignore_case: int
    no_keyword: bool
    new_family: int = -1
    push_pop_state: int = 0
    replace_sstate_top: int = 0
    eol_target_state: int = 0
    target_delimiter: int = 0
    keep_current_delimiter: bool = False
    clear_current_delimiter: bool = False
    compiled_regex = None  # set lazily by the interpreter (re.Pattern)


@dataclass
class TransitionInfo:
    """One state's set of outgoing transitions, tried in declaration order."""
    transitions: list = field(default_factory=list)
    eof_transition: Transition = None
    empty_transition: Transition = None


@dataclass
class LookBackTest:
    """One rule within a family's LookBackTests (LexUDL.cxx:328-439):
    "when the text immediately to the left is in `style`, is `action`
    (accept/reject/skip-to-the-next-run-further-left) -- optionally only
    when that run's text is one of `keywords` or ends with one of
    `strings`, per `test_type`."""
    style: int = -1
    action: int = LBTEST_ACTION_REJECT
    test_type: int = LBTEST_LIST_ALL
    keywords: frozenset = None
    strings: list = None


@dataclass
class LookBackTests:
    """A family's full set of lookback rules (LexUDL.cxx:450-544), used to
    gate `token_check` transitions -- e.g. distinguishing "/" as division
    vs. the start of a regex literal by checking what precedes it."""
    base_style: int = 0
    num_styles: int = 0
    defaults: dict = field(default_factory=dict)  # style -> action
    tests: list = field(default_factory=list)  # list[LookBackTest]

    def style_in_range(self, style):
        return self.base_style <= style <= self.base_style + self.num_styles

    def get_default(self, style):
        return self.defaults.get(style, LBTEST_ACTION_REJECT)


@dataclass
class Flipper:
    """One folding rule (LexUDL.cxx's `Flipper` class, 601-654): matching
    `string` while lexed with `style` changes the running fold level by
    `direction` (+1 opens a fold, -1 closes one). Global across the whole
    `.lexres` (MainInfo::pp_Flippers), disambiguated only by `style` --
    not scoped per-family despite `fold` directives being written inside a
    `family` block in the .udl source."""
    string: str
    style: int
    direction: int


@dataclass
class FamilyInfo:
    start_state: int = -1
    keywords: frozenset = field(default_factory=frozenset)
    identifier_style: int = -1
    keyword_style: int = -1
    sublanguage_name: str = None
    lookback_tests: LookBackTests = None


@dataclass
class LexRes:
    language_name: str = None
    family_default_state: dict = field(default_factory=dict)  # family idx -> start state
    family_info: dict = field(default_factory=dict)  # family idx -> FamilyInfo
    states: list = field(default_factory=list)  # index -> TransitionInfo
    flippers: list = field(default_factory=list)  # list[Flipper], for folding


class LexResParseError(Exception):
    pass


def parse_lexres(path):
    """Parse a `.lexres` file into a LexRes structure.

    Mirrors MainInfo::Init (LexUDL.cxx:1286) line-by-line, but keeps the
    result in a plain Python object graph instead of C++ MainInfo/
    TransitionTable/FamilyInfo objects.
    """
    result = LexRes()
    scratch = []
    states = []
    current_family = None
    current_family_info = None
    current_tblock = None  # TransitionInfo currently being appended to
    current_tran = None  # Transition currently under construction
    current_lbtests = None  # LookBackTests currently being built
    current_lbtest = None  # LookBackTest currently being mutated

    with open(path, "r", encoding="utf-8") as f:
        for lineno, raw_line in enumerate(f, start=1):
            line = raw_line.rstrip("\r\n")
            if not line or line.startswith("#"):
                continue
            head, _, rest = line.partition(":")
            try:
                opcode = int(head)
            except ValueError:
                raise LexResParseError(f"{path}:{lineno}: bad opcode {head!r}")

            if opcode in _STRING_ARG_OPCODES:
                args = None
                str_arg = rest
            else:
                str_arg = None
                args = [int(a) for a in rest.split(":")] if rest else []

            if opcode == ASTC_META_COMMENTS:
                pass
            elif opcode in (
                ASTC_META_VERSION_MAJOR,
                ASTC_META_VERSION_MINOR,
                ASTC_META_VERSION_SUBMINOR,
                ASTC_TRAN_WRITER_VERSION,
            ):
                pass  # version metadata, not needed to interpret the rest
            elif opcode == ASTC_SCRATCH_BUFFER_START:
                scratch = []
            elif opcode == ASTC_SCRATCH_BUFFER_APPEND:
                scratch.append(str_arg)
            elif opcode == ASTC_LANGUAGE_NAME:
                result.language_name = "".join(scratch)
            elif opcode == ASTC_SUBLANGUAGE_NAME:
                if current_family_info is not None:
                    current_family_info.sublanguage_name = "".join(scratch)
            elif opcode in (ASTC_F_COLOR, ASTC_F_STYLE, ASTC_F_OPERATOR):
                pass  # presentation metadata (Komodo scheme colors), not styling logic
            elif opcode == ASTC_FLIPPER_COUNT:
                result.flippers = [None] * args[0]
            elif opcode == ASTC_CURRENT_FAMILY:
                current_family = args[0]
                current_family_info = result.family_info.setdefault(
                    current_family, FamilyInfo()
                )
                current_lbtests = None
                current_lbtest = None
            elif opcode == ASTC_F_DEFAULT_STATE:
                current_family_info.start_state = args[0]
                result.family_default_state[current_family] = args[0]
            elif opcode == ASTC_F_FLIPPER:
                index, style, direction = args
                result.flippers[index] = Flipper(
                    string="".join(scratch), style=style, direction=direction
                )
            elif opcode == ASTC_F_WORDLIST:
                current_family_info.keywords = frozenset(
                    "".join(scratch).split()
                )
            elif opcode == ASTC_F_KEYWORD_STYLE:
                current_family_info.identifier_style = args[0]
                current_family_info.keyword_style = args[1]
            elif opcode == ASTC_F_LOOKBACK_TESTS_CREATE:
                current_lbtests = LookBackTests()
                current_family_info.lookback_tests = current_lbtests
                current_lbtest = None
            elif opcode == ASTC_F_LOOKBACK_TESTS_INIT:
                current_lbtests.base_style = args[0]
                current_lbtests.num_styles = args[1]
            elif opcode == ASTC_F_LOOKBACK_TESTS_COUNT:
                current_lbtests.tests = [LookBackTest() for _ in range(args[0])]
            elif opcode == ASTC_LBT_GET:
                current_lbtest = current_lbtests.tests[args[0]]
            elif opcode == ASTC_LBT_ACTION_STYLE:
                current_lbtest.action = args[0]
                current_lbtest.style = args[1]
            elif opcode == ASTC_LBT_STRINGS:
                current_lbtest.test_type = LBTEST_LIST_STRINGS
                current_lbtest.strings = "".join(scratch).split()
            elif opcode == ASTC_LBT_WORDLIST:
                current_lbtest.test_type = LBTEST_LIST_KEYWORDS
                current_lbtest.keywords = frozenset("".join(scratch).split())
            elif opcode == ASTC_LBT_DEFAULT:
                current_lbtests.defaults[args[0]] = args[1]
            elif opcode == ASTC_LBT_TEST:
                pass  # LBT_GET already placed the right object at this index
            elif opcode == ASTC_TTABLE_NUM_UNIQUE_STATES:
                pass  # only needed for incremental-restart sync, which this MVP skips
            elif opcode == ASTC_TTABLE_UNIQUE_STATE:
                pass
            elif opcode == ASTC_TTABLE_CREATE_TRANS:
                count = args[0]
                states = [TransitionInfo() for _ in range(count)]
                result.states = states
            elif opcode == ASTC_TTABLE_GET_TBLOCK:
                current_tblock = states[args[0]]
                current_tran = None
            elif opcode == ASTC_CREATE_NEW_TRAN:
                # 7-arg (pre-4.0a5) or 8-arg (with no_keyword) form.
                if len(args) == 7:
                    a = args
                    no_keyword = False
                else:
                    a = args[:7]
                    no_keyword = bool(args[7])
                current_tran = Transition(
                    search_type=a[0],
                    search_string="".join(scratch),
                    upto_color=a[1],
                    include_color=a[2],
                    do_redo=bool(a[3]),
                    new_state=a[4],
                    token_check=a[5],
                    ignore_case=a[6],
                    no_keyword=no_keyword,
                )
            elif opcode == ASTC_TRAN_SET_F:
                current_tran.new_family = args[0]
            elif opcode == ASTC_TRAN_PUSH_STATE:
                current_tran.push_pop_state = sf_make_pair(args[0], args[1])
            elif opcode == ASTC_TRAN_POP_STATE:
                current_tran.push_pop_state = -1
            elif opcode == ASTC_TRAN_REPLACE_STATE:
                current_tran.replace_sstate_top = sf_make_pair(args[0], args[1])
            elif opcode == ASTC_TBLOCK_APPEND_TRAN:
                current_tblock.transitions.append(current_tran)
            elif opcode == ASTC_TBLOCK_EOF_TRAN:
                current_tblock.eof_transition = current_tran
            elif opcode == ASTC_TBLOCK_EMPTY_TRAN:
                current_tblock.empty_transition = current_tran
            elif opcode == ASTC_TRAN_EOL_STATE:
                current_tran.eol_target_state = sf_make_pair(args[0], args[1])
            elif opcode == ASTC_TRAN_SET_DELIMITER:
                current_tran.target_delimiter = sf_make_pair(args[0], args[1])
            elif opcode == ASTC_TRAN_KEEP_DELIMITER:
                current_tran.keep_current_delimiter = True
            elif opcode == ASTC_TRAN_CLEAR_DELIMITER:
                current_tran.clear_current_delimiter = True
            elif opcode == ASTC_EXTENSION:
                pass
            else:
                raise LexResParseError(
                    f"{path}:{lineno}: unhandled opcode {opcode}"
                )

    return result


def find_lexres_for_language(language_name):
    """Path to a prebuilt `.lexres` for `language_name`, or None if there
    isn't one (e.g. no build/release/ tree, or this language isn't UDL-based
    at all -- most languages use one of Scintilla's built-in/Pygments
    lexers instead, UDL is only for the handful that need it)."""
    path = os.path.join(
        KOMODO_ROOT,
        "build",
        "release",
        "udl",
        "build",
        language_name,
        "lexers",
        f"{language_name}.lexres",
    )
    return path if os.path.isfile(path) else None

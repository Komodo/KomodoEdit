// Scintilla source code edit control
/** @file LexUDL.cxx
 ** Lexer for user-defined templates -- first try, with a hard-wired table
 **/
// Copyright 2006 by ActiveState Software Inc.
// Authors: Eric Promislow <ericp@activestate.com>
// The License.txt file describes the conditions under which this software may be distributed.

#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdio.h>
#include <stdarg.h>

// Perl-compatible regular expression library -- see pcre.org
#define PCRE_STATIC
#include <pcre.h>

#include "Platform.h"

#include "PropSet.h"
#include "Accessor.h"
#include "KeyWords.h"
#include "Scintilla.h"
#include "SciLexer.h"

#include "SString.h"

#ifdef SCI_NAMESPACE
using namespace Scintilla;
#endif

#define assert PLATFORM_ASSERT

//XXX Identical to Perl, put in common area
static inline bool isEOLChar(char ch) {
    return (ch == '\r') || (ch == '\n');
}

#define isSafeASCII(ch) ((unsigned int)(ch) <= 127)
// This one's redundant, but makes for more readable code
#define isHighBitChar(ch) ((unsigned int)(ch) > 127)

// #pragma message("Compiling Komodo-devel/contrib/scintilla/src/LexUDL.cxx")

static inline bool isSafeAlpha(char ch) {
    return (isSafeASCII(ch) && isalpha(ch)) || ch == '_';
}

static inline bool isSafeAlnum(char ch) {
    return (isSafeASCII(ch) && isalnum(ch)) || ch == '_';
}

static inline bool isSafeAlnumOrHigh(char ch) {
    return isHighBitChar(ch) || isalnum(ch) || ch == '_';
}

static inline bool isSafeDigit(char ch) {
    return isSafeASCII(ch) && isdigit(ch);
}

static inline bool isSafeWordcharOrHigh(char ch) {
    // Error: scintilla's KeyWords.h includes '.' as a word-char
    // we want to separate things that can take methods from the
    // methods.
    return isHighBitChar(ch) || isalnum(ch) || ch == '_';
}

static bool inline iswhitespace(char ch) {
    return ch == ' ' || ch == '\t' || ch == '\r' || ch == '\n';
}

#define STYLE_MASK 63
#define actual_style(style) (style & STYLE_MASK)

static inline int safeStyleAt(int pos, Accessor &styler) {
    return actual_style((unsigned int)styler.StyleAt(pos));
}

#define MAX_KEYWORD_LENGTH 200

static FILE *fp_log = NULL;

static char opposite(char ch) {
    if (ch == '(')
        return ')';
    if (ch == '[')
        return ']';
    if (ch == '{')
        return '}';
    if (ch == '<')
        return '>';
    return ch;
}

static void getRange(unsigned int start,
		unsigned int end,
		Accessor &styler,
		char *s,
		unsigned int len) {
	unsigned int i = 0;
	while ((i < end - start + 1) && (i < len-1)) {
		s[i] = styler[start + i];
		i++;
	}
	s[i] = '\0';
}

static void GetCurrent(char *s, unsigned int len, unsigned int end,
                       Accessor &styler) {
	getRange(styler.GetStartSegment(), end, styler, s, len);
}

#ifndef LOG_MEM
#define LOG_MEM
#endif
#undef LOG_MEM
#ifdef LOG_MEM

#if _WIN32
#pragma message("XXX: #undef LOG_MEM to stop logging mem usage in UDL")
#endif

static void OpenFPLog()
{
    fp_log = fopen("LexUDL.log", "w");
}

#include <time.h>

static void LogEvent(bool entering, char *funcname, void *p)
{
    if (fp_log) {
        time_t t;
        time(&t);
        struct tm* p_tm = localtime(&t);
        
        if (fp_log) {
            fprintf(fp_log, "%04d-%02d-%02dT%02d:%02d:%02d -- %s: %s(0x%lx)\n",
                    p_tm->tm_year % 100,
                    p_tm->tm_mon + 1,
                    p_tm->tm_mday,
                    p_tm->tm_hour,
                    p_tm->tm_min,
                    p_tm->tm_sec,
                    funcname,
                    entering ? ">> Entering" : "<< Exiting",
                    p);
            fflush(fp_log);
        }
    }
}
#else
#define OpenFPLog()
#define LogEvent(status, funcname, p)
#endif
// end ifdef LOG_MEM


// ****************************************************************
// **************** Classes from UDL_Tables.h ****************
// ****************************************************************


// Definitions used by parts of the lexer

/* Define the transition table -- these should be cached during a session,
 * in each instance of the lexer.
 */

#define TRAN_SEARCH_STRING 1
#define TRAN_SEARCH_REGEX  2
#define TRAN_SEARCH_EMPTY  3
#define TRAN_SEARCH_EOF    4
#define TRAN_SEARCH_DELIMITER    5

/* Definitions used for look-back tests in languages that
 * have ambiguous lexemes, like '/' in JS/Perl/Ruby that can 
 * either start a reg-ex or be the division operator.
 */

#define LBTEST_ACTION_SKIP	0
#define LBTEST_ACTION_ACCEPT	1
#define LBTEST_ACTION_REJECT	2
#define LBTEST_NUM_ACTIONS		3

#define LBTEST_LIST_ALL			1
#define LBTEST_LIST_KEYWORDS	2
#define LBTEST_LIST_STRINGS		3

// We always have up to five families of styles

#define TRAN_FAMILY_MARKUP		0
#define TRAN_FAMILY_CSS			1
#define TRAN_FAMILY_CSL			2 // Client-side lang, usually JS
#define TRAN_FAMILY_SSL			3 // Server-side lang -- PHP,Ruby,Python,etc
#define TRAN_FAMILY_TEMPLATE	4 // Template augmentation lang, like Smarty

// No way we're going to have thousands of states, right...?

#define SF_MAKE_PAIR(state, family) 	((family) << 24 | (state))
#define SF_GET_STATE(fstate)			((fstate) & 0x00ffffff)
#define SF_GET_FAMILY(fstate)			(((fstate) & ~0x00ffffff) >> 24)

// ASTC : ActiveState Template Code

// In most of these code words like 'set' and 'current' are implicit

// 'F' : "FAMILY"
// 'LBT' : Lookback test"

// See bytecode.txt for a fuller description

#define ASTC_NOP					0

#define ASTC_META_COMMENTS			1
#define ASTC_META_VERSION_MAJOR		2
#define ASTC_META_VERSION_MINOR		3
#define ASTC_META_VERSION_SUBMINOR	4

#define ASTC_SCRATCH_BUFFER_START	11
#define ASTC_SCRATCH_BUFFER_APPEND	12

#define ASTC_LANGUAGE_NAME			13
#define ASTC_F_COLOR				14
#define ASTC_F_STYLE	    		15
#define ASTC_F_OPERATOR				16
#define ASTC_FLIPPER_COUNT			17
#define ASTC_CURRENT_FAMILY			18
#define ASTC_F_DEFAULT_STATE		19
#define ASTC_F_FLIPPER				20
#define ASTC_F_WORDLIST				21
#define ASTC_F_KEYWORD_STYLE		22

#define ASTC_F_LOOKBACK_TESTS_CREATE	23
#define ASTC_F_LOOKBACK_TESTS_INIT	24
#define ASTC_F_LOOKBACK_TESTS_COUNT	25

#define ASTC_LBT_GET				26
#define ASTC_LBT_ACTION_STYLE		27
#define ASTC_LBT_STRINGS			28
#define ASTC_LBT_WORDLIST			29
#define ASTC_LBT_DEFAULT			30
#define ASTC_LBT_TEST				31

#define ASTC_TTABLE_NUM_UNIQUE_STATES	32
#define ASTC_TTABLE_UNIQUE_STATE	33
#define ASTC_TTABLE_CREATE_TRANS	34
#define ASTC_TTABLE_GET_TBLOCK		35
#define ASTC_CREATE_NEW_TRAN		36
#define ASTC_TRAN_SET_F				37
#define ASTC_TRAN_PUSH_STATE		38
#define ASTC_TRAN_POP_STATE			39
#define ASTC_TBLOCK_APPEND_TRAN		40
#define ASTC_TBLOCK_EOF_TRAN		41
#define ASTC_TBLOCK_EMPTY_TRAN		42

#define ASTC_SUBLANGUAGE_NAME		43
#define ASTC_EXTENSION				44
#define ASTC_TRAN_EOL_STATE			45
#define ASTC_TRAN_SET_DELIMITER		46
#define ASTC_TRAN_KEEP_DELIMITER	47

#define ASTC_TRAN_WRITER_VERSION	48

#define ASTC_TRAN_CLEAR_DELIMITER	49

#define READER_VERSION_MAJOR	1
#define READER_VERSION_MINOR	1
#define READER_VERSION_SUBMINOR	0

static char *new_strdup(const char *s) {
    if (!s) {
        return NULL;
    }
    size_t slen = strlen(s);
    char *ns = new char[slen + 1];
    if (!ns) {
        return NULL;
    }
    strcpy(ns, s);
    return ns;
}

// There's probably a more OO-way of doing this...  see gang of 4

// A test-obj is either a wordlist -- testing for membership,
// a list of strings -- used to see if we're looking at one
// of them when two or more contiguous tokens can have the same
// style
// or it's "ALL", which means all instances of this style are
// handled the same way.

class LookBackTestObj {
    private:
    int			test_type;   // strings/keywords/all
    int			test_style;  // style it expects to test on
    int			result_action; // accept/reject/skip
    WordList   *p_wl;
    char	  **pp_strings;
    char	   *p_buf;
    public:
    LookBackTestObj() {
        test_type = LBTEST_LIST_ALL; // The default
        pp_strings = NULL;
        p_wl = NULL;
        p_buf = NULL;
    };
    ~LookBackTestObj() {
        if (test_type == LBTEST_LIST_KEYWORDS) {
            delete p_wl;
        } else if (test_type == LBTEST_LIST_STRINGS) {
            //XXX: This used to be scalar delete.
            // Does this fix crash bug 59067?
            delete[] p_buf;
            if (pp_strings)
                delete[] pp_strings;
        }
    };

    inline void SetActionStyle(int result_action_, int test_style_) {
        result_action = result_action_;
        test_style = test_style_;
    };
    inline int Action() {
        return result_action;
    };
    inline int Style() {
        return test_style;
    };
    inline int Type() {
        return test_type;
    };
    bool SetWordList(const char *s) {
        if (p_wl) {
            delete p_wl;
        }
        p_wl = new WordList;
        if (!p_wl)
            return false;
        p_wl->Set(s);
        test_type = LBTEST_LIST_KEYWORDS;
        return true;
    };
    bool InKeywords(const char *s) {
        return (p_wl && p_wl->InList(s));
    };
    bool SetStrings(const char *s) {
        // Here we copy the incoming string into a work-buffer,
        // and then build an array pointing to it as we zero-terminate
        // the pieces
        if (p_buf) {
            delete[] p_buf;
        }
        if (pp_strings) {
            delete[] pp_strings;
        }
        p_buf = new_strdup(s);
        if (!p_buf)
            return false;
        char *p_workBuf = p_buf;
        char *p_end = p_workBuf + strlen(p_buf);

        int numStrings = 0;
        bool inToken = false;
        
        // First figure out how big the array will be, and then
        // go back and create it.
        while (p_workBuf < p_end) {
            if (iswhitespace(*p_workBuf)) {
                inToken = false;
            } else if (!inToken) {
                inToken = true;
                numStrings += 1;
            }
            ++p_workBuf;
        }
        pp_strings = new char*[numStrings + 1];
        if (!pp_strings)
            return false;
        int n = 0; // current index
        inToken = false;
        for (p_workBuf = p_buf; p_workBuf < p_end; ++p_workBuf) {
            if (iswhitespace(*p_workBuf)) {
                if (inToken) {
                    // zero-terminate the previous string.
                    inToken = false;
                    *p_workBuf = 0;
                }
            } else if (!inToken) {
                inToken = true;
                assert(n < numStrings);
                pp_strings[n] = p_workBuf;
                ++n;
            }
        }
        assert(n == numStrings);
        pp_strings[n] = 0;
        test_type = LBTEST_LIST_STRINGS;
        return true;
    };
    char **Strings() {
        return pp_strings;
    };
};

// A sparse array of array of LookBackTestObj items or nulls
// Take the easy way out and allocate a [num styles] x 3 array,
// as the number of styles is always low, around 10 -- 10 * 3 * 4
// => 120 bytes per language

// Since C++ doesn't handle multi-dimensional arrays to easily,
// and I don't want to bring in vectors (or anything from STL,
// as scintilla doesn't use it), I'll do manual conversion.

class LookBackTests {
    private:
    int				  base_style;  // The default style for this sub-language
    int				  num_tests;
    LookBackTestObj	 **p_LBTests;  // Unmanaged array of LookBackTestObj objects
    int				  num_styles;
    int			     *p_defaults;

    public:
    LookBackTests() {
        base_style = num_styles = num_tests = 0;
        p_LBTests = NULL;
        p_defaults = NULL;
    };
    ~LookBackTests() {
        ClearTests();
        if (p_defaults) {
            delete[] p_defaults;
        }
    };

    bool Init(int base_style_, int num_styles_) {
        base_style = base_style_;
        num_styles = num_styles_;
        p_defaults = new int[num_styles];
        if (!p_defaults) {
            return false;
        }
        for (int i = 0; i < num_styles; i++) {
            p_defaults[i] = LBTEST_ACTION_REJECT;
        }
        return true;
    };

    void SetTestCount(int n) {
        ClearTests();
        num_tests = n;
        p_LBTests = new LookBackTestObj*[num_tests];
        if (!p_LBTests) {
            assert(0 && "Failed to allocate memory for the tests");
            return;
        }
        for (int i = 0; i < num_tests; i++) {
            p_LBTests[i] = new LookBackTestObj();
        }
    };
    int GetTestCount() {
        return num_tests;
    };
    void ClearTests() {
        if (p_LBTests) {
            for (int i = 0; i < num_tests; i++) {
                delete p_LBTests[i];
            }
            delete[] p_LBTests;
        }
    }

    // Policy: once a test is placed in this container,
    // the container is responsible for deleting it.
    
    void SetTest(int i, LookBackTestObj *p_Test) {
        if (i >= 0 && i < num_tests) {
            p_LBTests[i] = p_Test;
        } else {
            assert(0 && "SetTest -- bad index");
        }
    };
    LookBackTestObj * GetTest(int i) {
        if (i < 0 || i >= num_tests) {
            return NULL;
        }
        return p_LBTests[i];
    };

    int GetDefault(int style) {
        int actIndex = ActualIndex(style);
        assert(actIndex >= 0 && actIndex < num_styles * LBTEST_NUM_ACTIONS);
        return p_defaults[actIndex];
    };

    void SetDefault(int style, int defaultAction) {
        p_defaults[ActualIndex(style)] = defaultAction;
    };

    bool StyleInRange(int style) {
        return style >= base_style && style < (base_style + num_styles);
    };

    private:        
    inline int ActualIndex(int style) {
        return style - base_style;
    };
        
};

// Info for pushing and popping states, effectively turning
// our state machine into a pushdown automaton.  For now,
// only one type can be pushed and popped.

class StackItem {
    public:
    int state;
    StackItem *p_next;
    StackItem() : state(0), p_next(NULL) {
    };
    StackItem(int state_) : state(state_), p_next(NULL) {
    };
    StackItem(int state_, StackItem *p_si) : state(state_), p_next(p_si) {
    };
    ~StackItem() {
    };
};

class StateStack {
    private:
    StackItem *p_top;
    int        size;
    public:
    StateStack() : p_top(NULL), size(0) {
    };
    ~StateStack() {
        while (p_top) {
            (void) Pop();
        }
    };
    void Push(int state) {
        StackItem *p_tmp = new StackItem(state, p_top);
        p_top = p_tmp;
        size += 1;
    };
    int Pop() {
        if (!p_top) {
            return 0;
        }
        int i = p_top->state;
        StackItem *p_tmp = p_top;
        p_top = p_top->p_next;
        delete p_tmp;
        size -= 1;
        return i;
    };
    int Size() {
        return size;
    };
};

// A "flipper" is a (string, style, direction value) tuple that
// helps us determine the change in the line-level as we run
// through a line

class Flipper {
    private:
    char *s;
    int style;
    int direction;
    public:
    Flipper() {
        s = NULL;
        style = -1;
        direction = 0;
    };
    ~Flipper() {
        if (s) {
            delete[] s;
        }
    };
    bool Init(char *s_, int style_, int direction_) {
        if (direction_ == 0) return false;
        s = new_strdup(s_);
        if (!s) return false;
        style = style_;
        direction = direction_;
        return true;
    };
    int Match(char *s_, int style_) {
        if (style == style_ && !strcmp(s, s_)) {
            return direction;
        }
        return 0;
    };
};

// This class influences how we lex the code for the
// current family

class FamilyInfo {

    private:
    LookBackTests      *p_LookBackTests;
    WordList		   *keyword_list;  // Use scintilla's
    char			   *p_sub_language_name;
    int         		start_state;
    int					identifier_style;
    int					keyword_style;
    
    public:
    FamilyInfo() {
        keyword_list = NULL;
        p_LookBackTests = NULL;
        p_sub_language_name = NULL;
        start_state = identifier_style = keyword_style = -1;
    };
    ~FamilyInfo() {
        delete p_LookBackTests;
        delete keyword_list;
        delete[] p_sub_language_name;
    };

    void Init(int start_state_) {
        start_state = start_state_;
    }

    LookBackTests *CreateNewLookBackTests() {
        if (p_LookBackTests) {
            delete p_LookBackTests;
        }
        p_LookBackTests = new LookBackTests();
        return p_LookBackTests;
    };

    inline LookBackTests *GetLookBackTests() {
        return p_LookBackTests;
    };

    int DefaultStartState() {
        return start_state;
    }

    void SetWordList(const char *s) {
        if (keyword_list) {
            delete keyword_list;
        }
        keyword_list = new WordList;
        if (keyword_list)
            keyword_list->Set(s);
        // Fail quietly, as this is in the generated code.
    };
    WordList &GetWordList() {
        return *keyword_list;
    };

    void SetKeywordStyle(int identifier_style_, int keyword_style_) {
        identifier_style = identifier_style_;
        keyword_style = keyword_style_;
    };
    inline int GetIdentifierStyle() {
        return identifier_style;
    };
    inline int GetKeywordStyle() {
        return keyword_style;
    };

    inline void SetSublanguageName(char *p_Buf) {
        delete[] p_sub_language_name;
        p_sub_language_name = new_strdup(p_Buf);
    };
    inline char *GetSublanguageName() {
        return p_sub_language_name;
    };
};
       
class Transition {
    public: //XXX Make private
    int     search_type;        // instance of TRAN_SEARCH_*
    char   *p_search_string;    // new'ed pointer to a string
    pcre   *p_pattern;
    int     upto_color;         // if not -1, color upto starting pt this color
    int     include_color;      // if not -1, color upto current pt this color
    bool    do_redo;            // redo at this point
    bool    no_keyword;         // This transition does no keyword promotion
    int     new_state;          // -1: no new state
    int     new_family;          // -1: stay in same family
    int		token_check;		// 0: no check needed, !0: do a check
    int		push_pop_state;		// Used with the state-stack
    int     eol_target_state;     // Used with the at_eol directive.
    int		target_delimiter;
    bool	keep_current_delimiter;
    bool	clear_current_delimiter;

    class Transition *p_next;  // For the linked list

    public:
    Transition(int search_type_,
               char   *p_search_string_,
               int  upto_color_,
               int  include_color_,
               bool do_redo_,
               int      new_state_,
               int		token_check_,
               int		ignore_case_,
               bool no_keyword_
) :
            search_type(search_type_),
            upto_color(upto_color_),
            include_color(include_color_),
            do_redo(do_redo_),
            no_keyword(no_keyword_),
            new_state(new_state_),
            token_check(token_check_),
            push_pop_state(0),
            eol_target_state(0),
            target_delimiter(0),
            keep_current_delimiter(false),
            clear_current_delimiter(false),
            p_next(NULL) {
        new_family = -1;
        p_search_string = new_strdup(p_search_string_);
        if (search_type == TRAN_SEARCH_REGEX && p_search_string) {
            int options = PCRE_ANCHORED;
            if (ignore_case_) {
                options |= PCRE_CASELESS;
            }
            const char *errptr;
            int   erroffset;
            p_pattern = pcre_compile(p_search_string, options,
                                     &errptr, &erroffset, NULL);
            if (!p_pattern) {
                //XXX Remove
                fprintf(stderr, "udl: failed to compile ptn <%s>: failed at offset %d (%s): %s\n",
			p_search_string, erroffset, &p_search_string[erroffset],
                        errptr);
            }
        } else {
            p_pattern = NULL;
        }
    };
    
    ~Transition() {
        delete[] p_search_string;
        if (p_pattern) {
            LogEvent(true, "~Transition::pcre_free(p_pattern)", p_pattern);
            (*pcre_free)((void *) p_pattern);
            LogEvent(false, "... pcre_free(p_pattern)", p_pattern);
            p_pattern = NULL;
        }
    };
    Transition *Next() {
        return p_next;
    };
    inline void SetNewFamily(int new_family_) {
        new_family = new_family_;
    };
    inline void SetPushState(int state, int family) {
        push_pop_state = SF_MAKE_PAIR(state, family);
    };
    inline void SetPopState() {
        push_pop_state = -1;
    };
    inline void SetEolTransition(int state, int family) {
        eol_target_state = SF_MAKE_PAIR(state, family);
    };
    inline void SetDelimiter(int use_opposite, int group_num) {
        target_delimiter = SF_MAKE_PAIR(use_opposite, group_num);
    };
    inline void KeepDelimiter() {
        keep_current_delimiter = true;
    };
    inline void SetClearDelimiter() {
        clear_current_delimiter = true;
    };
};

// Each state for a template type has zero or more transitions

class TransitionInfo {
    public:
    TransitionInfo() {
        p_first = p_last = p_EOF = p_Empty = NULL;
    };
    ~TransitionInfo() {
        Transition *p_curr = p_first, *p_next;
        while (p_curr) {
            p_next = p_curr->p_next;
            delete p_curr;
            p_curr = p_next;
        }
        p_first = p_last = NULL;
        if (p_EOF) {
            delete p_EOF;
            p_EOF = NULL;
        }
        if (p_Empty) {
            delete p_Empty;
            p_Empty = NULL;
        }
    };
    void Append(Transition *p_node) {
        if (!p_last) {
            assert(!p_first);
            p_first = p_last = p_node;
        } else {
            p_last->p_next = p_node;
            p_last = p_node;
        }
    };
    void SetEOFInfo(Transition *p_node) {
        p_EOF = p_node;
    };
    Transition *GetEOFInfo() {
        return p_EOF;
    };
    void SetEmptyInfo(Transition *p_node) {
        p_Empty = p_node;
    };
    Transition *GetEmptyInfo() {
        return p_Empty;
    };
    

    Transition *First() {
        return p_first;
    };
    Transition *Next(Transition *p_curr) {
        return p_curr->p_next;
    };

    private:
    Transition *p_first, *p_last, *p_EOF, *p_Empty;
};

// Each template type has a set of types

class TransitionTable {
    private:
    TransitionInfo  *p_transitions;

    int count; // num transition info headers, one for each state, one for 0

    int         	 num_unique_states;
    int        		*p_unique_state_map;


    public:
    TransitionTable() {
        p_transitions = NULL;
        count = 0;
        num_unique_states = 0;
    };
    ~TransitionTable() {
        Clear();
    };
    
    void CreateNewTransitions(int count_) {
        Clear();
        count = count_;
        p_transitions = new TransitionInfo[count];
    };

    //XXX -- drop these
    void SetNumUniqueStates(int i) {
        num_unique_states = i;
        p_unique_state_map = new int[2 * i];
    };

    void SetUniqueState(int index, int style_num, int internal_state_num) {
        assert(index < num_unique_states);
        p_unique_state_map[2 * index] = style_num;
        p_unique_state_map[2 * index + 1] = internal_state_num;
    };

    int GetUniqueState(int style_num) {
        int num_unique_states_adj = num_unique_states * 2;
        for (int i = 0; i < num_unique_states_adj; i += 2) {
            if (p_unique_state_map[i] == style_num) {
                return p_unique_state_map[i + 1];
            }
        }
        return -1; // failure
    };

    inline int Count() {
        return count;
    };

    void Clear() {
        delete[] p_transitions;
        count = 0;
    };
    bool IsEmpty() {
        return count == 0;
    };

    TransitionInfo *Get(int i) {
        assert(i >= 0 && i < count);
        return &p_transitions[i];
    };

};

#define NUM_FAMILIES 5
#define NUM_VECTORS 30

// Global info

class MainInfo {
    private:
    TransitionTable   *p_TTable;
    FamilyInfo		   **pp_FamilyInfo;
    Flipper   		  **pp_Flippers; // for tracking levels
    StateStack		   *p_StateStack;
    int					flipper_count;

    int 				curr_family;
    char			   *p_language_name;

    int					familyColors[NUM_FAMILIES];
    int					familyOperators[NUM_FAMILIES];
    int					familyStyles[NUM_FAMILIES];

    bool					ready;

    public:
    char		   	   *p_raw_sublang_file; // Key for lookup
    MainInfo		   *p_Next; // Used by LexerInfoList only

    // Used semi-globally to transition when we hit the end-of-line
    // Once one is set, nothing can override it.
    
    int					curr_eol_transition;

    // Vars used for managing captured groups
    int					ovec_count;  // space to work with captured groups
    int					ovector[NUM_VECTORS];
    int					num_captured_groups;

    SString				current_delimiter; // Scintilla Simple String object

    public:
    MainInfo(char *p_raw_sublang_file_) {
        p_TTable = new TransitionTable();
        pp_FamilyInfo = new FamilyInfo*[NUM_FAMILIES];
        for (int i = 0; i < NUM_FAMILIES; i++) {
            pp_FamilyInfo[i] = new FamilyInfo;
        }
        pp_Flippers = NULL;
        p_language_name = NULL; // Not used?
        flipper_count = 0;
        p_StateStack = new StateStack;
        ready = false;
        p_raw_sublang_file = new_strdup(p_raw_sublang_file_);
        p_Next = NULL;
        ovec_count = NUM_VECTORS;
        curr_eol_transition = 0;
    };
    ~MainInfo() {
        Clear();
    };

    inline bool IsReady() { return ready; };

    void Clear() {
        delete p_TTable;
        delete[] p_language_name;
        p_TTable = 0;
        if (pp_FamilyInfo) {
            for (int i = 0; i < NUM_FAMILIES; i++) {
                pp_FamilyInfo[i] = new FamilyInfo;
            }
            delete[] pp_FamilyInfo;
            pp_FamilyInfo = 0;
        }
        if (pp_Flippers) {
            for (int i = 0; i < flipper_count; i++) {
                delete pp_Flippers[i];
            }
            delete[] pp_Flippers;
            pp_Flippers = 0;
        }
        delete p_StateStack;
        p_StateStack = 0;
        delete[] p_raw_sublang_file;
        p_raw_sublang_file = 0;
    };
    bool Init(const char *sublang=NULL);
    
    void SetCurrFamily(int curr_family_) {
        curr_family = curr_family_;
    };
    inline TransitionTable *GetTable() {
        return p_TTable;
    };
    int CurrFamilyIdx() {
        return curr_family;
    };
    FamilyInfo*	GetCurrFamily() {
        if (curr_family < 0 || curr_family >= NUM_FAMILIES) {
            assert(0 && "Bad family index");
            return NULL;
        }
        return pp_FamilyInfo[curr_family];
    };

    int StyleToFamily(int currStyle) {
        if (currStyle < SCE_UDL_CSS_DEFAULT) {
            return TRAN_FAMILY_MARKUP;
        } else if (currStyle < SCE_UDL_CSL_DEFAULT) {
            return TRAN_FAMILY_CSS;
        } else if (currStyle < SCE_UDL_SSL_DEFAULT) {
            return TRAN_FAMILY_CSL;
        } else if (currStyle < SCE_UDL_TPL_DEFAULT) {
            return TRAN_FAMILY_SSL;
        } else {
            return TRAN_FAMILY_TEMPLATE;
        }
    };

    int GetFamilyDefaultColor(int family) {
        if (family < 0 || family >= NUM_FAMILIES) {
            return -1;
        }
        return familyColors[family];
    };

    int GetFamilyDefaultStyle(int family) {
        if (family < 0 || family >= NUM_FAMILIES) {
            return -1;
        }
        return familyStyles[family];
    };

    void SetFlipperCount(int n) {
        flipper_count = n;
        pp_Flippers = new Flipper* [flipper_count];
        for (int i = 0; i < flipper_count; i++) {
            pp_Flippers[i] = new Flipper;
        }
    };

    bool SetFlipper(int i, char *s, int style, int direction) {
        if (i < 0 || i >= flipper_count) {
            return false;
        }
        pp_Flippers[i]->Init(s, style, direction);
        return true;
    };

    int GetFoldChange(char *s, int style, int& lengthUsed);

    bool IsOperator(int style) {
        for (int i = 0;
             i < (int) (sizeof(familyOperators)/sizeof(familyOperators[0]));
             i++) {
            if (familyOperators[i] == style)
                return true;
        }
        return false;
    }
    int NumTransitions() {
        return p_TTable->Count();
    };

    void PushState(int family_state) {
        p_StateStack->Push(family_state);
    };
    int PopState() {
        return p_StateStack->Pop();
    };
    int StateStackSize() {
        return p_StateStack->Size();
    };

    // Helpers and internal routines
    private:

    char *GetNextNumber(char *p_readBuf, int& code) {
        char *p_end;
        long int val = strtol(p_readBuf, &p_end, 10);
        code = (int) val;
        return p_end;
    };

    void GetNumsFromLine(char *p_readBuf, int args[], size_t n_args,
                         int *p_arg_count) {
        int i = 0, tmp;
        char *p_next;
        while (i < (int) n_args) {
            p_next = GetNextNumber(p_readBuf, tmp);
            if (p_next == p_readBuf) break;
            args[i++] = tmp;
            
            if (*p_next != ':') break;
            p_readBuf = p_next + 1;
        }
        *p_arg_count = i;
        for (;i < (int) n_args; i++) {
            args[i] = -9999;
        }
    };

    char *wrap_fgets(char *p_readBuf, int readBufSize, FILE *fp) {
        char *p_buf = fgets(p_readBuf, readBufSize, fp);
        if (!p_buf) return p_buf;
        int slen = (int) strlen(p_readBuf) - 1;
        if (p_readBuf[slen] == '\n') {
            p_readBuf[slen] = 0;
        } else if (!p_readBuf[slen]) {
            fprintf(stderr, "udl: don't get it, p_readBuf[%d] = %d\n",
		    slen, p_readBuf[slen]);
        }
        return p_buf;
    };

    bool verifyArgs(int args[], int arg_count, int num_needed, const char *sig) {
        if (num_needed != arg_count) {
            fprintf(stderr, "udl: verifyArgs: expecting %d args for the current opcode, got %d\n",
		    num_needed, arg_count);
            return false;
        }
        int *p_args = args;
        const char *p_sig = sig;
        int i = 0;
        int mult = 0;// msvc warning 4701
        int targ = 0;
        for (i = 0; i < arg_count; i++, p_sig++, p_args++) {
            if (!*p_sig) {
                fprintf(stderr, "udl: verifyArgs: ran out of sig chars at item %d\n", i);
                return false;
            }
            switch (*p_sig) {
            case 'd': mult = 0; targ = 0; break;  // any integer
            case 'p': mult = 1; targ = 1; break; // > 0
            case 'P': mult = 1; targ = 0; break; // >= 0
            case 'n': mult = -1; targ = 1; break; // < 0
            case 'N': mult = -1; targ = 0; break; // <= 0
            }
            if (mult * *p_args < targ) {
                fprintf(stderr, "udl: expecting arg %d to be of type %c, got %d\n",
			i, *p_sig, *p_args);
                return false;
            }
        }
        return true;
    };

    bool processingOlderFormat(int *writer_version) {
        if (writer_version[0] < READER_VERSION_MAJOR) return true;
        else if (writer_version[0] > READER_VERSION_MAJOR) return false;
        else if (writer_version[1] < READER_VERSION_MINOR) return true;
        // changes in subminor version are ignored.
        else return false;
    };

    bool processingNewerFormat(int *writer_version) {
        if (writer_version[0] > READER_VERSION_MAJOR) return true;
        else if (writer_version[0] < READER_VERSION_MAJOR) return false;
        else if (writer_version[1] > READER_VERSION_MINOR) return true;
        // changes in subminor version are ignored.
        else return false;
    };
};

#if _WIN32
#pragma warning( disable : 4127)
#endif

#define null_check(constx, var) \
do { \
  if (!var) { \
    fprintf(stderr, "udl: error: " #constx " at line %d: " #var " is null\n", __LINE__); \
    goto free_stuff; \
  } \
} while (0)

bool MainInfo::Init(const char *p_sublang_file) {
    // This variant finds and reads in a lexer resource.
    // Resource files have form of path/<sublang-name>.lexres


    // Variables we'll need for reading:
    int scratchBufSize = 255;
    char *p_scratchBuf = NULL;
    int numScratchCharsWritten = 0;

    int readBufSize = 255;
    char *p_readBuf = NULL;

    TransitionTable *p_TransitionTable;
    TransitionInfo *p_TranBlock = NULL;
    Transition *p_Tran = NULL;
    FamilyInfo *p_FamilyInfo = NULL;
    LookBackTests *p_LBTests = NULL;
    LookBackTestObj *p_LBTestObj = NULL;
    int				versionInfo[3];
    int bytecode;
    int args[10];
    int arg_count;
    int writer_version[3] = {1, 0, 0};
    int lineNo = 1;
    char *p_lang = NULL;
    FILE *fp = NULL;
    bool rc = false;

    // Don't define any other vars for this routine below
    // this point due to the goto to the free_stuff thing.

    fp = fopen(p_sublang_file, "r");
    if (!fp) {
        fprintf(stderr, "udl: can't open file %s (who knows why)\n",
		p_sublang_file);
        goto free_stuff;
    }
    p_TransitionTable = GetTable();
    if (!p_TransitionTable) {
        fprintf(stderr, "udl: no transition table\n");
        goto free_stuff;
    }
    p_scratchBuf = (char *) malloc(scratchBufSize + 1);
    if (!p_scratchBuf) {
        fprintf(stderr, "udl: no memory for p_scratchBuf\n");
        goto free_stuff;
    }
    p_readBuf = (char *) malloc(readBufSize + 1);
    if (!p_readBuf) {
        fprintf(stderr, "udl: no memory for p_readBuf\n");
        goto free_stuff;
    }
    

    for (;wrap_fgets(p_readBuf, readBufSize, fp); ++lineNo) {
        if ((int) strlen(p_readBuf) >= readBufSize - 2) {
            fprintf(stderr, "udl: internal error: line %d too big\n", lineNo);
            goto free_stuff;
        }
        if (*p_readBuf == '#') {
            // #-delimited comments ok
            continue;
        }
        char *p_rest = GetNextNumber(p_readBuf, bytecode); // pass by ref
        // Big switch stmt, better to make this a dispatcher
        if (bytecode <= 0) {
            fprintf(stderr, "udl: error: bad bytecode %d\n", bytecode);
            goto free_stuff;
        }
        if (*p_rest == ':') p_rest++;
        switch((int) bytecode) {
        case ASTC_META_COMMENTS:
        case ASTC_SCRATCH_BUFFER_APPEND:
        case ASTC_LANGUAGE_NAME:
        case ASTC_SUBLANGUAGE_NAME:
            arg_count = 0; // Not used, squelch msvc warning 4701
            break;
        default:
            GetNumsFromLine(p_rest, args, sizeof(args)/sizeof(args[0]),
                            &arg_count);
        }
        
        switch((int) bytecode) {
        case ASTC_META_COMMENTS:
            // fprintf(stderr, "udl: comment: %s\n", p_readBuf);
            break;
        case ASTC_META_VERSION_MAJOR:
        case ASTC_META_VERSION_MINOR:
        case ASTC_META_VERSION_SUBMINOR:
            if (!verifyArgs(args, arg_count, 1, "P"))
                goto free_stuff;
            versionInfo[bytecode - ASTC_META_VERSION_MAJOR] = args[0];
            break;
        case ASTC_SCRATCH_BUFFER_START:
            if (!verifyArgs(args, arg_count, 1, "p"))
                goto free_stuff;
            if (scratchBufSize < args[0]) {
                scratchBufSize = args[0];
                char *p_hold = (char *) realloc(p_scratchBuf, scratchBufSize + 1);
                if (!p_hold) {
                    fprintf(stderr, "udl: MainInfo::Init: can't realloc scratch-buf\n");
                    goto free_stuff;
                }
                p_scratchBuf = p_hold;
            }
            numScratchCharsWritten = 0;
            p_scratchBuf[0] = 0;
            break;
            
        case ASTC_SCRATCH_BUFFER_APPEND:
            {
                int numCharsToAdd = (int) strlen(p_rest);
                if (numScratchCharsWritten + numCharsToAdd > scratchBufSize) {
                    fprintf(stderr, 
                            "udl: internal error: can't hold %d chars in a buf containing %d chars\n",
                            numScratchCharsWritten + numCharsToAdd,
                            scratchBufSize);
                    goto free_stuff;
                }
                strncpy(&p_scratchBuf[numScratchCharsWritten], p_rest,
                        numCharsToAdd);
                numScratchCharsWritten += numCharsToAdd;
                p_scratchBuf[numScratchCharsWritten] = 0;
            }
            break;

        case ASTC_LANGUAGE_NAME:
            if (!p_scratchBuf[0]) {
                fprintf(stderr, "udl: language-name: p_scratchBuf is empty\n");
                goto free_stuff;
            }
            delete[] p_language_name;
            p_language_name = new_strdup(p_scratchBuf);
            break;

        case ASTC_SUBLANGUAGE_NAME:
            if (!p_scratchBuf[0]) {
                fprintf(stderr, "udl: sub-language-name: p_scratchBuf is empty\n");
                goto free_stuff;
            }
            null_check(ASTC_SUBLANGUAGE_NAME, p_FamilyInfo);
            p_FamilyInfo->SetSublanguageName(p_scratchBuf);
            break;

        case ASTC_F_COLOR:
            if (!verifyArgs(args, arg_count, 2, "PP"))
                goto free_stuff;
            familyColors[args[0]] = args[1];
            break;

        case ASTC_F_STYLE:
            if (!verifyArgs(args, arg_count, 2, "PP"))
                goto free_stuff;
            familyStyles[args[0]] = args[1];
            break;

        case ASTC_F_OPERATOR:
            if (!verifyArgs(args, arg_count, 2, "Pp"))
                goto free_stuff;
            familyOperators[args[0]] = args[1];
            break;
            
        case ASTC_FLIPPER_COUNT:
            if (!verifyArgs(args, arg_count, 1, "P"))
                goto free_stuff;
            SetFlipperCount(args[0]);
            break;

        case ASTC_CURRENT_FAMILY:
            if (!verifyArgs(args, arg_count, 1, "P"))
                goto free_stuff;
            SetCurrFamily(args[0]);
            p_FamilyInfo = GetCurrFamily();
            p_LBTests = NULL;
            p_LBTestObj = NULL;
            null_check(ASTC_CURRENT_FAMILY, p_FamilyInfo);
            break;

        case ASTC_F_DEFAULT_STATE:
            if (!verifyArgs(args, arg_count, 1, "P"))
                goto free_stuff;
            null_check(ASTC_F_DEFAULT_STATE, p_FamilyInfo);
            p_FamilyInfo->Init(args[0]);
            break;

        case ASTC_F_FLIPPER:
            if (!verifyArgs(args, arg_count, 3, "PPd")) // non-neg twice, any
                goto free_stuff;
            if (!p_scratchBuf[0]) {
                fprintf(stderr, "udl: set-flipper: p_scratchBuf is empty\n");
                goto free_stuff;
            }
            // scratch-buf copied here
            SetFlipper(args[0], p_scratchBuf, args[1], args[2]);
            break;

        case ASTC_F_WORDLIST:
            if (!p_scratchBuf[0]) {
                fprintf(stderr, "udl: set-wordlist: p_scratchBuf is empty\n");
                goto free_stuff;
            }
            null_check(ASTC_F_WORDLIST, p_FamilyInfo);
            // scratch-buf copied by the word-list thing
            p_FamilyInfo->SetWordList(p_scratchBuf);
            break;

        case ASTC_F_KEYWORD_STYLE:
            if (!verifyArgs(args, arg_count, 2, "PP"))
                goto free_stuff;
            null_check(ASTC_F_KEYWORD_STYLE, p_FamilyInfo);
            p_FamilyInfo->SetKeywordStyle(args[0], args[1]);
            break;

        case ASTC_F_LOOKBACK_TESTS_CREATE:
            if (!verifyArgs(args, arg_count, 0, ""))
                goto free_stuff;
            null_check(ASTC_F_LOOKBACK_TESTS_CREATE, p_FamilyInfo);
            p_LBTests = p_FamilyInfo->CreateNewLookBackTests();
            p_LBTestObj = NULL;
            if (!p_LBTests) {
                fprintf(stderr, "udl: ASTC_F_LOOKBACK_TESTS_CREATE: failed to create p_LBTests\n");
                goto free_stuff;
            }
            break;

        case ASTC_F_LOOKBACK_TESTS_INIT:
            if (!verifyArgs(args, arg_count, 2, "Pp"))
                goto free_stuff;
            null_check(ASTC_F_LOOKBACK_TESTS_INIT, p_LBTests);
            p_LBTests->Init(args[0], args[1]);
            break;
            
        case ASTC_F_LOOKBACK_TESTS_COUNT:
            if (!verifyArgs(args, arg_count, 1, "P"))
                goto free_stuff;
            null_check(ASTC_F_LOOKBACK_TESTS_COUNT, p_LBTests);
            p_LBTests->SetTestCount(args[0]);
            break;
            
        case ASTC_LBT_GET:
            if (!verifyArgs(args, arg_count, 1, "P")) // can have test 0
                goto free_stuff;
            null_check(ASTC_LBT_GET, p_LBTests);
            p_LBTestObj = p_LBTests->GetTest(args[0]);
            if (!p_LBTestObj) {
                fprintf(stderr, "udl: ASTC_LBT_GET: failed to get p_LBTestObj\n");
                goto free_stuff;
            }
            break;
            
        case ASTC_LBT_ACTION_STYLE:
            if (!verifyArgs(args, arg_count, 2, "PP"))
                goto free_stuff;
            null_check(ASTC_LBT_ACTION_STYLE, p_LBTestObj);
            p_LBTestObj->SetActionStyle(args[0], args[1]);
            break;
            
        case ASTC_LBT_STRINGS:
            if (!verifyArgs(args, arg_count, 0, ""))
                goto free_stuff;
            null_check(ASTC_LBT_STRINGS, p_LBTestObj);
            // scratch-buf copied by SetStrings
            p_LBTestObj->SetStrings(p_scratchBuf);
            break;
            
        case ASTC_LBT_WORDLIST:
            if (!verifyArgs(args, arg_count, 0, ""))
                goto free_stuff;
            null_check(ASTC_LBT_WORDLIST, p_LBTestObj);
            if (!p_scratchBuf[0]) {
                fprintf(stderr, "udl: ASTC_LBT_WORDLIST: p_scratchBuf is empty\n");
                goto free_stuff;
            }
            // scratch-buf copied by the word-list thing
            p_LBTestObj->SetWordList(p_scratchBuf); // no need to copy
            break;

        case ASTC_LBT_DEFAULT:
            if (!verifyArgs(args, arg_count, 2, "PP"))
                goto free_stuff;
            null_check(ASTC_LBT_DEFAULT, p_LBTests);
            p_LBTests->SetDefault(args[0], args[1]);
            break;

        case ASTC_LBT_TEST:
            if (!verifyArgs(args, arg_count, 1, "P"))
                goto free_stuff;
            null_check(ASTC_LBT_TEST, p_LBTestObj);
            null_check(ASTC_LBT_TEST, p_LBTests);
            p_LBTests->SetTest(args[0], p_LBTestObj);
            break;

        case ASTC_TTABLE_NUM_UNIQUE_STATES:
            if (!verifyArgs(args, arg_count, 1, "P"))
                goto free_stuff;
            null_check(ASTC_TTABLE_NUM_UNIQUE_STATES, p_TransitionTable);
            p_TransitionTable->SetNumUniqueStates(args[0]);
            break;

        case ASTC_TTABLE_UNIQUE_STATE:
            if (!verifyArgs(args, arg_count, 3, "PPp"))
                goto free_stuff;
            null_check(ASTC_TTABLE_UNIQUE_STATE, p_TransitionTable);
            p_TransitionTable->SetUniqueState(args[0], args[1], args[2]);
            break;

        case ASTC_TTABLE_CREATE_TRANS:
            if (!verifyArgs(args, arg_count, 1, "P"))
                goto free_stuff;
            null_check(ASTC_TTABLE_CREATE_TRANS, p_TransitionTable);
            p_TransitionTable->CreateNewTransitions(args[0]);
            break;

        case ASTC_TTABLE_GET_TBLOCK:
            if (!verifyArgs(args, arg_count, 1, "P"))
                goto free_stuff;
            null_check(ASTC_TTABLE_GET_TBLOCK, p_TransitionTable);
            p_TranBlock = p_TransitionTable->Get(args[0]);
            p_Tran = NULL;
            if (!p_TranBlock) {
                fprintf(stderr, "udl: ASTC_TTABLE_GET_TBLOCK: failed to get p_TranBlock");
                goto free_stuff;
            }
            break;

            // This went from 7 args to 8 post version 4.0 alpha 5
        case ASTC_CREATE_NEW_TRAN:
        {
            bool no_keyword;
            if (arg_count == 7) {
                if (!verifyArgs(args, arg_count, 7, "PddPdPP"))
                    goto free_stuff;
                no_keyword = false;
            } else {
                if (!verifyArgs(args, arg_count, 8, "PddPdPPP"))
                    goto free_stuff;
                no_keyword = args[7] == 0 ? false : true;
            }
            // scratch-buf copied by the Transition ctor
            p_Tran = new Transition(args[0],   // TRAN_regex|string|empty|eof
                                    p_scratchBuf,
                                    args[1],	// upto-color|-1
                                    args[2],	// inc-color|-1
                                    args[3] == 1 ? true : false,	// redo?
                                    args[4],	// => state | -1 (don't)
                                    args[5],	// token-check? 0 | 1
                                    args[6],	// ignore-case? 0 | 1
                                    no_keyword 	// no_keyword? 0 | 1
                                    );
            if (!p_Tran) {
                fprintf(stderr, "udl: ASTC_CREATE_NEW_TRAN: failed to get p_Tran");
                goto free_stuff;
            }
        }
        break;

        case ASTC_TRAN_SET_F:
            if (!verifyArgs(args, arg_count, 1, "P"))
                goto free_stuff;
            null_check(ASTC_TRAN_SET_F, p_Tran);
            p_Tran->SetNewFamily(args[0]);
            break;

        case ASTC_TRAN_PUSH_STATE:
            if (!verifyArgs(args, arg_count, 2, "pP"))
                goto free_stuff;
            null_check(ASTC_TRAN_PUSH_STATE, p_Tran);
            p_Tran->SetPushState(args[0], args[1]);
            break;

        case ASTC_TRAN_POP_STATE:
            if (!verifyArgs(args, arg_count, 0, ""))
                goto free_stuff;
            null_check(ASTC_TRAN_POP_STATE, p_Tran);
            p_Tran->SetPopState();
            break;

        case ASTC_TBLOCK_APPEND_TRAN:
            if (!verifyArgs(args, arg_count, 0, ""))
                goto free_stuff;
            null_check(ASTC_TBLOCK_APPEND_TRAN, p_Tran);
            p_TranBlock->Append(p_Tran);
            break;

        case ASTC_TBLOCK_EOF_TRAN:
            if (!verifyArgs(args, arg_count, 0, ""))
                goto free_stuff;
            null_check(ASTC_TBLOCK_EOF_TRAN, p_Tran);
            p_TranBlock->SetEOFInfo(p_Tran);
            break;

        case ASTC_TBLOCK_EMPTY_TRAN:
            if (!verifyArgs(args, arg_count, 0, ""))
                goto free_stuff;
            null_check(ASTC_TBLOCK_EMPTY_TRAN, p_Tran);
            p_TranBlock->SetEmptyInfo(p_Tran);
            break;

        case ASTC_TRAN_EOL_STATE:
            if (!verifyArgs(args, arg_count, 2, "pP"))
                goto free_stuff;
            null_check(ASTC_TRAN_EOL_STATE, p_Tran);
            p_Tran->SetEolTransition(args[0], args[1]);
            break;

        case ASTC_TRAN_SET_DELIMITER:
            if (!verifyArgs(args, arg_count, 2, "Pp"))
                goto free_stuff;
            null_check(ASTC_TRAN_SET_DELIMITER, p_Tran);
            p_Tran->SetDelimiter(args[0], args[1]);
            break;

        case ASTC_TRAN_KEEP_DELIMITER:
            if (!verifyArgs(args, arg_count, 0, ""))
                goto free_stuff;
            null_check(ASTC_TRAN_KEEP_DELIMITER, p_Tran);
            p_Tran->KeepDelimiter();
            break;

        case ASTC_TRAN_CLEAR_DELIMITER:
            if (!verifyArgs(args, arg_count, 0, ""))
                goto free_stuff;
            null_check(ASTC_TRAN_KEEP_DELIMITER, p_Tran);
            p_Tran->SetClearDelimiter();
            break;

        case ASTC_TRAN_WRITER_VERSION:
            if (!verifyArgs(args, arg_count, 3, "PPP"))
                goto free_stuff;
            memcpy((void *) writer_version, (void *) args,
                   (size_t) sizeof(writer_version));
            break;
            
        default:
            // If we're processing this version's format, or an older
            // one, complain and stop.  Otherwise quietly ignore
            // bytecodes from the future.
            if (!processingNewerFormat(writer_version)) {
                fprintf(stderr, "udl: found unknown op %d\n", bytecode);
                goto free_stuff;
            } else {
                fprintf(stderr, "udl: reader/writer mismatch: reader (Komodo) is built for lexres version %d.%d,\ngiven file is version %d.%d -- ignoring op %d\n",
                        READER_VERSION_MAJOR,
                        READER_VERSION_MINOR,
                        writer_version[0],
                        writer_version[1],
                        bytecode);
            }
            break;
        }
    }
    rc = true;

    // Jump to here and continue;
    free_stuff:
    if (!rc) {
        fprintf(stderr, "udl: bailing out of file '%s' at line %d\n",
		p_sublang_file, lineNo);
        Clear();
    } else {
        ready = true;
    }
    if (p_lang) free(p_lang);
    if (p_scratchBuf)  free(p_scratchBuf);
    if (p_readBuf) free(p_readBuf);
    if (fp) fclose(fp);             
    return rc;
}

#if _WIN32
#pragma warning( default : 4127)
#endif

int MainInfo::GetFoldChange(char *s, int style, int& lengthUsed) {
    int direction;
    int slen = (int) strlen(s);
        
    if (IsOperator(style)) {
        // For operators, try every single prefix
        // Try to match the longest string first.
        for (int j = slen; j > 0; j--) {
            char ch = s[j];
            s[j] = 0;
            for (int i = 0; i < flipper_count; i++) {
                direction = pp_Flippers[i]->Match(s, style);
                if (direction) {
                    lengthUsed = j;
                    s[j] = ch;
                    return direction;
                }
            }
            s[j] = ch;
        }
        lengthUsed = 1;
    } else {
        lengthUsed = slen;
        for (int i = 0; i < flipper_count; i++) {
            direction = pp_Flippers[i]->Match(s, style);
            if (direction) {
                return direction;
            }
        }
    }
    return 0;
}

// A list of MainInfo's    

class LexerInfoList {
    private:
    MainInfo *p_Head;
    
    public:
    LexerInfoList() {
        p_Head = NULL;
    };
    ~LexerInfoList() {
        if (p_Head) {
#if 0
            fprintf(stderr, "udl: destructing LexerInfoList\n");
#endif
            MainInfo *p_CurrNode = p_Head;
            MainInfo *p_NextNode;
            while (p_CurrNode) {
                p_NextNode = p_CurrNode->p_Next;
                delete p_CurrNode;
                p_CurrNode = p_NextNode;
            };
            p_Head = NULL;
        }
    };

    MainInfo *Intern(char *p_rawSubLanguage) {
        MainInfo *p_MI = Lookup(p_rawSubLanguage);
        if (!p_MI) {
            p_MI = new MainInfo(p_rawSubLanguage);
            if (!p_MI) {
                fprintf(stderr, "udl: ColouriseTemplate1Doc: couldn't create a MainInfo\n");
                return NULL;
            }
            char *p_finalFileName;
            bool free_subLanguage = false;
            if (!unescapeFileName(p_rawSubLanguage, &p_finalFileName,
                                  &free_subLanguage)) {
                return NULL;
            }
#if 0
            fprintf(stderr, "udl: ColouriseTemplate1Doc: loading sublanguage %s, \n",
                    p_finalFileName);
#endif
            p_MI->Init(p_finalFileName);
            if (free_subLanguage) {
                delete[] p_finalFileName;
            }
            p_MI->p_Next = p_Head;
            p_Head = p_MI;
        }
        return p_MI;
    };
    
    private:
    
    MainInfo *Lookup(char *p_rawSubLanguage) {
        MainInfo *p_CurrNode = p_Head;
        while (p_CurrNode) {
            if (p_CurrNode->p_raw_sublang_file
                && !strcmp(p_rawSubLanguage, p_CurrNode->p_raw_sublang_file)) {
                return p_CurrNode;
            }
            p_CurrNode = p_CurrNode->p_Next;
        }
        return p_CurrNode;
    };

    bool unescapeFileName(char	   *p_rawSubLanguage,
                          char	  **pp_finalFileName,
                          bool	   *p_free_subLanguage) {
#if 0
        fprintf (stderr, "strchr(p_subLanguage, '%%') => %s\n",
                 strchr(p_rawSubLanguage, '%') ? "yes" : "no");
#endif
        if (strchr(p_rawSubLanguage, '%')) {
#if 0
            fprintf(stderr, "udl: ColouriseTemplate1Doc: need to url-unescape %s, \n",
                    p_rawSubLanguage);
#endif
            // Write it in place, as we know there's enough memory.
            char *p_new_lang_buf = new_strdup(p_rawSubLanguage);
            if (!p_new_lang_buf) {
                fprintf(stderr, "udl: ColouriseTemplate1Doc: out of memory\n");
                return false;
            }
            char *p_new_lang = p_new_lang_buf;
            const char *p_old_lang = p_rawSubLanguage;
            const char *p_end_old_lang = p_rawSubLanguage + strlen(p_rawSubLanguage);
            char conversion_buf[5];
            conversion_buf[0] = '0';
            conversion_buf[1] = 'x';
            conversion_buf[4] = 0;
            while (p_old_lang < p_end_old_lang) {
                if (*p_old_lang == '%') {
                    if (p_end_old_lang - p_old_lang < 3) {
                        break;
                    }
                    conversion_buf[2] = *(p_old_lang + 1);
                    conversion_buf[3] = *(p_old_lang + 2);
                    int val = strtol(conversion_buf, NULL, 16);
                    if (val) {
                        *p_new_lang++ = (char) val;
                        p_old_lang += 3;
                    } else {
                        // If we can't convert, leave it as a '%' char.
                        *p_new_lang++ = *p_old_lang++;
                    }
                } else {
                    *p_new_lang++ = *p_old_lang++;
                }
            }
            *p_new_lang = 0;
#if 0
            fprintf(stderr, "udl: ColouriseTemplate1Doc: converted %s to %s, \n",
                    p_rawSubLanguage, p_new_lang_buf);
#endif
            *pp_finalFileName = p_new_lang_buf;
            *p_free_subLanguage = true;
        } else {
            *pp_finalFileName = p_rawSubLanguage;
            *p_free_subLanguage = false;
        }
        return true;
    };
};


// ****************************************************************
// **************** End UDL_Tables.h classes ****************
// ****************************************************************


// This class is used by the enter and exit methods, so it needs
// to be hoisted out of the function.

class QuoteCls {
    public:
    int  Count;
    char Up;
    char Down;
    QuoteCls() {
        this->New();
    }
    void New() {
        Count = 0;
        Up    = '\0';
        Down  = '\0';
    }
    void Open(char u) {
        Count++;
        Up    = u;
        Down  = opposite(Up);
    }
    QuoteCls(const QuoteCls& q) {
        // copy constructor -- use this for copying in
        Count = q.Count;
        Up    = q.Up;
        Down  = q.Down;
    }
    QuoteCls& operator=(const QuoteCls& q) { // assignment constructor
        if (this != &q) {
            Count = q.Count;
            Up    = q.Up;
            Down  = q.Down;
        }
        return *this;
    }
            
};

class LexString {
    private:
    char *p_buf;
    unsigned int buf_size;
    int			curr_line;

    public:
    LexString() {
        p_buf = NULL;
        buf_size = 0;
        curr_line = -1;
    };
    ~LexString() {
        if (p_buf) {
            delete[] p_buf;
        }
    };
    int CurrLine() {
        return curr_line;
    };
    char *Val() {
        return p_buf;
    };

    bool SetLine(int pos, Accessor &styler) {
        curr_line = styler.GetLine(pos);
        int line_length = CurrLineLength(pos, styler);
        if (!MakeSpace(line_length + 1)) {
            curr_line = -1;
            return false;
        }
        char *p_s = p_buf;
        int line_start = styler.LineStart(curr_line);
        int line_end = line_start + line_length;
        for (int i = line_start; i < line_end; i++) {
            *p_s++ = styler.SafeGetCharAt(i);
        }
        *p_s = 0;
        return true;        
    };
    bool Init() {
        buf_size = 256;
        p_buf = new char[buf_size];
        if (!p_buf) {
            buf_size = 0;
            return false;
        }
        return true;
    };
    private:
    int CurrLineLength(int pos, Accessor &styler)
    {
        int docLength;
        if (pos < 0 || pos >= (docLength = styler.Length())) {
            return -1;
        }
        int currLine = styler.GetLine(pos);
        int lineStart = styler.LineStart(currLine);
        int nextLineStart = styler.LineStart(currLine + 1);
        if (nextLineStart >= docLength) {
            return docLength - lineStart + 1;
        }
        return nextLineStart - lineStart;
    };
    bool MakeSpace(unsigned int needed_len) {
        if (buf_size < needed_len) {
            unsigned int curr_buf_size = buf_size;
            while (curr_buf_size < needed_len) {
                curr_buf_size *= 2;
            }
            if (!p_buf) {
                assert(0 && "In LexString::Set, p_buf is null");
            } else {
                delete[] p_buf;
            }
            p_buf = new char[curr_buf_size];
            if (!p_buf) {
                buf_size = 0;
                return false;
            }
            buf_size = curr_buf_size;
        }
        return true;
    };

};

static LexerInfoList LexerList;    

// For table-driven lexers, we move back until we find a style
// that maps to exactly one internal style.  Otherwise we move
// to char 0, and use this table's initial style.

// Move back looking for the first style 
// Only look at the start of each line, because we need to 
// count fold-changing constructs in each line as well.

// Requirements:
// 1. The color style at the start of the line must map
//    to a unique internal style
// 2. The color style on the line preceding it must be default,
//    ruling out multi-line styles.

// This is a conservative approach, forcing the lexer back to 
// well-understood points.  Hopefully not to the beginning of
// the buffer too often.

// We set the initStyle to the default style for the current family.

#if 0
// Semi-useful helper, but can only be called once per sprintf
static char* line_colon_col(int pos, Accessor &styler) {
    static char buf[30];
    int line = styler.GetLine(pos);
    sprintf(buf, "%d:%d", line + 1, pos - styler.LineStart(line));
    return buf;
}
#endif

// Macros for manipulating the line-state

#define LEXER_STATE_MASK	0xfff
#define DELIMITER_MASK		0xfff
#define PUSH_STATE_MASK		0x7f

#define eol_state_from_line_state(state) ((state) & LEXER_STATE_MASK)
#define delimiter_hash_from_line_state(state) ((state >> 12) & DELIMITER_MASK)
#define push_stack_size_from_line_state(state) ((state >> 24) & PUSH_STATE_MASK)

static int create_line_state(int push_stack_size,
                             int state) {
    if (state > LEXER_STATE_MASK) {
        // Fake a reason not to accept this state.
        state = LEXER_STATE_MASK;
        push_stack_size += 1;
    }
    if (push_stack_size > PUSH_STATE_MASK) {
        push_stack_size = PUSH_STATE_MASK;
    }
    // Delimiter hashes are added in update_line_state_from_delim
    return ((push_stack_size << 24) | state);
}

#define update_line_state_from_delim(line_state, delimiter_hash) \
    ((line_state) | (((delimiter_hash) & DELIMITER_MASK) << 12))

static void synchronizeDocStart(unsigned int& startPos,
                                int &length,
                                int &initState, // out only
                                int &currFamily,
                                Accessor &styler,
                                MainInfo		   *p_MainInfo
                                )
{
    int startLine;
    int newPos = startPos;
    int lineEndPos;
    // Avoid moving back to the beginning when in a nested state
    int nested_lines_to_skip = 24;
    if (newPos > 0) {
        // Start at the line previous to the line the lexer's invoked at.
        startLine = styler.GetLine(newPos);
        // if startLine == 0, lineEndPos ends up at -1, but it's
        // never consulted in this case, so it's ok
        lineEndPos = styler.LineStart(startLine) - 1;
        startLine -= 1;
        newPos = styler.LineStart(startLine);
    } else {
        lineEndPos = 0; // Not used, squelch an OS X compiler warning
        startLine = -1;
    }
    if (startLine > 0) {
        styler.Flush();
        for(;;) {

            // Move up the buffer looking for a line we can stop at,
            // and restore the internal lexer state

            int currStyle;
            currStyle = actual_style(styler.StyleAt(newPos));
            currFamily = p_MainInfo->StyleToFamily(currStyle);
            int familyDefaultStyle = p_MainInfo->GetFamilyDefaultColor(currFamily);
            int prevLineEndStyle = actual_style(styler.StyleAt(lineEndPos));
            if (prevLineEndStyle == familyDefaultStyle) {
                int prevLineState = styler.GetLineState(startLine - 1);
                if (delimiter_hash_from_line_state(prevLineState)) {
#if 0
                    fprintf(stderr, "Rejecting line %d because of delim.\n",
                            startLine - 1);
#endif
                } else if (--nested_lines_to_skip >= 0
                           && push_stack_size_from_line_state(prevLineState)) {
#if 0
                    if (nested_lines_to_skip == 23
                        || nested_lines_to_skip == 0) {
                        fprintf(stderr, "Rejecting line %d because it's in a push-state.\n",
                                startLine - 1);
                    }
#endif
                } else {
#if 0
                    fprintf(stderr, "udl: QQQ: synchronizeDocStart: stopping at line %d => %d, pos %d => %d, docLength %d, family %d, color %d\n",
                            styler.GetLine(startPos),
                            startLine, startPos, newPos, length + (startPos - newPos),
                            currFamily,
                            familyDefaultStyle);
#endif
                    p_MainInfo->SetCurrFamily(currFamily);
                    initState = eol_state_from_line_state(prevLineState);
                    length += (startPos - newPos);
                    startPos = newPos;
                    return;
                }
            } else {
#if 0
                fprintf(stderr, " rejecting line %d -- prev line ends with style %d\n",
                        startLine, prevLineEndStyle);
#endif
            }
            if (--startLine <= 0) {
                break;
            }
            lineEndPos = newPos - 1;
            newPos = styler.LineStart(startLine);
        }
    }
    length += startPos;
    startPos = 0;
    // By default, start in the markup family
    currFamily = TRAN_FAMILY_MARKUP;
    p_MainInfo->SetCurrFamily(currFamily);
    initState = p_MainInfo->GetCurrFamily()->DefaultStartState();
}

static void doColorAction(int	    styleNum,
                          bool		no_keyword,
                          int		pos,
                          FamilyInfo	*p_FamilyInfo,
                          Accessor &styler
                          )
{
    if (styleNum >= 0) {
        // Look to see if we should color this as a keyword instead
        if (!no_keyword && styleNum == p_FamilyInfo->GetIdentifierStyle()) {
            char s[100];
            GetCurrent(s, sizeof(s), pos - 1, styler);
            if (s[0]) {
                WordList &keywords = p_FamilyInfo->GetWordList();
                if (keywords.InList(s)) {
                    int newStyleNum = p_FamilyInfo->GetKeywordStyle();
                    if (newStyleNum >= 0) {
                        styleNum = newStyleNum;
                    }
                }
            }
        }
        styler.ColourTo(pos - 1, styleNum);
    }
}

static void doActions(Transition     *p_TranBlock,
                      int      &oldPos,
                      int      &newPos,
                      int       ,//lengthDoc,
                      int      &istate, // internal state to move to
                      int	   &curr_family,
                      MainInfo   *p_MainInfo,
                      Accessor &styler
                      )
{
    if (!p_TranBlock) {
        assert(p_TranBlock && "doActions got null tran-block");
        return;
    }
    FamilyInfo *p_FamilyInfo = p_MainInfo->GetCurrFamily();
    if (!p_TranBlock->token_check && oldPos > 0) {
        doColorAction(p_TranBlock->upto_color, p_TranBlock->no_keyword, oldPos, p_FamilyInfo, styler);
    }
    doColorAction(p_TranBlock->include_color, p_TranBlock->no_keyword, newPos, p_FamilyInfo, styler);
    int origOldPos = oldPos;
    if (p_TranBlock->search_type == TRAN_SEARCH_EMPTY) {
        // leave oldPos unchanged
    } else if (p_TranBlock->do_redo) {
        // leave oldPos unchanged
        // oldPos = newPos - 1;
    } else {
        oldPos = newPos;
    }
    int push_pop_state = p_TranBlock->push_pop_state;

    // Determine if we hit end-of-line, and should redo
    int eol_state = p_MainInfo->curr_eol_transition;
    if (eol_state) {
        int start_line = styler.GetLine(origOldPos);
        int end_line   = styler.GetLine(newPos);
        // Are we going to use the eol-state this time?
        int nextOldPos;
        if (end_line > start_line) {
            oldPos = styler.LineStart(start_line + 1);
#if 0
            fprintf(stderr, "#1: start-line=%d, end-line=%d, setting oldPos=%d=>%d\n",
                    start_line, end_line, origOldPos, oldPos);
#endif
        } else if (origOldPos >= (nextOldPos =
                                  styler.LineStart(start_line + 1)) - 1
                   && newPos >= nextOldPos) {
            oldPos = nextOldPos;
#if 0
            fprintf(stderr, "#2: start-line=%d, end-line=%d, setting oldPos=%d=>%d\n",
                    start_line, end_line, origOldPos, oldPos);
#endif
        } else {
            eol_state = 0;
        }
    }

    if (p_TranBlock->clear_current_delimiter) {
        p_MainInfo->current_delimiter.clear();
    }

    int new_state = 0;
    int new_family = curr_family; // ms vc++ 6 can't follow when this var
    // isn't initialized and isn't used, so set it to an innocuous value

    if (p_TranBlock->eol_target_state) {
        if (!p_MainInfo->curr_eol_transition) {
            p_MainInfo->curr_eol_transition = p_TranBlock->eol_target_state;
        } else if (p_MainInfo->curr_eol_transition != p_TranBlock->eol_target_state) {
            // Currently if we have a non-zero eol-target state that's
            // different from the one specified in an at_eol directive,
            // we ignore it.
            fprintf(stderr, "Current EOL setting is 0x%08x, ignoring 0x%08x\n",
                    p_MainInfo->curr_eol_transition,
                    p_TranBlock->eol_target_state);
        }
    }
    // Now look to see if we need to act on a pending EOL-state.
    if (eol_state != 0) {
        new_state = SF_GET_STATE(eol_state);
        new_family = SF_GET_FAMILY(eol_state);
        // Set the global state to 0.
        p_MainInfo->curr_eol_transition = 0;
        // This deliberately squelches any pushing that would be done here.
        //XXX: Pop all push-state transitions pushed since the eol_state
        // thing was set.
    } else if (push_pop_state > 0) {
        p_MainInfo->PushState(push_pop_state);
    } else if (push_pop_state == -1) {
        int tmp = p_MainInfo->PopState();
        new_state = SF_GET_STATE(tmp);
        new_family = SF_GET_FAMILY(tmp);
    }
    if (!new_state) {
        new_state = p_TranBlock->new_state;
        if (new_state >= 1) {
            new_family = p_TranBlock->new_family;
        }
    }
    if (new_state >= 1 && new_state < p_MainInfo->NumTransitions()) {
#if 0
        fprintf(stderr, "state tran %d=>%d at pos %d [%d:%d] => %d\n",
                istate,
                new_state,
                origOldPos,
                styler.GetLine(origOldPos),
                origOldPos - styler.LineStart(styler.GetLine(origOldPos)),
                newPos);
#endif
        istate = new_state;
        if (new_family >= 0 && curr_family != new_family) {
            curr_family = new_family;
            p_MainInfo->SetCurrFamily(curr_family);
        }
    }
}
/*
 * Write no more than bufCapacity characters into the buffer:
 * If oldPos <= bufCapacity - 2, stopPoint will be 0, and there's
 * no problem.
 * 
 * Othewise, we set stopPoint = oldPos - bufCapacity + 2;
 * segStart >= stopPoint
 * Then we try to write chars segStart ... oldPos inclusive
 * oldPos - segStart + 1 >=
 * oldPos - stopPoint + 1 ==
 * oldPos - (oldPos - bufCapacity + 2) + 1 ==
 * bufCapacity - 1
 * which leaves us room for the null byte.
 *
 */ 

static void getSegmentParts(char *buf,
                            int bufCapacity,
                            int &segStart,
                            int oldPos,
                            int this_style,
                            Accessor		&styler)
{
    // Allow 1 for styler[oldPos], 1 for the null byte
    int stopPoint = oldPos - bufCapacity + 2; 
    if (stopPoint < 0) {
        stopPoint = 0;
    }
    for (segStart = oldPos;
         segStart > stopPoint && actual_style(styler.StyleAt(segStart - 1)) == this_style;
         segStart -= 1) {
        //EMPTY
    }
    char *p_s;
    int i;
    for (i = segStart, p_s = buf; i <= oldPos; i++) {
        *p_s++ = styler[i];
    }
    *p_s = 0;
}
                            
static inline int columnStartPos(int pos, Accessor &styler) {
    return pos - styler.LineStart(styler.GetLine(pos));
}

// We do this when we've matched a conditional string, like 
// '/' if preferRE : paint(upto, CSL_DEFAULT), => IN_CSL_REGEX

// Return true if there's no test, or if it passes
// The idea is to walk backwards from the current point,
// looking at each sequence of styled text, and determining
// what to do next.

static bool doLookBackTest(Transition      *p_TranBlock,
                           int				oldPos,
                           MainInfo		   *p_MainInfo,
                           Accessor		&styler)
{
    if (oldPos <= 0) return true;
    if (!p_TranBlock->token_check) return true;

    FamilyInfo	*p_FamilyInfo = p_MainInfo->GetCurrFamily();
    if (!p_FamilyInfo) {
        assert(0 && "Can't get family info");
        return true;
    }

    /* If there's an upto thing, color it now, as we need to
     * test against the text to the left.
     */
    doColorAction(p_TranBlock->upto_color, p_TranBlock->no_keyword, oldPos, p_FamilyInfo, styler);
    LookBackTests  *p_LookBackTests = p_FamilyInfo->GetLookBackTests();
    if (!p_LookBackTests) return true;
    oldPos--;
    char buf[200];
    int segStart;
    styler.Flush();
    while (oldPos > 0) {
        int this_style = actual_style(styler.StyleAt(oldPos));
        if (!p_LookBackTests->StyleInRange(this_style)) {
            // We're at the beginning of a subfamily,
            // so make the same assumption we make at the start of the doc
            return true;
        }
        getSegmentParts(buf, sizeof(buf)/sizeof(buf[0]),
                        segStart, oldPos,
                        this_style, styler);
        int action = -1;
        int num_tests = p_LookBackTests->GetTestCount();
        for (int i = 0; action == -1 && i < num_tests; i++) {
            LookBackTestObj *p_LBTest = p_LookBackTests->GetTest(i);
            if (!p_LBTest || p_LBTest->Style() != this_style) {
                continue;
            }
            int list_type = p_LBTest->Type();
            if (list_type == LBTEST_LIST_ALL) {
                action = p_LBTest->Action();
            } else if (list_type == LBTEST_LIST_KEYWORDS) {
                if (p_LBTest->InKeywords(buf)) {
                    action = p_LBTest->Action();
                }
            } else if (list_type == LBTEST_LIST_STRINGS) {
                // for each string in the list of strings
                // if we're looking at it, all one style, 
                // go do the action.

                int segLen = (int) strlen(buf);
                char **pp_StringList = p_LBTest->Strings();
                if (!pp_StringList)
                    continue;
                while (*pp_StringList) {
                    int thisLen = (int) strlen(*pp_StringList);
                    if (thisLen <= segLen
                        && !strncmp(*pp_StringList,
                                    buf + (segLen - thisLen), thisLen)) {
                        // Adjust segStart in case we're skipping this one
                        segStart = oldPos - segLen;
                        action = p_LBTest->Action();
                        break;
                    }
                    pp_StringList++;
                }
            }
        } // end for loop
        if (action == -1) {
            action = p_LookBackTests->GetDefault(this_style);
        }
        if (action == LBTEST_ACTION_REJECT) {
            return false;
        } else if (action == LBTEST_ACTION_ACCEPT) {
            return true;
        } else {
            // Skip
            oldPos = segStart - 1;
        }
    }  // end while loop
    // If we moved to the beginning of the doc, assume we'll transition
    return true;
}
                           

static bool lookingAtString(const char   *p_target,
                            int     oldPos,
                            int    &newPos,
                            int     lengthDoc,
                            Accessor &styler)
{
    int targetLen = (int) strlen(p_target);
    if (lengthDoc - oldPos < targetLen) {
        // Not enough space
        return false;
    }
    const char *s = p_target;
    while (*s && oldPos < lengthDoc) {
        if (*s != styler[oldPos]) {
            return false;
        }
        s += 1;
        oldPos += 1;
    }
    newPos = oldPos;
    return true;
}

static bool lookingAtMatch(
#ifdef DEBUG
                           char   *p_origPattern,
#endif
                           pcre    *p_compiledPattern,
                           int      oldPos,
                           int     &newPos,
                           int      ,//lengthDoc,
                           LexString   *p_CurrTextLine,
                           MainInfo		   *p_MainInfo,
                           Accessor &styler)
{
    if (!p_compiledPattern) {
        return false;
    }
    int rc;
    int currLine = styler.GetLine(oldPos);
    int currLineStart = styler.LineStart(currLine);
    if (p_CurrTextLine->CurrLine() != currLine) {
        rc = (int) p_CurrTextLine->SetLine(oldPos, styler);
        if (!rc) {
            return false;
        }
    }
    char *p_subject = p_CurrTextLine->Val();
    rc = pcre_exec(p_compiledPattern,
                       NULL, // no extra data - we didn't study the pattern
                       p_subject,
                       (int) strlen(p_subject),
                       oldPos - currLineStart,
                       PCRE_ANCHORED, /* default options */
                       p_MainInfo->ovector,   /* output vector for substring information */
                       p_MainInfo->ovec_count);/* number of elements in the output vector */
    bool res;
    if (rc < 0) {
        res = false;
    } else if (p_MainInfo->ovector[0] == oldPos - currLineStart) {
        res = true;
        int num_chars_matched = p_MainInfo->ovector[1] - p_MainInfo->ovector[0];
        newPos = oldPos + num_chars_matched;
        p_MainInfo->num_captured_groups = rc - 1;
    } else {
        res = false;
    }
    return res;
}

// Using strchr and pointer arithmetic might be more elegant, but
// it's probably slower to run.
static char getOpposite(char ch) {
    switch (ch) {
    case '[': return ']';
    case '{' : return '}';
    case '(': return ')';
    case '<': return '>';
    default: return ch;
    }
}

static int simpleHash(unsigned int maxVal, const char *delim) {
    unsigned int h = 0;
    const char *p = delim;
    while (*p) {
        h += (h << 1) ^ *p++;
        if (h > maxVal) {
            unsigned int diff = h & ~maxVal;
            while (diff && (diff & 1) == 0) {
                diff >>= 2;
            }
            h = (h & maxVal) | diff;
        }
    }
    return (int) h;
}

static void setNewDelimiter(Transition      *p_TranBlock,
                            MainInfo		   *p_MainInfo,
                            LexString   *p_CurrTextLine,
                            int , // i,
                            Accessor & //styler
                            )
{
    int do_opposite = SF_GET_STATE(p_TranBlock->target_delimiter);
    int group_num = SF_GET_FAMILY(p_TranBlock->target_delimiter);
    if (group_num <= p_MainInfo->num_captured_groups) {
        int start_delim = p_MainInfo->ovector[2 * group_num];
        int end_delim = p_MainInfo->ovector[2 * group_num + 1];
        char *p_delim_start = &(p_CurrTextLine->Val()[start_delim]);
        bool succeeded;
        int len = end_delim - start_delim;
        char c = p_delim_start[len];
        if (!do_opposite) {
            p_delim_start[len] = 0;
            p_MainInfo->current_delimiter = p_delim_start;
            p_delim_start[len] = c;
            succeeded = true;
        } else if (end_delim - start_delim != 1) {
            fprintf(stderr,
                    "udl: can't capture delimiter [%d,%d] on [%s]\n",
                    start_delim, end_delim, p_CurrTextLine->Val());
            succeeded = false;
        } else {
            char buf[2];
            buf[0] = getOpposite(*p_delim_start);
            buf[1] = 0;
            p_MainInfo->current_delimiter = buf;
            succeeded = true;
        }
    }
}

static void ColouriseTemplate1Doc(unsigned int startPos,
                                  int length,
                                  int
#if 0
				  initStyle
#endif
				  ,
                                  WordList *keywordlists[],
                                  Accessor &styler)
{
#if 0
    fprintf(stderr,
            "udl: ColouriseTemplate1Doc(startPos=%d, length=%d, initStyle=%d\n",
            startPos,
            length, initStyle);
#endif

#ifdef LOG_MEM
    if (!fp_log) {
        OpenFPLog();
    }
    LogEvent(true, "ColouriseTemplate1Doc", &styler);
#endif

    bool rc;
    WordList &wl = *keywordlists[0];
    char *p_subLanguage = wl.words[0];
    if (!p_subLanguage || !p_subLanguage[0]) {
        // This happens as part of a fallback in
        // koTemplateLanguageBase.py::koTemplateLanguage.get_lexer
        // when no lexres can be found.  This is the code:
        //      lex.setKeywords(0, [])
        // The result is that nothing gets colorized, but we
        // don't need a message.
        
        //fprintf(stderr, "udl: ColouriseTemplate1Doc: no sublanguage\n");
        styler.ColourTo(length, 0);
        return;
    }
    
    MainInfo *p_MainInfo = LexerList.Intern(p_subLanguage);
    if (!p_MainInfo) {
        fprintf(stderr, "udl: ColouriseTemplate1Doc: couldn't create a MainInfo\n");
        assert(0 && "Can't create a MainInfo");
        return;
    }
    if (!p_MainInfo->IsReady()) {
        rc = false;
    } else {
        rc = true;
    }
    if (!rc) {
        styler.ColourTo(length, 0);
        fprintf(stderr, "udl: ColouriseTemplate1Doc: failed to load the engine\n");
        return;
    }
    
    int curr_family;
    TransitionTable  *p_TransitionTable = p_MainInfo->GetTable();
#if 0
    int origStartPos = startPos;
    int origLength = length;
#endif
    int istate; // the internal state
    synchronizeDocStart(startPos, length, istate, curr_family,
                        styler, // ref args
                        p_MainInfo
                        );
    FamilyInfo		 *p_FamilyInfo = p_MainInfo->GetCurrFamily();
    if (!p_FamilyInfo) {
        fprintf(stderr, "udl: ColouriseTemplate1Doc: Can't get family info\n");
        assert(0 && "Can't get family info");
        return;
    }

    if (length == 0) {
        return;
    }
#if 0
    int origLine = styler.GetLine(origStartPos);
    int currLine = styler.GetLine(startPos);
    fprintf(stderr,
            "udl: ColouriseTemplate1Doc -- sync moved from %d[%d:%d](%d) to %d[%d:%d](%d), internal state %d\n",
            
            origStartPos,
            origLine + 1,
            origStartPos - styler.LineStart(origLine),
            origLength,
            startPos,
            currLine + 1,
            startPos - styler.LineStart(currLine),
            length,
            istate);
#endif

    TransitionInfo *p_TransitionInfo;
    Transition     *p_TranBlock;
    LexString	   *p_CurrTextLine = new LexString;
    if (!p_CurrTextLine->Init()) {
        fprintf(stderr, "udl: failed to init the current line tracker\n");
        return;
    } else if (!p_CurrTextLine->SetLine(startPos, styler)) {
        fprintf(stderr, "udl: failed to setup the line tracker at pos %d\n",
                startPos);
        return;
    }
    
    char ch;
    int lengthDoc = startPos + length;
    int totalDocLength = styler.Length();
    int i, newPos;
    int lineStartUpdateState = styler.GetLine(startPos) - 1;
    if (lineStartUpdateState < 0) lineStartUpdateState = 0;
    int redoCount = 0;
    const int redoLimit = 1000;

    char lexerMask = 0x3f; // 6 bits

    styler.StartAt(startPos, lexerMask);
    styler.StartSegment(startPos);
    i = startPos;
    for (;;) {
        ch = styler.SafeGetCharAt(i);
        if (styler.IsLeadByte(ch)) {
            i += 1;
            continue;
        }
        // set the line-state, to force further updates
        // Update the line-state if we need to
        // This is why we can't use a loop like
        // for (i = startPos; i < lengthDoc; i++) : lengthDoc might change.
        
        int lineCurrent = styler.GetLine(i);
        if (lineStartUpdateState < lineCurrent) {
            for (int iLine = lineStartUpdateState; iLine < lineCurrent; iLine++) {
                // We don't look at the current line, so there's no danger
                // that iLine + 1 exceeds the document boundary.
                int lineEndPos = styler.LineStart(iLine + 1) - 1;
                int oldLineState = styler.GetLineState(iLine);
                int currStackSize = p_MainInfo->StateStackSize();
                int newLineState = create_line_state(currStackSize,
                                                     istate);
                
                // If we have an active delimiter, set the line-state
                // based on a hash of it.  Otherwise set it to the current style.
                if (p_MainInfo->current_delimiter[0]) {
                    // Create a hash of the delimiter, and or it in based
                    // on the current state
                    unsigned int delimHash = (simpleHash(DELIMITER_MASK,
                                                p_MainInfo->current_delimiter.c_str())
                                     & DELIMITER_MASK);
                    newLineState = update_line_state_from_delim(newLineState,
                                                                delimHash);
                    if (oldLineState != newLineState && iLine == lineCurrent - 1) {
                        // We changed delimiters, so force at least another line
                        int nextLine = lineCurrent + 1;
                        int nextLinePos = styler.LineStart(nextLine);
                        // update the target
                        if (lengthDoc < nextLinePos) {
                            int newLengthDoc = nextLinePos < totalDocLength ? nextLinePos : totalDocLength;
#if 0
                            fprintf(stderr,
                                    "Need to keep lexing, from %d to %d\n",
                                    lengthDoc, newLengthDoc);
#endif
                            lengthDoc = newLengthDoc;
                        }
                    }
                }
                styler.SetLineState(iLine, newLineState);
            }
            lineStartUpdateState = lineCurrent;
        }

        if (i >= lengthDoc) {
            break;
        }

        // Time to enter the engine
        p_TransitionInfo = p_TransitionTable->Get(istate);
        if (!p_TransitionInfo) {
            // No point continuing ... there's no table info
            break;
        }
        p_TranBlock = p_TransitionInfo->First();
        if (!p_TranBlock) {
            assert(p_TranBlock && "No transition block for this state .. bail out");
            // Again, no point continuing, as we're stuck as this istate
            break;
        }
        bool passedPart1 = false;
        for (; p_TranBlock; p_TranBlock = p_TranBlock->Next()) {
            if (p_TranBlock->search_type == TRAN_SEARCH_STRING) {
                if (lookingAtString(p_TranBlock->p_search_string,
                                    i, newPos, lengthDoc, styler)) {
#if 0
                    fprintf(stderr, "Matched [%s] at pos %d\n",
                            p_TranBlock->p_search_string, i);
#endif
                    passedPart1 = true;
                }
            } else if (p_TranBlock->search_type == TRAN_SEARCH_REGEX) {
                if (lookingAtMatch(
#ifdef DEBUG
                                   p_TranBlock->p_search_string,
#endif
                                   p_TranBlock->p_pattern,
                                   i, newPos, lengthDoc, p_CurrTextLine,
                                   p_MainInfo,
                                   styler)) {
#if 0
                    fprintf(stderr, "Matched [%s] at pos %d\n",
                            p_TranBlock->p_search_string, i);
#endif
                    passedPart1 = true;
                }
            } else {
                assert(p_TranBlock->search_type == TRAN_SEARCH_DELIMITER);
                if (p_MainInfo->current_delimiter[0]
                    && lookingAtString(p_MainInfo->current_delimiter.c_str(),
                                       i, newPos, lengthDoc, styler)) {
                    passedPart1 = true;
#if 0
                    fprintf(stderr, "keeping delimiter %s: %s\n",
                            p_MainInfo->current_delimiter.c_str(),
                            p_TranBlock->keep_current_delimiter ? "true" : "false");
#endif
                    if (!p_TranBlock->keep_current_delimiter) {
                        p_MainInfo->current_delimiter.clear(); // can't undo
                    }
                }
            }
            if (passedPart1 && doLookBackTest(p_TranBlock, i, p_MainInfo,
                                              styler)) {
                if (p_TranBlock->search_type == TRAN_SEARCH_REGEX
                    && p_TranBlock->target_delimiter) {
                    setNewDelimiter(p_TranBlock, p_MainInfo,
                                    p_CurrTextLine, i, styler);
                }
                break;
            } else {
                p_MainInfo->num_captured_groups = 0;
                passedPart1 = false;
            }
        }
        if (!p_TranBlock) {
            p_TranBlock = p_TransitionInfo->GetEmptyInfo();
        }
        if (p_TranBlock) {
            // Watch out for infinite-redo loops
            if (p_TranBlock->do_redo && ++redoCount > redoLimit) {
                int line = styler.GetLine(i);
                fprintf(stderr,
                        "udl: looks like there's an infinite redo-loop at position %d (%d:%d), matching (%s) ... breaking it\n",
                        i, line + 1, i + 1 - styler.LineStart(line),
                        p_TranBlock->p_search_string);
                p_TranBlock->do_redo = false;
                doActions(p_TranBlock, i, newPos, lengthDoc,
                          istate, curr_family, p_MainInfo,
                          styler);
                p_TranBlock->do_redo = true;
                redoCount = 0;
            } else {
                int oldPos = i;
                doActions(p_TranBlock, i, newPos, lengthDoc,
                          istate, curr_family, p_MainInfo,
                          styler);
                if (oldPos != i) {
                    redoCount = 0;
                }
            }
        } else {
            ++i;
            redoCount = 0;
        }
    }
    // Check end-of-buffer conditions
    p_TransitionInfo = p_TransitionTable->Get(istate);
    // Coding it this way because VC++ issues warning C4706:
    // assignment within conditional expression
    if (p_TransitionInfo) {
        p_TranBlock = p_TransitionInfo->GetEOFInfo();
        if (p_TranBlock) {
            newPos = lengthDoc;
            doActions(p_TranBlock, i, newPos, lengthDoc, istate,
                      curr_family, p_MainInfo,
                      styler);
        }
    }
    delete p_CurrTextLine;
    LogEvent(false, "ColouriseTemplate1Doc", &styler);
}

//Precondition: buf can contain at least 3 chars, including the null byte.

//Precondition: s points to a zero-terminated string

static bool containsNonSpace(char *s) {
    while (*s) {
        if (!isspacechar(*s)) {
            return true;
        }
        ++s;
    }
    return false;
}

static void getToken(int 	curr_style,
                     int 	pos,
                     int	docLength,
                     char  *buf,
                     int 	bufSize,
                     Accessor &styler)
{
    char ch = buf[0] = styler[pos];
    if (pos >= docLength || ch == '\n') {
        buf[1] = 0;
        return;
    } else if (ch == '\r' && styler[pos + 1] == '\n') {
        buf[1] = '\n';
        buf[2] = 0;
        return;
    }
    char *p_s = &buf[1];
    int maxNumToCopy = docLength - pos + 1; // include zero byte
    if (maxNumToCopy > bufSize) {
        docLength = pos + bufSize - 1;
    }
    // No need to test the first char of the return buf
    for (++pos; pos < docLength; ++pos) {
        ch = styler[pos];
        if (ch == '\r' || ch == '\n') {
            break;
        }
        if (safeStyleAt(pos, styler) == curr_style) {
            *p_s++ = ch;
        } else {
            break;
        }
    }
    *p_s = 0;
}


static void FoldUDLDoc(unsigned int startPos, int length, int
#if 0
		       initStyle
#endif
		       ,
                      WordList *keywordlists[], Accessor &styler)
{
#if 0
    fprintf(stderr,
            "udl: FoldUDLDoc(startPos=%d, length=%d, initStyle=%d\n",
            startPos,
            length, initStyle);
#endif
#ifdef LOG_MEM
    if (!fp_log) {
        OpenFPLog();
    }
    LogEvent(true, "FoldUDLDoc", &styler);
#endif
    MainInfo *p_MainInfo = LexerList.Intern((*(keywordlists[0])).words[0]);
    if (!p_MainInfo || !p_MainInfo->IsReady()) {
        return;
    }
	const bool foldCompact = styler.GetPropertyInt("fold.compact", 1) != 0;
	// bool foldComment = styler.GetPropertyInt("fold.comment") != 0;
    int curr_family;
    int istate; // the internal state
    synchronizeDocStart(startPos, length, istate, curr_family,
                        styler, // ref args
                        p_MainInfo
                        );
    FamilyInfo		 *p_FamilyInfo = p_MainInfo->GetCurrFamily();
    if (!p_FamilyInfo) {
        assert(0 && "Can't get family info");
        return;
    }

    if (length == 0)
        return;

    // Variables to allow folding.
    unsigned int endPos = startPos + length;
	int visibleChars = 0;
    int lineCurrent = styler.GetLine(startPos);
	int levelPrev = startPos == 0 ? 0 : (styler.LevelAt(lineCurrent)
                                         & SC_FOLDLEVELNUMBERMASK
                                         & ~SC_FOLDLEVELBASE);
	int levelCurrent = levelPrev;
    char s[100];
    unsigned int i = startPos;
    bool buffer_ends_with_eol = false;
	while (i < endPos) {
        int lengthUsed;
        int direction;
        int curr_style = actual_style(styler.StyleAt(i));

        // Blast through the buffer one token at a time.
        // Note that there is m * n behavior with token lookup,
        // where m is the length of a consecutive set of operator-like
        // tokens, and n is the number of fold directives.

        // Hopefully both these numbers will be small.
        
        getToken(curr_style, i, endPos, s, sizeof(s)/sizeof(s[0]), styler);

        lengthUsed = 0;
        direction = p_MainInfo->GetFoldChange(s, curr_style, lengthUsed);
        if (direction) {
            levelCurrent += direction;
            if (!lengthUsed) {
                fprintf(stderr, "udl: internal error: FoldUDLDoc: matched a folder, but aren't advancing i at line %d, pos %d\n", lineCurrent, i);
                i++;
            } else {
                i += lengthUsed;
            }
        } else if (lengthUsed) {
            i += lengthUsed;
        } else {
            i += (int) strlen(s);
        }
        if (levelCurrent < 0)
            levelCurrent = 0;
        
		bool atEOL = (s[0] == '\r' || s[0] == '\n');
		if (atEOL) {
			int lev = levelPrev;
			if (visibleChars == 0 && foldCompact)
				lev |= SC_FOLDLEVELWHITEFLAG;
			if ((levelCurrent > levelPrev) && (visibleChars > 0))
				lev |= SC_FOLDLEVELHEADERFLAG;
            styler.SetLevel(lineCurrent, lev|SC_FOLDLEVELBASE);
			lineCurrent++;
			levelPrev = levelCurrent;
			visibleChars = 0;
            buffer_ends_with_eol = true;
		} else if (containsNonSpace(s)) {
			visibleChars++;
            buffer_ends_with_eol = false;
        }
    }
	// Fill in the real level of the next line, keeping the current flags as they will be filled in later
    if (!buffer_ends_with_eol) {
        lineCurrent++;
        int new_lev = levelCurrent;
        if (visibleChars == 0 && foldCompact)
            new_lev |= SC_FOLDLEVELWHITEFLAG;
			if ((levelCurrent > levelPrev) && (visibleChars > 0))
				new_lev |= SC_FOLDLEVELHEADERFLAG;
            levelCurrent = new_lev;
    }
	styler.SetLevel(lineCurrent, levelCurrent|SC_FOLDLEVELBASE);
    LogEvent(false, "FoldUDLDoc", &styler);
        
}

static const char * const UDLWordListDesc[] = {
    "Keywords",
    0
};

LexerModule lmUDL(SCLEX_UDL, ColouriseTemplate1Doc, "udl", FoldUDLDoc, UDLWordListDesc);

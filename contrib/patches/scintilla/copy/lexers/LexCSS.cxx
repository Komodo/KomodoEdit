// Scintilla source code edit control
/** @file LexCSS.cxx
 ** Lexer for Cascading Style Sheets
 ** Written by Eric Promislow
 **/
// Copyright 1998-2011 by ActiveState Software Inc.
// The License.txt file describes the conditions under which this software may be distributed.

#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <stdarg.h>
#include <assert.h>
#include <ctype.h>

#include "ILexer.h"
#include "Scintilla.h"
#include "SciLexer.h"

#include "WordList.h"
#include "LexAccessor.h"
#include "Accessor.h"
#include "StyleContext.h"
#include "CharacterSet.h"
#include "LexerModule.h"

#ifdef SCI_NAMESPACE
using namespace Scintilla;
#endif


static inline bool IsAWordChar(const unsigned int ch) {
	/* FIXME:
	 * The CSS spec allows "ISO 10646 characters U+00A1 and higher" to be treated as word chars.
	 * Unfortunately, we are only getting string bytes here, and not full unicode characters. We cannot guarantee
	 * that our byte is between U+0080 - U+00A0 (to return false), so we have to allow all characters U+0080 and higher
	 */
	return ch >= 0x80 || isalnum(ch) || ch == '-' || ch == '_';
}

static inline bool IsSafeAlpha(const unsigned int ch) {
	return ch >= 0x80 || isalpha(ch) || ch == '_';
}

static void getCurrentWord(char buf[],
                           unsigned int capacity,
                           unsigned int wordStart,
                           unsigned int currentPos,
                           Accessor &styler) {
	char *s = buf;
	while (wordStart < currentPos
	       && !IsAWordChar(styler[wordStart])) {
		wordStart += 1;
	}
	if (currentPos - wordStart >= capacity) {
		currentPos = capacity + wordStart - 1;
	}
	for (; wordStart < currentPos; wordStart++) {
		*s++ = styler[wordStart];
	}
	*s = 0;
}

static void classifyWordAndStyle(StyleContext &sc,
                                 Accessor &styler,
                                 WordList *keywordlists[],
                                 bool styleTheDefault,
                                 int defaultStyle) {
	char buf[100];
	WordList &css1Props = *keywordlists[0];
	WordList &css2Props = *keywordlists[2];
	WordList &css3Props = *keywordlists[3];
	WordList &exProps = *keywordlists[5];
	unsigned int wordStart = styler.GetStartSegment();
	getCurrentWord(buf, sizeof(buf)/sizeof(buf[0]),
		       wordStart, sc.currentPos, styler);
	if (css1Props.InList(buf))
		sc.ChangeState(SCE_CSS_IDENTIFIER);
	else if (css2Props.InList(buf))
		sc.ChangeState(SCE_CSS_IDENTIFIER2);
	else if (css3Props.InList(buf))
		sc.ChangeState(SCE_CSS_IDENTIFIER3);
	else if (exProps.InList(buf))
		sc.ChangeState(SCE_CSS_EXTENDED_IDENTIFIER);
	else if (styleTheDefault)
		sc.ChangeState(defaultStyle);
	sc.SetState(SCE_CSS_DEFAULT);
}

// Ignore comments.  Resolve ambiguity by looking for particular characters.
static bool followedByChars(int pos, int endPos,
			    const char *posChars, const char *negChars,
			    LexAccessor &styler ) {
	int ch;
	for (; pos < endPos; pos++) {
		ch = styler.SafeGetCharAt(pos);
		if (strchr(posChars, ch)) {
			return true;
		} else if (strchr(negChars, ch)) {
			return false;
		}
	}
	return false;
}

static bool startsArg(int pos, Accessor &styler) {
    char c;
    while (pos > 0 && ((c = styler[pos]) == ' ' || c == '\t')) {
        pos -= 1;
    }
    return (c = styler[pos]) == '(' || c == ',';
}

typedef struct fields {
	unsigned int f_main_substate: 3;
	unsigned int f_nested_declaration_count: 8; // high, but we can spare the bits
	unsigned int f_important_substate: 2;
	unsigned int f_string_substate: 3;
	unsigned int f_comment_substate: 2;
	unsigned int f_identifier_substate: 1;
	unsigned int f_style: 8;
} fn_fields;

typedef union fieldUnion {
	unsigned long fn_data;
	fn_fields css_fields;
} fieldUnion;

#define fillUnion(fn, main_substate, nested_declaration_count, \
	important_substate, string_substate, comment_substate, \
		      identifier_substate, style)      \
	fn.css_fields.f_main_substate = main_substate; \
	fn.css_fields.f_nested_declaration_count = nested_declaration_count; \
	fn.css_fields.f_important_substate = important_substate; \
	fn.css_fields.f_string_substate = string_substate; \
	fn.css_fields.f_comment_substate = comment_substate; \
	fn.css_fields.f_identifier_substate = identifier_substate; \
	fn.css_fields.f_style = style;

// 'unused' is just to give these two macros different signatures.
#define extractFromUnion(fn, main_substate, nested_declaration_count, \
	important_substate, string_substate, comment_substate, \
		      identifier_substate, style, unused) \
	main_substate = fn.css_fields.f_main_substate; \
	nested_declaration_count = fn.css_fields.f_nested_declaration_count; \
	important_substate = fn.css_fields.f_important_substate; \
	string_substate = fn.css_fields.f_string_substate; \
	comment_substate = fn.css_fields.f_comment_substate; \
	identifier_substate = fn.css_fields.f_identifier_substate; \
	style = fn.css_fields.f_style;

static void ColouriseCssDoc(unsigned int startPos, int length, int initStyle, WordList *keywordlists[], Accessor &styler) {
	// WordList &css1Props = *keywordlists[0];
	WordList &pseudoClasses = *keywordlists[1];
	// WordList &css2Props = *keywordlists[2];
	// WordList &css3Props = *keywordlists[3];
	WordList &pseudoElements = *keywordlists[4];
	// WordList &exProps = *keywordlists[5];
	WordList &exPseudoClasses = *keywordlists[6];
	WordList &exPseudoElements = *keywordlists[7];

	bool isLessDocument, isScssDocument, isSassDocument;
	// SCSS = "Sassy CSS"; SASS is no longer supported.
	
	// Main State
	const int MAIN_SUBSTATE_TOP_LEVEL = 0;
	const int MAIN_SUBSTATE_IN_SELECTOR = 1;
	const int MAIN_SUBSTATE_IN_DECLARATION_NAME = 2;
	const int MAIN_SUBSTATE_IN_PROPERTY_VALUE = 3;
	const int MAIN_SUBSTATE_AMBIGUOUS_SELECTOR_OR_PROPERTY_NAME = 4;
	const int MAIN_SUBSTATE_SCSS_ASSIGNMENT = 5;
	const int MAIN_SUBSTATE_IN_MEDIA_TOP_LEVEL = 6;
	const int MAIN_SUBSTATE_IN_FONT_FACE = 7;
	
	int main_substate = MAIN_SUBSTATE_TOP_LEVEL;
	int nested_declaration_count = 0;
	
	// Substates
	const int IMPORTANT_SUBSTATE__AFTER_BANG = 0; // after "!"
	const int IMPORTANT_SUBSTATE__IN_COMMENT = 1; // after "!  /* "
	const int IMPORTANT_SUBSTATE__IN_WHITESPACE = 2; // after "! /* ... */  "
	const int IMPORTANT_SUBSTATE__IN_WORD = 3; // after "! /* ... */  <letter>"
	int important_substate = IMPORTANT_SUBSTATE__AFTER_BANG;
	
	const int STRING_SUBSTATE__IN_STRING = 0; // inside a string
	//const int STRING_SUBSTATE__IN_LESS_JS_ESCAPE = 1; // in "...` ...
	//const int STRING_SUBSTATE__IN_LESS_INTERPOLATE = 2; // in "...@{ ...
	const int STRING_SUBSTATE__IN_LESS_CSS_ESCAPE = 3; // in ~"...
	//const int STRING_SUBSTATE__IN_SASS_INTERPOLATE = 4; // in "...#{...
	int string_substate = STRING_SUBSTATE__IN_STRING;
	
	const int COMMENT_SUBSTATE_BLOCK = 1;
	const int COMMENT_SUBSTATE_LINE = 2;
	int comment_substate = 0;
    
	const int IDENTIFIER_SUBSTATE_DEFAULT = 0;
	const int IDENTIFIER_SUBSTATE_SCSS_DOLLAR = 1;
	//const int IDENTIFIER_SUBSTATE_LESS_ATSIGN = 2;
	int identifier_substate = IDENTIFIER_SUBSTATE_DEFAULT;

	bool in_top_level_directive = false;
	const char* moz_document_words[5] = {
	  "url",
	  "url-prefix",
	  "domain",
	  "regexp",
	  NULL
	};

	isLessDocument = styler.GetPropertyInt("lexer.css.less.language") != 0;
	isScssDocument = styler.GetPropertyInt("lexer.css.scss.language") != 0;
	isSassDocument = styler.GetPropertyInt("lexer.css.sass.language") != 0;

	unsigned int origStartPos = startPos;
	int lineCurrent = styler.GetLine(origStartPos);
	startPos = styler.LineStart(lineCurrent);
	fieldUnion fdata; // for line-state
	
	if (lineCurrent > 0) {
		// Update the state based on whatever was going on at the end
		// of the previous line.
		fdata.fn_data = styler.GetLineState(lineCurrent - 1);
		extractFromUnion(fdata, main_substate, nested_declaration_count,
				 important_substate, string_substate,
				 comment_substate, identifier_substate, initStyle, 1);
	}

	int finalLength = length + origStartPos;
	bool sass_atStartOfLine = true;
	StyleContext sc(startPos, finalLength, initStyle, styler);

	// This is now a straightforward state machine, with some
	// sub-state tracking apart from the styles.
    
	for (; sc.More(); sc.Forward()) {
		int ch = sc.ch;
		char s2[100];
		switch (sc.state) {
		case SCE_CSS_IDENTIFIER:
			if (!IsAWordChar(ch)) {
				if (identifier_substate == IDENTIFIER_SUBSTATE_SCSS_DOLLAR) {
					// In SCSS, all $... things are identifiers only.
					// In Less, @... things could be directives as well.
					identifier_substate = IDENTIFIER_SUBSTATE_DEFAULT;
					sc.SetState(SCE_CSS_DEFAULT);
				} else {
					classifyWordAndStyle(sc, styler, keywordlists,
							     true, SCE_CSS_UNKNOWN_IDENTIFIER);
				}
			}
			break;

		case SCE_CSS_PSEUDOCLASS:
			if (!IsAWordChar(ch)) {
				int wordStart = styler.GetStartSegment();
				getCurrentWord(s2, sizeof(s2)/sizeof(s2[0]),
					       wordStart, sc.currentPos, styler);
				if (pseudoClasses.InList(s2))
					sc.ChangeState(SCE_CSS_PSEUDOCLASS);
				else if (pseudoElements.InList(s2))
					sc.ChangeState(SCE_CSS_PSEUDOELEMENT);
				else if (exPseudoClasses.InList(s2))
					sc.ChangeState(SCE_CSS_EXTENDED_PSEUDOCLASS);
				else if (exPseudoElements.InList(s2))
					sc.ChangeState(SCE_CSS_EXTENDED_PSEUDOELEMENT);
				else
					sc.ChangeState(SCE_CSS_UNKNOWN_PSEUDOCLASS);
				sc.SetState(SCE_CSS_DEFAULT);
			}
			break;
            
		case SCE_CSS_VALUE: // rgb hash values
			if (!IsAWordChar(ch)) {
				char buf[12];
				int moz_doc_word_idx = 0;
				const char *docWord;
				int docWordLen;
				bool inURLLikeValue = false;
				sc.GetCurrentLowered(buf, sizeof(buf));
				for (moz_doc_word_idx = 0;
				     moz_doc_word_idx < 4;
				     moz_doc_word_idx++) {
					docWord = moz_document_words[moz_doc_word_idx];
					if (!strcmp(buf, docWord) && ch == '(') {
						inURLLikeValue = true;
						break;
					} else {
						docWordLen = strlen(docWord);
						if (!strncmp(buf, docWord, docWordLen)
						    && buf[docWordLen] == '(') {
							inURLLikeValue = true;
							break;
						}
					}
				}
				if (inURLLikeValue) {
					// Compatibility: make the ( in url( a value char
					// EMPTY
					if (ch == '(') {
						if (sc.chNext == '"') {
							sc.ForwardSetState(SCE_CSS_DOUBLESTRING);
						} else if (sc.chNext == '\'') {
							sc.ForwardSetState(SCE_CSS_SINGLESTRING);
						}
					} else if (strchr("\r\n\f \t)", ch)) {
						// Started with url(, have to end it now
						if (ch == ')') {
							// Keep the closing ')' with a value style so it
							
							// matches the opening '('
							sc.Forward();
						}
						sc.SetState(SCE_CSS_DEFAULT);
					}
				} else {
					sc.SetState(SCE_CSS_DEFAULT);
				}
			}
			break;

		case SCE_CSS_TAG:
			if (!IsAWordChar(ch)) {
				if (main_substate == MAIN_SUBSTATE_AMBIGUOUS_SELECTOR_OR_PROPERTY_NAME) {
					int i = sc.currentPos;
					if (ch == ':'
					    && styler.SafeGetCharAt(i + 1) == ' ') {
						// Style ambiguous name followed by :-space
						// as an identifier
						classifyWordAndStyle(sc, styler, keywordlists, true, SCE_CSS_IDENTIFIER);
					} else {
						// If this is followed by '{', treat it as a tag.
						// Otherwise it should be classified.
						char followChar = ' ';
						int ch;
						for (; i < finalLength; i++) {
							ch = styler.SafeGetCharAt(i);
							if (ch == ':' || ch == '{') {
								followChar = ch;
								break;
							}
						}
						if (followChar == '{') {
							// We're still nested
							sc.SetState(SCE_CSS_DEFAULT);
						} else {
							// If we're at end, assume we saw a ":"
							classifyWordAndStyle(sc, styler, keywordlists, false, SCE_CSS_UNKNOWN_IDENTIFIER);
						}
					}
				} else {
					sc.SetState(SCE_CSS_DEFAULT);
				}
			}
			break;
            
		case SCE_CSS_DIRECTIVE:
			if (!IsAWordChar(ch) && ch != '-') {
				char s2[100], *p_buf = s2;
				int wordStart = styler.GetStartSegment();
				getCurrentWord(s2, sizeof(s2)/sizeof(s2[0]),
					       wordStart, sc.currentPos, styler);
				if (*p_buf == '@') p_buf += 1;
				if (!CompareCaseInsensitive(p_buf, "import")
				    || !CompareCaseInsensitive(p_buf, "charset")
				    || !CompareCaseInsensitive(p_buf, "namespace")) {
					in_top_level_directive = true;
					main_substate = MAIN_SUBSTATE_IN_PROPERTY_VALUE;
				} else if (!CompareCaseInsensitive(p_buf, "media")) {
					main_substate = MAIN_SUBSTATE_IN_MEDIA_TOP_LEVEL;
				} else if (!CompareCaseInsensitive(p_buf, "font-face")) {
					main_substate = MAIN_SUBSTATE_IN_FONT_FACE;
				} else if (!CompareCaseInsensitive(p_buf, "-moz-document")) {
					main_substate = MAIN_SUBSTATE_IN_MEDIA_TOP_LEVEL;
				}
				sc.SetState(SCE_CSS_DEFAULT);
			}
			break;

		case SCE_CSS_CLASS:
			if (!IsAWordChar(ch)) {
				if (isLessDocument) {
					// Allow white-space before ( or ;
					int currentPos = sc.currentPos;
					char nextCh;
					for (; currentPos < finalLength; ++currentPos) {
						nextCh = styler.SafeGetCharAt(currentPos);
						if (strchr("(;", nextCh)) {
							sc.ChangeState(SCE_CSS_MIXIN);
							break;
						} else if (!strchr("\r\n\f \t", nextCh)) {
							break;
						}
					}
				}
				sc.SetState(SCE_CSS_DEFAULT);
			}
			break;

		case SCE_CSS_ID:
		case SCE_CSS_ATTRIBUTE:
		case SCE_CSS_PSEUDOELEMENT:
			if (!IsAWordChar(ch)) {
				sc.SetState(SCE_CSS_DEFAULT);
			}
			break;
		
		case SCE_CSS_IMPORTANT:
			if (IsAWordChar(ch)) {
				if (important_substate != IMPORTANT_SUBSTATE__IN_COMMENT) {
					if (important_substate == IMPORTANT_SUBSTATE__IN_WHITESPACE) {
						sc.ChangeState(SCE_CSS_DEFAULT);
						sc.SetState(SCE_CSS_IMPORTANT);
					}
					important_substate = IMPORTANT_SUBSTATE__IN_WORD;
				}
			} else if (important_substate == IMPORTANT_SUBSTATE__IN_WORD) {
				char s2[100], *p_buf = s2;
				int wordStart = styler.GetStartSegment();
				getCurrentWord(s2, sizeof(s2)/sizeof(s2[0]),
					       wordStart, sc.currentPos, styler);
				if (*p_buf == '!') {
					p_buf += 1;
				}
				if (!CompareCaseInsensitive(p_buf, "important")) {
					main_substate = MAIN_SUBSTATE_IN_PROPERTY_VALUE;
				} else {
					sc.ChangeState(SCE_CSS_VALUE);
				}
				sc.SetState(SCE_CSS_DEFAULT);
			} else if (strchr(" \t\r\n\f", ch)) {
				if (important_substate == IMPORTANT_SUBSTATE__AFTER_BANG) {
					sc.SetState(SCE_CSS_IMPORTANT);
				}
				important_substate = IMPORTANT_SUBSTATE__IN_WHITESPACE;
			} else if (sc.Match('/', '*')) {
				if (important_substate == IMPORTANT_SUBSTATE__AFTER_BANG) {
					sc.SetState(SCE_CSS_IMPORTANT);
					important_substate = IMPORTANT_SUBSTATE__IN_COMMENT;
				} else if (important_substate == IMPORTANT_SUBSTATE__IN_WHITESPACE) {
					sc.ChangeState(SCE_CSS_DEFAULT);
					sc.SetState(SCE_CSS_IMPORTANT);
					important_substate = IMPORTANT_SUBSTATE__IN_COMMENT;
				}
				sc.Forward();
			} else if (important_substate == IMPORTANT_SUBSTATE__IN_COMMENT
				   && sc.Match('*', '/')) {
				sc.Forward();
				sc.Forward();
				sc.ChangeState(SCE_CSS_COMMENT);
				sc.SetState(SCE_CSS_IMPORTANT);
				sc.currentPos -= 1; // because we'll go forward later.
				important_substate = IMPORTANT_SUBSTATE__AFTER_BANG;
			} else if (important_substate == IMPORTANT_SUBSTATE__AFTER_BANG) {
                // Give up.
                sc.SetState(SCE_CSS_DEFAULT);
                
            }
			break;
		
		case SCE_CSS_DOUBLESTRING:
		case SCE_CSS_SINGLESTRING:
			if (ch == '\\') {
				if (sc.Match('\r', '\n')) {
					if (sc.Match('\n')) {
						fillUnion(fdata, main_substate, nested_declaration_count,
							  important_substate, string_substate,
							  comment_substate, identifier_substate, sc.state);
						styler.SetLineState(lineCurrent, fdata.fn_data);
						lineCurrent += 1;
					}
					sc.Forward();
				}
				sc.Forward();
			} else if (ch == '\n'
				   || ch == '\r'
				   || ch == '\f') {
				sc.ChangeState(SCE_CSS_STRINGEOL);
				sc.SetState(SCE_CSS_DEFAULT);
				// No need to set line state inside a string
			} else if (ch ==
				   (sc.state == SCE_CSS_DOUBLESTRING ? '\"' : '\'')) {
				sc.Forward();
				sc.SetState(SCE_CSS_DEFAULT);
			}
			break;
		
		case SCE_CSS_NUMBER:
			if (!IsADigit(ch) && ch != '.') {
				if ((sc.MatchIgnoreCase("grad")
					 || sc.MatchIgnoreCase("dpcm")
					 || sc.MatchIgnoreCase("dppx")
					 || sc.MatchIgnoreCase("turn")
					 || sc.MatchIgnoreCase("vmin")
					 || sc.MatchIgnoreCase("vmax"))
					&& !IsAWordChar(styler.SafeGetCharAt(sc.currentPos + 4))) {
					sc.Forward();
					sc.Forward();
					sc.Forward();
					sc.ForwardSetState(SCE_CSS_DEFAULT);
				} else if ((sc.MatchIgnoreCase("deg")
					    || sc.MatchIgnoreCase("rad")
					    || sc.MatchIgnoreCase("rem")
					    || sc.MatchIgnoreCase("khz")
					    || sc.MatchIgnoreCase("dpi"))
					   && !IsAWordChar(styler.SafeGetCharAt(sc.currentPos + 3))) {
					sc.Forward();
					sc.Forward();
					sc.ForwardSetState(SCE_CSS_DEFAULT);
				} else if ((sc.MatchIgnoreCase("em")
					    || sc.MatchIgnoreCase("ex")
					    || sc.MatchIgnoreCase("px")
					    || sc.MatchIgnoreCase("ch")
					    || sc.MatchIgnoreCase("cm")
					    || sc.MatchIgnoreCase("mm")
					    || sc.MatchIgnoreCase("in")
					    || sc.MatchIgnoreCase("pt")
					    || sc.MatchIgnoreCase("pc")
					    || sc.MatchIgnoreCase("ms")
					    || sc.MatchIgnoreCase("ss")
					    || sc.MatchIgnoreCase("hz")
					    || sc.MatchIgnoreCase("vh")
					    || sc.MatchIgnoreCase("vw"))
					   && !IsAWordChar(styler.SafeGetCharAt(sc.currentPos + 2))) {
					sc.Forward();
					sc.ForwardSetState(SCE_CSS_DEFAULT);
				} else if ((ch == '%' || ch == 's' || ch == 'S')
					   && !IsAWordChar(sc.chNext)) {
					// MatchIgnoreCase fails with 1-char strings
					sc.ForwardSetState(SCE_CSS_DEFAULT);
				} else {
					sc.SetState(SCE_CSS_DEFAULT);
				}
			}
			break;
		
		case SCE_CSS_OPERATOR:
			sc.SetState(SCE_CSS_DEFAULT);
			break;
		
		case SCE_CSS_COMMENT:
			if (comment_substate == COMMENT_SUBSTATE_BLOCK
			    && sc.Match('*', '/')) {
				sc.Forward();
				sc.ForwardSetState(SCE_CSS_DEFAULT);
			} else if (comment_substate == COMMENT_SUBSTATE_LINE
				   && (ch == '\n' || ch == '\r')) {
				sc.SetState(SCE_CSS_DEFAULT);
			} else if (ch == '\n') {
				fillUnion(fdata, main_substate, nested_declaration_count,
					  important_substate, string_substate,
					  comment_substate, identifier_substate, sc.state);
				styler.SetLineState(lineCurrent, fdata.fn_data);
				lineCurrent += 1;
			}
			break;
		}

		// Now figure out where to go next.
		if (sc.state == SCE_CSS_DEFAULT) {
			// Be safe, and refresh this value.
			ch = sc.ch;
			if (isSassDocument) {
				if (ch == '\n') {
					sass_atStartOfLine = true;
					// In default state \n takes place of ';'
					if (main_substate == MAIN_SUBSTATE_SCSS_ASSIGNMENT) {
						main_substate = MAIN_SUBSTATE_AMBIGUOUS_SELECTOR_OR_PROPERTY_NAME;
					} else {
						main_substate = MAIN_SUBSTATE_TOP_LEVEL;
					}
				} else if (sass_atStartOfLine) {
					/**
					 * For Sass processing we don't need to look at anything
					 * but the current line's leading white-space.
					 * If there is no white-space, we must be at the top-level.
					 * Otherwise we're in an ambiguous spot.
					 */
					if (!strchr(" \t\r\n\f", ch)) {
						sass_atStartOfLine = (sc.currentPos ==
								      styler.LineStart(lineCurrent));
						main_substate = (sass_atStartOfLine
								 ? MAIN_SUBSTATE_TOP_LEVEL
								 : MAIN_SUBSTATE_AMBIGUOUS_SELECTOR_OR_PROPERTY_NAME);
						// And now we're past the leading white-space.
						sass_atStartOfLine = false;
					}
				}
			}
			// Get all the white space recognized in one spot.
			if (strchr(" \t\r\n\f", ch)) {
				if (ch == '\n') {
					fillUnion(fdata, main_substate, nested_declaration_count,
						  important_substate, string_substate,
						  comment_substate, identifier_substate, sc.state);
					styler.SetLineState(lineCurrent, fdata.fn_data);
					lineCurrent += 1;
				}
				continue;
			}
			switch (sc.ch) {
			case '!':
				if (main_substate == MAIN_SUBSTATE_IN_PROPERTY_VALUE) {
					sc.SetState(SCE_CSS_IMPORTANT);
					important_substate = IMPORTANT_SUBSTATE__AFTER_BANG;
				} else {
					sc.SetState(SCE_CSS_OPERATOR);
				}
				break;
			
			case '"':
				if (isLessDocument &&
				    string_substate == STRING_SUBSTATE__IN_LESS_CSS_ESCAPE) {
					// End of a ~"...." escape sequence
					sc.SetState(SCE_CSS_OPERATOR);
					string_substate = STRING_SUBSTATE__IN_STRING;
				} else {
					sc.SetState(SCE_CSS_DOUBLESTRING);
				}
				break;
	
			case '\'':
				sc.SetState(SCE_CSS_SINGLESTRING);
				break;
	
			case '#':
				if (main_substate == MAIN_SUBSTATE_IN_PROPERTY_VALUE
				    || main_substate == MAIN_SUBSTATE_SCSS_ASSIGNMENT) {
					sc.SetState(SCE_CSS_VALUE);
				} else {
					main_substate = MAIN_SUBSTATE_IN_SELECTOR;
					sc.SetState(SCE_CSS_OPERATOR);
					if (IsAWordChar(sc.chNext)) {
						sc.ForwardSetState(SCE_CSS_ID);
					}
				}
				break;
	
			case '$':
				if (isScssDocument) {
					identifier_substate = IDENTIFIER_SUBSTATE_SCSS_DOLLAR;
					if (main_substate == MAIN_SUBSTATE_TOP_LEVEL) {
						main_substate = MAIN_SUBSTATE_SCSS_ASSIGNMENT;
					}
					sc.SetState(SCE_CSS_IDENTIFIER);
					break;
				}
				// If we're still here, it's a CSS-3 selector, treat as operator
				sc.SetState(SCE_CSS_OPERATOR);
				break;
	
			case '.':
				if ((main_substate == MAIN_SUBSTATE_IN_PROPERTY_VALUE
				     || main_substate == MAIN_SUBSTATE_SCSS_ASSIGNMENT
				     || main_substate == MAIN_SUBSTATE_IN_MEDIA_TOP_LEVEL)
				    && IsADigit(sc.chNext)) {
					sc.SetState(SCE_CSS_NUMBER);
				} else {
					sc.SetState(SCE_CSS_OPERATOR);
					if ((main_substate == MAIN_SUBSTATE_TOP_LEVEL
					     || main_substate == MAIN_SUBSTATE_IN_SELECTOR
					     || main_substate == MAIN_SUBSTATE_AMBIGUOUS_SELECTOR_OR_PROPERTY_NAME)
					    && IsAWordChar(sc.chNext)) {
						sc.ForwardSetState(SCE_CSS_CLASS);
						main_substate = MAIN_SUBSTATE_IN_SELECTOR;
					}
				}
				break;
	
			case '&':
				if ((isLessDocument || isScssDocument)
				    && sc.chNext == ':'
				    && main_substate == MAIN_SUBSTATE_AMBIGUOUS_SELECTOR_OR_PROPERTY_NAME) {
					char next2Char = styler.SafeGetCharAt(sc.currentPos + 2);
					if (next2Char == ':' || IsAWordChar(next2Char)) {
						sc.SetState(SCE_CSS_OPERATOR);
						sc.Forward();
						if (next2Char == ':') {
							sc.ForwardSetState(SCE_CSS_PSEUDOELEMENT);
						} else {
							sc.ForwardSetState(SCE_CSS_PSEUDOCLASS);
						}
						main_substate = MAIN_SUBSTATE_IN_SELECTOR;
						break;
					}
				}
				// else fall through
			case '^': // Used in CSS3 selectors, and Less/SCSS
			case '|': // Used in CSS3 Namespaces extension
			case '%':
			case '*':
			case '+':
			case ',':
			case '<':
			case '=':
			case '>':
			case '?':
			case ']':
			case '(':
				sc.SetState(SCE_CSS_OPERATOR);
				break;
	
			case '/':
				if (sc.chNext == '*') {
					comment_substate = COMMENT_SUBSTATE_BLOCK;
					sc.SetState(SCE_CSS_COMMENT);
					sc.Forward();
				} else if ((isLessDocument || isScssDocument || isSassDocument) && sc.chNext == '/') {
					comment_substate = COMMENT_SUBSTATE_LINE;
					sc.SetState(SCE_CSS_COMMENT);
				} else {
					sc.SetState(SCE_CSS_OPERATOR);
				}
				break;
	
			case '{':
				nested_declaration_count += 1;
				if (main_substate == MAIN_SUBSTATE_AMBIGUOUS_SELECTOR_OR_PROPERTY_NAME) {
					// stay ambiguous, next level
				} else if (main_substate == MAIN_SUBSTATE_TOP_LEVEL
					   || main_substate == MAIN_SUBSTATE_IN_SELECTOR) {
					if (isLessDocument || isScssDocument) {
						main_substate = MAIN_SUBSTATE_AMBIGUOUS_SELECTOR_OR_PROPERTY_NAME;
					} else {
						main_substate = MAIN_SUBSTATE_IN_DECLARATION_NAME;
					}
				} else if (main_substate == MAIN_SUBSTATE_IN_FONT_FACE) {
					main_substate = MAIN_SUBSTATE_IN_DECLARATION_NAME;
				} else if (main_substate == MAIN_SUBSTATE_IN_PROPERTY_VALUE) {
					// Happens in @page blocks
					if (isScssDocument) {
					    // Nested property names with a common parent, like
					    // font: {
					    //    family: serif;
					    //    weight: bold; ...
					    // }
					    main_substate = MAIN_SUBSTATE_IN_DECLARATION_NAME;
					} else {
					    main_substate = MAIN_SUBSTATE_IN_SELECTOR;
					}
				} else if (main_substate == MAIN_SUBSTATE_IN_MEDIA_TOP_LEVEL) {
					main_substate = MAIN_SUBSTATE_IN_SELECTOR;
				}
				sc.SetState(SCE_CSS_OPERATOR);
				break;
	
			case ':':
				if ((IsAWordChar(sc.chNext) || sc.chNext == ':')
				    && (main_substate == MAIN_SUBSTATE_TOP_LEVEL
					|| main_substate == MAIN_SUBSTATE_IN_SELECTOR
					|| (main_substate == MAIN_SUBSTATE_AMBIGUOUS_SELECTOR_OR_PROPERTY_NAME
					    && followedByChars(sc.currentPos, finalLength, "{", ";}", styler)))) {
					sc.SetState(SCE_CSS_OPERATOR);
					if (sc.chNext == ':') {
						sc.Forward();
						sc.ForwardSetState(SCE_CSS_PSEUDOELEMENT);
					} else {
						sc.ForwardSetState(SCE_CSS_PSEUDOCLASS);
					}
					main_substate = MAIN_SUBSTATE_IN_SELECTOR;
				} else {
					// Ambig resolution isn't perfect here, chance it
					if (main_substate == MAIN_SUBSTATE_IN_DECLARATION_NAME
					    || main_substate == MAIN_SUBSTATE_AMBIGUOUS_SELECTOR_OR_PROPERTY_NAME) {
						main_substate = MAIN_SUBSTATE_IN_PROPERTY_VALUE;
					}
					// MAIN_SUBSTATE_SCSS_ASSIGNMENT: stay
					sc.SetState(SCE_CSS_OPERATOR);
				}
				break;
			
			case ';':
				// Always change to DECL NAME
				if (isScssDocument && main_substate == MAIN_SUBSTATE_SCSS_ASSIGNMENT) {
					main_substate = MAIN_SUBSTATE_TOP_LEVEL;
				} else if (isLessDocument || isScssDocument || isSassDocument) {
					main_substate = MAIN_SUBSTATE_AMBIGUOUS_SELECTOR_OR_PROPERTY_NAME;
				} else if (in_top_level_directive) {
					main_substate = MAIN_SUBSTATE_TOP_LEVEL;
					in_top_level_directive = false;
				} else {
					main_substate = MAIN_SUBSTATE_IN_DECLARATION_NAME;
				}
				sc.SetState(SCE_CSS_OPERATOR);
				break;
			
			case '@':
				sc.SetState(SCE_CSS_OPERATOR);
				if (IsAWordChar(sc.chNext)) {
					sc.ForwardSetState(SCE_CSS_DIRECTIVE);
				}
				break;
			
			case '[':
				if (main_substate == MAIN_SUBSTATE_IN_SELECTOR
				    || main_substate == MAIN_SUBSTATE_AMBIGUOUS_SELECTOR_OR_PROPERTY_NAME) {
					sc.SetState(SCE_CSS_OPERATOR);
					if (IsASpaceOrTab(sc.chNext)) {
						sc.ForwardSetState(SCE_CSS_DEFAULT);
						while (sc.More() && IsASpaceOrTab(sc.chNext)) {
							sc.Forward();
						}
					}
					if (IsSafeAlpha(sc.chNext)) {
						sc.ForwardSetState(SCE_CSS_ATTRIBUTE);
					}
					// otherwise it's just an operator.
				} else {
					sc.SetState(SCE_CSS_OPERATOR);
				}
				break;
			
			case '}':
				if (nested_declaration_count > 0) {
					nested_declaration_count -= 1;
				}
				// In CSS '}' always takes us to the top-level.
				main_substate = (((isLessDocument || isScssDocument)
						  && nested_declaration_count > 0)
						 ? MAIN_SUBSTATE_AMBIGUOUS_SELECTOR_OR_PROPERTY_NAME
						 : MAIN_SUBSTATE_TOP_LEVEL);
				sc.SetState(SCE_CSS_OPERATOR);
				break;
			
			case '~':
				sc.SetState(SCE_CSS_OPERATOR);
				if (isLessDocument && sc.chNext == '"') {
					sc.Forward();
					string_substate = STRING_SUBSTATE__IN_LESS_CSS_ESCAPE;
				}
				break;
			
			case '`':
				if (isLessDocument) {
					sc.SetState(SCE_CSS_OPERATOR);
				}
				break;
			
			case '-':
                if (main_substate == MAIN_SUBSTATE_IN_PROPERTY_VALUE || main_substate == MAIN_SUBSTATE_SCSS_ASSIGNMENT) {
					if (IsADigit(sc.chNext)) {
						sc.SetState(SCE_CSS_NUMBER);
					} else if (IsAWordChar(sc.chNext)) {
						sc.SetState(SCE_CSS_VALUE);
					} else {
						sc.SetState(SCE_CSS_OPERATOR);
					}
				} else if (isLessDocument
                           && (main_substate == MAIN_SUBSTATE_IN_SELECTOR
                               || main_substate == MAIN_SUBSTATE_AMBIGUOUS_SELECTOR_OR_PROPERTY_NAME)
                           && startsArg(sc.currentPos - 1, styler)
                           && IsADigit(sc.chNext)) {
                    sc.SetState(SCE_CSS_NUMBER);
                } else {
					sc.SetState(SCE_CSS_IDENTIFIER);
				}
				break;
			case ')':
					sc.SetState(SCE_CSS_OPERATOR);
				break;
			
			default:
				if (IsADigit(sc.ch)) {
				    sc.SetState(SCE_CSS_NUMBER);
				} else if (IsSafeAlpha(sc.ch)) {
					if (main_substate == MAIN_SUBSTATE_IN_PROPERTY_VALUE
					    || main_substate == MAIN_SUBSTATE_SCSS_ASSIGNMENT
					    || main_substate == MAIN_SUBSTATE_IN_MEDIA_TOP_LEVEL) {
						sc.SetState(SCE_CSS_VALUE);
					} else if (main_substate == MAIN_SUBSTATE_TOP_LEVEL) {
						main_substate = MAIN_SUBSTATE_IN_SELECTOR;
						sc.SetState(SCE_CSS_TAG);
					} else if (main_substate == MAIN_SUBSTATE_IN_SELECTOR) {
						sc.SetState(SCE_CSS_TAG);
					} else if (main_substate == MAIN_SUBSTATE_AMBIGUOUS_SELECTOR_OR_PROPERTY_NAME) {
						sc.SetState(SCE_CSS_TAG);
					} else {
						 sc.SetState(SCE_CSS_IDENTIFIER);
					}
				}
			}
		}
	}
	switch (sc.state) {
	case SCE_CSS_DOUBLESTRING:
	case SCE_CSS_SINGLESTRING:
		sc.ChangeState(SCE_CSS_STRINGEOL);
	}
	sc.Complete();
}

static bool isNonNegativeFoldingLevel(int level) {
	return ((level & SC_FOLDLEVELNUMBERMASK)
		& ~SC_FOLDLEVELBASE) > 0;
}

static void FoldCSSDoc(unsigned int startPos, int length, int, WordList *[], Accessor &styler) {
	bool foldComment = styler.GetPropertyInt("fold.comment") != 0;
	bool foldCompact = styler.GetPropertyInt("fold.compact", 1) != 0;
	unsigned int endPos = startPos + length;
	int visibleChars = 0;
	int lineCurrent = styler.GetLine(startPos);
	int levelPrev = (styler.LevelAt(lineCurrent) & SC_FOLDLEVELNUMBERMASK) | SC_FOLDLEVELBASE;
	int levelCurrent = levelPrev;
	char chNext = styler[startPos];
	bool inComment = (styler.StyleAt(startPos-1) == SCE_CSS_COMMENT);
	for (unsigned int i = startPos; i < endPos; i++) {
		char ch = chNext;
		chNext = styler.SafeGetCharAt(i + 1);
		int style = styler.StyleAt(i);
		bool atEOL = (ch == '\r' && chNext != '\n') || (ch == '\n');
		if (foldComment) {
			if (!inComment && (style == SCE_CSS_COMMENT))
				levelCurrent++;
			else if (inComment
				 && (style != SCE_CSS_COMMENT)
				 && isNonNegativeFoldingLevel(levelCurrent)) {
				levelCurrent--;
			}
			inComment = (style == SCE_CSS_COMMENT);
		}
		if (style == SCE_CSS_OPERATOR) {
			if (ch == '{') {
				levelCurrent++;
			} else if (ch == '}' && isNonNegativeFoldingLevel(levelCurrent)) {
				levelCurrent--;
			}
		}
		if (atEOL) {
			int lev = levelPrev;
			if (visibleChars == 0 && foldCompact)
				lev |= SC_FOLDLEVELWHITEFLAG;
			if ((levelCurrent > levelPrev) && (visibleChars > 0))
				lev |= SC_FOLDLEVELHEADERFLAG;
			if (lev != styler.LevelAt(lineCurrent)) {
				styler.SetLevel(lineCurrent, lev);
			}
			lineCurrent++;
			levelPrev = levelCurrent;
			visibleChars = 0;
		}
		if (!isspacechar(ch))
			visibleChars++;
	}
	// Fill in the real level of the next line, keeping the current flags as they will be filled in later
	int flagsNext = styler.LevelAt(lineCurrent) & ~SC_FOLDLEVELNUMBERMASK;
	styler.SetLevel(lineCurrent, levelPrev | flagsNext);
}

static const char * const cssWordListDesc[] = {
	"CSS1 Properties",
	"Pseudo-classes",
	"CSS2 Properties",
	"CSS3 Properties",
	"Pseudo-elements",
	"Browser-Specific CSS Properties",
	"Browser-Specific Pseudo-classes",
	"Browser-Specific Pseudo-elements",
	0
};

LexerModule lmCss(SCLEX_CSS, ColouriseCssDoc, "css", FoldCSSDoc, cssWordListDesc);

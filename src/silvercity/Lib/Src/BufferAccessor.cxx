// Copyright 2002 by Brian Quinlan <brian@sweetapp.com>
// The License.txt file describes the conditions under which this 
// software may be distributed.

#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdio.h>

#include <assert.h>

#include "ILexer.h"
#include "Scintilla.h"
#include "SciLexer.h"

#include "LexAccessor.h"
#include "Accessor.h"
#include "WordList.h"
#include "CharacterSet.h"
#include "LexerModule.h"

#include "SC_PropSet.h"
#include "Platform.h"
#if 0

#include "SVector.h"
#include "Accessor.h"
#include "Scintilla.h"
#endif

#include "BufferAccessor.h"
#include "LexState.h"

BufferAccessor::BufferAccessor(const char * charBuf_,
                               int bufLen_,
                               char * styleBuf_,
                               SC_PropSet &props_) : 
        props(props_), bufLen(bufLen_), charBuf(charBuf_), styleBuf(styleBuf_)
    
{
    char lstChar = 0;
    int i;
    //fprintf(stderr, "silvercity/Lib/Src/BufferAccessor.cxx: In BufferAccessor::BufferAccessor\n");

	dbcsCodePage = 0;
	tabInChars = 8;
    lv.Append(LineData(0, 0));
    for (i = 0; i < bufLen; ++i) {
        if (lstChar == 0x0d) {
            if (charBuf[i] == 0x0a) {
                // Wait until the next character
                continue;
            }
        }

        if ((lstChar == 0x0d) || (lstChar == 0x0a)) {
            lv.Append(LineData(i, 0));
        }
        lstChar = charBuf[i];
    }

    if ((lstChar == 0x0d) || (lstChar == 0x0a)) {
        lv.Append(LineData(i, 0));
    }
}

BufferAccessor::~BufferAccessor() {
}

bool BufferAccessor::InternalIsLeadByte(char ch) {
	if (SC_CP_UTF8 == codePage)
		// For lexing, all characters >= 0x80 are treated the
		// same so none is considered a lead byte.
		return false;
	else
		return Platform::IsDBCSLeadByte(codePage, ch);
}

int BufferAccessor::GetColumn(int position)
{
    return position - lv[LineFromPosition(position)].startPosition;
}

static bool IsTrailByte(int ch) {
	return (ch >= 0x80) && (ch < (0x80 + 0x40));
}

static int BytesFromLead(int leadByte) {
	if (leadByte > 0xF4) {
		// Characters longer than 4 bytes not possible in current UTF-8
		return 0;
	} else if (leadByte >= 0xF0) {
		return 4;
	} else if (leadByte >= 0xE0) {
		return 3;
	} else if (leadByte >= 0xC2) {
		return 2;
	}
	return 0;
}

bool BufferAccessor::InGoodUTF8(int pos, int &start, int &end) const {
	int lead = pos;
	while ((lead>0) && (pos-lead < 4) && IsTrailByte(static_cast<unsigned char>(charBuf[lead-1])))
		lead--;
	start = 0;
	if (lead > 0) {
		start = lead-1;
	}
	int leadByte = static_cast<unsigned char>(charBuf[start]);
	int bytes = BytesFromLead(leadByte);
	if (bytes == 0) {
		return false;
	} else {
		int trailBytes = bytes - 1;
		int len = pos - lead + 1;
		if (len > trailBytes)
			// pos too far from lead
			return false;
		// Check that there are enough trails for this lead
		int trail = pos + 1;
		while ((trail-lead<trailBytes) && (trail < Length())) {
			if (!IsTrailByte(static_cast<unsigned char>(charBuf[trail]))) {
				return false;
			}
			trail++;
		}
		end = start + bytes;
		return true;
	}
}


int BufferAccessor::NextPosition(int pos, int moveDir) const {
	// If out of range, just return minimum/maximum value.
	int increment = (moveDir > 0) ? 1 : -1;
	if (pos + increment <= 0)
		return 0;
	if (pos + increment >= Length())
		return Length();

	if (dbcsCodePage) {
		if (SC_CP_UTF8 == dbcsCodePage) {
			pos += increment;
			unsigned char ch = static_cast<unsigned char>(charBuf[pos]);
			int startUTF = pos;
			int endUTF = pos;
			if (IsTrailByte(ch) && InGoodUTF8(pos, startUTF, endUTF)) {
				// ch is a trail byte within a UTF-8 character
				if (moveDir > 0)
					pos = endUTF;
				else
					pos = startUTF;
			}
		} else {
			if (moveDir > 0) {
				int mbsize = IsDBCSLeadByte(charBuf[pos]) ? 2 : 1;
				pos += mbsize;
				if (pos > Length())
					pos = Length();
			} else {
				// Anchor DBCS calculations at start of line because start of line can
				// not be a DBCS trail byte.
				int posStartLine = LineStart(LineFromPosition(pos));
				// See http://msdn.microsoft.com/en-us/library/cc194792%28v=MSDN.10%29.aspx
				// http://msdn.microsoft.com/en-us/library/cc194790.aspx
				if ((pos - 1) <= posStartLine) {
					return pos - 1;
				} else if (IsDBCSLeadByte(charBuf[pos - 1])) {
					// Must actually be trail byte
					return pos - 2;
				} else {
					// Otherwise, step back until a non-lead-byte is found.
					int posTemp = pos - 1;
					while (posStartLine <= --posTemp && IsDBCSLeadByte(charBuf[posTemp]))
						;
					// Now posTemp+1 must point to the beginning of a character,
					// so figure out whether we went back an even or an odd
					// number of bytes and go back 1 or 2 bytes, respectively.
					return (pos - 1 - ((pos - posTemp) & 1));
				}
			}
		}
	} else {
		pos += increment;
	}

	return pos;
}


int BufferAccessor::GetLine(int position) {
    return LineFromPosition(position);
}

int SCI_METHOD BufferAccessor::LineStart(int line) const {
	if (line < 0)
		return 0;
	else if (line >= lv.GetNumLines())
		return Length();
	else
		return lv[line].startPosition;

    return 0;
}

int BufferAccessor::Length() const {
    //fprintf(stderr, ">>BufferAccessor.cxx: Length -> %d\n", bufLen);
	return bufLen;
}

int BufferAccessor::GetLineState(int line) const {

    return lv[line].lineState;
}

int BufferAccessor::SetLineState(int line, int state) {
	int stateOld = lv[line].lineState;
	lv[line].lineState = state;
	return stateOld;
}

int BufferAccessor::SetLineStateNoNotify(int line, int state) {
    // This is used for UDL and Scintilla to avoid editor repaints.
    // It's only here to provide SilverCity a compatible Scintilla interface
    return SetLineState(line, state);
}

int SCI_METHOD BufferAccessor::SetLevel(int line, int level) {
	if ((line >= 0) && (line < lv.GetNumLines())) {
        int prev = lv[line].level;
    	lv[line].level = level;
        return prev;
	}
    return 0;
}

int BufferAccessor::IndentAmount(int line, int *flags) {
	int end = Length();
	int spaceFlags = 0;

	// Determines the indentation level of the current line and also checks for consistent
	// indentation compared to the previous line.
	// Indentation is judged consistent when the indentation whitespace of each line lines
	// the same or the indentation of one line is a prefix of the other.

	int pos = LineStart(line);
	char ch = charBuf[pos];
	int indent = 0;
	bool inPrevPrefix = line > 0;
	int posPrev = inPrevPrefix ? LineStart(line-1) : 0;
	while ((ch == ' ' || ch == '\t') && (pos < end)) {
		if (inPrevPrefix) {
			char chPrev = charBuf[posPrev++];
			if (chPrev == ' ' || chPrev == '\t') {
				if (chPrev != ch)
					spaceFlags |= wsInconsistent;
			} else {
				inPrevPrefix = false;
			}
		}
		if (ch == ' ') {
			spaceFlags |= wsSpace;
			indent++;
		} else {	// Tab
			spaceFlags |= wsTab;
			if (spaceFlags & wsSpace)
				spaceFlags |= wsSpaceTab;
			indent = (indent / 8 + 1) * 8;
		}
		ch = charBuf[++pos];
	}

	*flags = spaceFlags;
	indent += SC_FOLDLEVELBASE;
	// if completely empty line or the start of a comment...
	//if ((ch == ' ' || ch == '\t' || ch == '\n' || ch == '\r') || 
		//(pfnIsCommentLeader && (*pfnIsCommentLeader)(charBuf, pos, end-pos)) )
		// return indent | SC_FOLDLEVELWHITEFLAG;
	//else
		return indent;
}

// Methods defined in IDocument that we have to implement.
void SCI_METHOD BufferAccessor::GetCharRange(char *buffer, int position, int lengthRetrieve) const {
    memcpy((void *) buffer, (void *) &charBuf[position], lengthRetrieve);
}

// Methods defined in IDocument, not used here

int SCI_METHOD BufferAccessor::Version() const {
    return dvOriginal;
}

void SCI_METHOD BufferAccessor::SetErrorStatus(int status) {
}

int SCI_METHOD BufferAccessor::LineFromPosition(int position) const {
	if (lv.GetNumLines() == 0)
		return 0;

    if (position >= lv[lv.GetNumLines() - 1].startPosition)
		return lv.GetNumLines() - 1;
	int lower = 0;
	int upper = lv.GetNumLines() - 1;
	do {
		int middle = (upper + lower + 1) / 2; 	// Round high
		if (position < lv[middle].startPosition) {
			upper = middle - 1;
		} else {
			lower = middle;
		}
	} while (lower < upper);

    return lower;
}

int SCI_METHOD BufferAccessor::GetLevel(int line) const {
	if ((line >= 0) && (line < lv.GetNumLines())) {
		return lv[line].level;
	} else {
		return SC_FOLDLEVELBASE;
	}
}

void SCI_METHOD BufferAccessor::StartStyling(int position, char mask) {
	stylingMask = mask;
	endStyled = position;
}

bool SCI_METHOD BufferAccessor::SetStyleFor(int length, char style) {
    style &= stylingMask;
    //fprintf(stderr, "BufferAccessor::SetStyleFor(%d-%d, style:%d\n",
    //        endStyled, endStyled + length, style);
    char *p_styleBuf = &styleBuf[endStyled];
    for (int i = 0; i < length; ++i) {
        *p_styleBuf++ = style;
    }
    endStyled += length;
    return true;
}

bool SCI_METHOD BufferAccessor::SetStyles(int length, const char *styles) {
    //fprintf(stderr, "BufferAccessor::SetStyles(length:%d), endStyled:%d\n", length, endStyled);
    //PLATFORM_ASSERT(endStyled + length <= Length());
    int bufLen = Length();
    if (length > bufLen - endStyled) {
        //TODO: Bug 91322: Why is this happening after moving to Scintilla 228?
        //fprintf(stderr, "Komodo: SilverCity: Assertion Failure: endStyled:%d, length:%d, Length():%d\n  expected: endStyled + length=%d < %d\n",
        //        endStyled, length, bufLen, endStyled + length, bufLen);
        //
        //I'd say the assertion is wrong.  Because we don't color styleBuf[bufLen],
        // but stop at bufLen - 1,  the "<" should have been "<="
        length = bufLen - endStyled;
    }
    //fprintf(stderr, "  Length(): %d\n", Length());
    //fprintf(stderr, "  styleBuf:%p\n", styleBuf);
    for (int iPos = 0; iPos < length; iPos++, endStyled++) {
        //fprintf(stderr, "    iPos: %d\n", iPos);
        //fprintf(stderr, "    style: %d\n", styles[iPos]);
        styleBuf[endStyled] = styles[iPos] & stylingMask;
    }
    return true;
}

char SCI_METHOD BufferAccessor::StyleAt(int position) const {
    return styleBuf[position];
}

void SCI_METHOD BufferAccessor::DecorationSetCurrentIndicator(int indicator) {
    // Not done by SilverCity
}

void SCI_METHOD BufferAccessor::DecorationFillRange(int position, int value, int fillLength) {
    // Not done by SilverCity
}

void SCI_METHOD BufferAccessor::ChangeLexerState(int start, int end) {
    // Not done by SilverCity
}

int SCI_METHOD BufferAccessor::CodePage() const {
	return dbcsCodePage;
}

bool SCI_METHOD BufferAccessor::IsDBCSLeadByte(char ch) const {
    // Copied from Document::IsDBCSLeadByte
	unsigned char uch = static_cast<unsigned char>(ch);
	switch (dbcsCodePage) {
		case 932:
			// Shift_jis
			return ((uch >= 0x81) && (uch <= 0x9F)) ||
				((uch >= 0xE0) && (uch <= 0xFC));
				// Lead bytes F0 to FC may be a Microsoft addition. 
		case 936:
			// GBK
			return (uch >= 0x81) && (uch <= 0xFE);
		case 949:
			// Korean Wansung KS C-5601-1987
			return (uch >= 0x81) && (uch <= 0xFE);
		case 950:
			// Big5
			return (uch >= 0x81) && (uch <= 0xFE);
		case 1361:
			// Korean Johab KS C-5601-1992
			return
				((uch >= 0x84) && (uch <= 0xD3)) ||
				((uch >= 0xD8) && (uch <= 0xDE)) ||
				((uch >= 0xE0) && (uch <= 0xF9));
	}
	return false;
}
const char * SCI_METHOD BufferAccessor::BufferPointer() {
    return charBuf;
}

static int NextTab(int pos, int tabSize) {
	return ((pos / tabSize) + 1) * tabSize;
}

int SCI_METHOD BufferAccessor::GetLineIndentation(int line) {
	int indent = 0;
	if ((line >= 0) && (line < lv.GetNumLines())) {
		int lineStart = LineStart(line);
		int length = Length();
		for (int i = lineStart; i < length; i++) {
			char ch = charBuf[i];
			if (ch == ' ')
				indent++;
			else if (ch == '\t')
				indent = NextTab(indent, tabInChars);
			else
				return indent;
		}
	}
	return indent;
}


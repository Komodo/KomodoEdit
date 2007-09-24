// Copyright 2002 by Brian Quinlan <brian@sweetapp.com>
// The License.txt file describes the conditions under which this 
// software may be distributed.

#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdio.h>

#include "Platform.h"

#include "PropSet.h"
#include "SVector.h"
#include "Accessor.h"
#include "BufferAccessor.h"
#include "Scintilla.h"

#include <assert.h>

BufferAccessor::BufferAccessor(const char * charBuf_,
                               int bufLen_,
                               char * styleBuf_,
                               PropSet &props_) : 
	Accessor(), props(props_), charBuf(charBuf_), bufLen(bufLen_), styleBuf(styleBuf_),
    chFlags(0), chWhile(0)
    
{
    char lstChar = 0;
    int i;

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

void BufferAccessor::Fill(int position) {
	startPos = position - slopSize;
	if (startPos + bufferSize > bufLen)
		startPos = bufLen - bufferSize;
	if (startPos < 0)
		startPos = 0;
	endPos = startPos + bufferSize;
	if (endPos > bufLen)
		endPos = bufLen;

    memcpy(buf, charBuf + startPos, endPos-startPos);
	buf[endPos-startPos] = '\0';
    
}

bool BufferAccessor::Match(int pos, const char *s)
{
	for (int i=0; *s; i++) {
		if (*s != SafeGetCharAt(pos+i))
			return false;
		s++;
	}
	return true;

}


char BufferAccessor::StyleAt(int position) {
	return styleBuf[position];
}

int BufferAccessor::GetLine(int pos) {
	if (lv.GetNumLines() == 0)
		return 0;

    if (pos >= lv[lv.GetNumLines() - 1].startPosition)
		return lv.GetNumLines() - 1;
	int lower = 0;
	int upper = lv.GetNumLines() - 1;
	do {
		int middle = (upper + lower + 1) / 2; 	// Round high
		if (pos < lv[middle].startPosition) {
			upper = middle - 1;
		} else {
			lower = middle;
		}
	} while (lower < upper);

    return lower;
}

int BufferAccessor::GetColumn(int position)
{
    return position - lv[GetLine(position)].startPosition;
}

int BufferAccessor::LineStart(int line) {
	if (line < 0)
		return 0;
	else if (line >= lv.GetNumLines())
		return Length();
	else
		return lv[line].startPosition;

    return 0;
}

int BufferAccessor::Length() {
	return bufLen;
}

int BufferAccessor::GetLineState(int line) {

    return lv[line].lineState;
}

int BufferAccessor::SetLineState(int line, int state) {
	int stateOld = lv[line].lineState;
	lv[line].lineState = state;
	return stateOld;
}

void BufferAccessor::StartAt(unsigned int start, char chMask) {
	stylingMask = chMask;
	endStyled = start;
}

void BufferAccessor::StartSegment(unsigned int pos) {
	startSeg = pos;
}

void BufferAccessor::ColourTo(unsigned int pos, int chAttr) {
	// Only perform styling if non empty range
    // XXX Is this supposed to happen this way? i.e. pos is
    // negative on first pass?!
	if (pos != startSeg - 1) {
		if (pos < startSeg) {
			Platform::DebugPrintf("Bad colour positions %d - %d\n", startSeg, pos);
        } else if (pos >= (unsigned int) bufLen) {
            pos = bufLen - 1;
            Platform::DebugPrintf("Colour position %d is >= buffer length %d\n", pos, bufLen);
		}

		if (chAttr != chWhile)
			chFlags = 0;
		chAttr |= chFlags;
		for (unsigned int i = startSeg; i <= pos; i++) {
		    styleBuf[i] = static_cast<char>(chAttr);
		}
	}
	startSeg = pos+1;
}

int BufferAccessor::LevelAt(int line) {
	if ((line >= 0) && (line < lv.GetNumLines())) {
		return lv[line].level;
	} else {
		return SC_FOLDLEVELBASE;
	}
}

void BufferAccessor::SetLevel(int line, int level) {
	if ((line >= 0) && (line < lv.GetNumLines())) {
    	lv[line].level = level;
	}
}


void BufferAccessor::Flush() {
}

int BufferAccessor::IndentAmount(int line, int *flags, PFNIsCommentLeader pfnIsCommentLeader) {
	int end = Length();
	int spaceFlags = 0;

	// Determines the indentation level of the current line and also checks for consistent
	// indentation compared to the previous line.
	// Indentation is judged consistent when the indentation whitespace of each line lines
	// the same or the indentation of one line is a prefix of the other.

	int pos = LineStart(line);
	char ch = (*this)[pos];
	int indent = 0;
	bool inPrevPrefix = line > 0;
	int posPrev = inPrevPrefix ? LineStart(line-1) : 0;
	while ((ch == ' ' || ch == '\t') && (pos < end)) {
		if (inPrevPrefix) {
			char chPrev = (*this)[posPrev++];
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
		ch = (*this)[++pos];
	}

	*flags = spaceFlags;
	indent += SC_FOLDLEVELBASE;
	// if completely empty line or the start of a comment...
	if ((ch == ' ' || ch == '\t' || ch == '\n' || ch == '\r') || 
		(pfnIsCommentLeader && (*pfnIsCommentLeader)(*this, pos, end-pos)) )
		return indent | SC_FOLDLEVELWHITEFLAG;
	else
		return indent;
}


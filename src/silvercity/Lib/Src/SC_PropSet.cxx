// SciTE - Scintilla based Text Editor
/** @file SC_PropSet.cxx
 ** A Java style properties file module.
 **/
// Copyright 1998-2003 by Neil Hodgson <neilh@scintilla.org>
// The License.txt file describes the conditions under which this software may be distributed.

// Forked from Scintilla because this class is now an
// internal class in Scintilla.

// Maintain a dictionary of properties

#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdio.h>
#include <assert.h>

#include "ILexer.h"
#include "Scintilla.h"
#include "SciLexer.h"

#include "WordList.h"
#include "LexAccessor.h"
#include "Accessor.h"
#include "StyleContext.h"
#include "CharacterSet.h"
#include "LexerModule.h"

#include "Platform.h"

#include "SC_PropSet.h"


// The comparison and case changing functions here assume ASCII
// or extended ASCII such as the normal Windows code page.

static inline bool IsLetter(char ch) {
	return ((ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z'));
}

inline bool IsASpace(unsigned int ch) {
    return (ch == ' ') || ((ch >= 0x09) && (ch <= 0x0d));
}

bool SC_EqualCaseInsensitive(const char *a, const char *b) {
	return 0 == CompareCaseInsensitive(a, b);
}

// Since the CaseInsensitive functions declared in SString
// are implemented here, I will for now put the non-inline
// implementations of the SString members here as well, so
// that I can quickly see what effect this has.

SString::SString(int i) : sizeGrowth(sizeGrowthDefault) {
	char number[32];
	sprintf(number, "%0d", i);
	s = StringAllocate(number);
	sSize = sLen = (s) ? strlen(s) : 0;
}

SString::SString(double d, int precision) : sizeGrowth(sizeGrowthDefault) {
	char number[32];
	sprintf(number, "%.*f", precision, d);
	s = StringAllocate(number);
	sSize = sLen = (s) ? strlen(s) : 0;
}

bool SString::grow(lenpos_t lenNew) {
	while (sizeGrowth * 6 < lenNew) {
		sizeGrowth *= 2;
	}
	char *sNew = new char[lenNew + sizeGrowth + 1];
	if (sNew) {
		if (s) {
			memcpy(sNew, s, sLen);
			delete []s;
		}
		s = sNew;
		s[sLen] = '\0';
		sSize = lenNew + sizeGrowth;
	}
	return sNew != 0;
}

SString &SString::assign(const char *sOther, lenpos_t sSize_) {
	if (!sOther) {
		sSize_ = 0;
	} else if (sSize_ == measure_length) {
		sSize_ = strlen(sOther);
	}
	if (sSize > 0 && sSize_ <= sSize) {	// Does not allocate new buffer if the current is big enough
		if (s && sSize_) {
			memcpy(s, sOther, sSize_);
		}
		s[sSize_] = '\0';
		sLen = sSize_;
	} else {
		delete []s;
		s = StringAllocate(sOther, sSize_);
		if (s) {
			sSize = sSize_;	// Allow buffer bigger than real string, thus providing space to grow
			sLen = sSize_;
		} else {
			sSize = sLen = 0;
		}
	}
	return *this;
}

bool SString::operator==(const SString &sOther) const {
	if ((s == 0) && (sOther.s == 0))
		return true;
	if ((s == 0) || (sOther.s == 0))
		return false;
	return strcmp(s, sOther.s) == 0;
}

bool SString::operator==(const char *sOther) const {
	if ((s == 0) && (sOther == 0))
		return true;
	if ((s == 0) || (sOther == 0))
		return false;
	return strcmp(s, sOther) == 0;
}

SString SString::substr(lenpos_t subPos, lenpos_t subLen) const {
	if (subPos >= sLen) {
		return SString();					// return a null string if start index is out of bounds
	}
	if ((subLen == measure_length) || (subPos + subLen > sLen)) {
		subLen = sLen - subPos;		// can't substr past end of source string
	}
	return SString(s, subPos, subPos + subLen);
}

SString &SString::lowercase(lenpos_t subPos, lenpos_t subLen) {
	if ((subLen == measure_length) || (subPos + subLen > sLen)) {
		subLen = sLen - subPos;		// don't apply past end of string
	}
	for (lenpos_t i = subPos; i < subPos + subLen; i++) {
		if (s[i] < 'A' || s[i] > 'Z')
			continue;
		else
			s[i] = static_cast<char>(s[i] - 'A' + 'a');
	}
	return *this;
}

SString &SString::uppercase(lenpos_t subPos, lenpos_t subLen) {
	if ((subLen == measure_length) || (subPos + subLen > sLen)) {
		subLen = sLen - subPos;		// don't apply past end of string
	}
	for (lenpos_t i = subPos; i < subPos + subLen; i++) {
		if (s[i] < 'a' || s[i] > 'z')
			continue;
		else
			s[i] = static_cast<char>(s[i] - 'a' + 'A');
	}
	return *this;
}

SString &SString::append(const char *sOther, lenpos_t sLenOther, char sep) {
	if (!sOther) {
		return *this;
	}
	if (sLenOther == measure_length) {
		sLenOther = strlen(sOther);
	}
	int lenSep = 0;
	if (sLen && sep) {	// Only add a separator if not empty
		lenSep = 1;
	}
	lenpos_t lenNew = sLen + sLenOther + lenSep;
	// Conservative about growing the buffer: don't do it, unless really needed
	if ((lenNew < sSize) || (grow(lenNew))) {
		if (lenSep) {
			s[sLen] = sep;
			sLen++;
		}
		memcpy(&s[sLen], sOther, sLenOther);
		sLen += sLenOther;
		s[sLen] = '\0';
	}
	return *this;
}

SString &SString::insert(lenpos_t pos, const char *sOther, lenpos_t sLenOther) {
	if (!sOther || pos > sLen) {
		return *this;
	}
	if (sLenOther == measure_length) {
		sLenOther = strlen(sOther);
	}
	lenpos_t lenNew = sLen + sLenOther;
	// Conservative about growing the buffer: don't do it, unless really needed
	if ((lenNew < sSize) || grow(lenNew)) {
		lenpos_t moveChars = sLen - pos + 1;
		for (lenpos_t i = moveChars; i > 0; i--) {
			s[pos + sLenOther + i - 1] = s[pos + i - 1];
		}
		memcpy(s + pos, sOther, sLenOther);
		sLen = lenNew;
	}
	return *this;
}

/**
 * Remove @a len characters from the @a pos position, included.
 * Characters at pos + len and beyond replace characters at pos.
 * If @a len is 0, or greater than the length of the string
 * starting at @a pos, the string is just truncated at @a pos.
 */
void SString::remove(lenpos_t pos, lenpos_t len) {
	if (pos >= sLen) {
		return;
	}
	if (len < 1 || pos + len >= sLen) {
		s[pos] = '\0';
		sLen = pos;
	} else {
		for (lenpos_t i = pos; i < sLen - len + 1; i++) {
			s[i] = s[i+len];
		}
		sLen -= len;
	}
}

bool SString::startswith(const char *prefix) {
	lenpos_t lenPrefix = strlen(prefix);
	if (lenPrefix > sLen) {
		return false;
	}
	return strncmp(s, prefix, lenPrefix) == 0;
}

bool SString::endswith(const char *suffix) {
	lenpos_t lenSuffix = strlen(suffix);
	if (lenSuffix > sLen) {
		return false;
	}
	return strncmp(s + sLen - lenSuffix, suffix, lenSuffix) == 0;
}

int SString::search(const char *sFind, lenpos_t start) const {
	if (start < sLen) {
		const char *sFound = strstr(s + start, sFind);
		if (sFound) {
			return sFound - s;
		}
	}
	return -1;
}

int SString::substitute(char chFind, char chReplace) {
	int c = 0;
	char *t = s;
	while (t) {
		t = strchr(t, chFind);
		if (t) {
			*t = chReplace;
			t++;
			c++;
		}
	}
	return c;
}

int SString::substitute(const char *sFind, const char *sReplace) {
	int c = 0;
	lenpos_t lenFind = strlen(sFind);
	lenpos_t lenReplace = strlen(sReplace);
	int posFound = search(sFind);
	while (posFound >= 0) {
		remove(posFound, lenFind);
		insert(posFound, sReplace, lenReplace);
		posFound = search(sFind, posFound + lenReplace);
		c++;
	}
	return c;
}

char *SContainer::StringAllocate(lenpos_t len) {
	if (len != measure_length) {
		return new char[len + 1];
	} else {
		return 0;
	}
}

char *SContainer::StringAllocate(const char *s, lenpos_t len) {
	if (s == 0) {
		return 0;
	}
	if (len == measure_length) {
		len = strlen(s);
	}
	char *sNew = new char[len + 1];
	if (sNew) {
		memcpy(sNew, s, len);
		sNew[len] = '\0';
	}
	return sNew;
}

// End SString functions

SC_PropSet::SC_PropSet() {
	for (int root = 0; root < hashRoots; root++)
		props[root] = 0;
}

SC_PropSet::~SC_PropSet() {
	Clear();
}

void SC_PropSet::Set(const char *key, const char *val, int lenKey, int lenVal) {
	if (!*key)	// Empty keys are not supported
		return;
	if (lenKey == -1)
		lenKey = static_cast<int>(strlen(key));
	if (lenVal == -1)
		lenVal = static_cast<int>(strlen(val));
	unsigned int hash = HashString(key, lenKey);
	for (SC_Property *p = props[hash % hashRoots]; p; p = p->next) {
		if ((hash == p->hash) &&
			((strlen(p->key) == static_cast<unsigned int>(lenKey)) &&
				(0 == strncmp(p->key, key, lenKey)))) {
			// Replace current value
			delete [](p->val);
			p->val = StringDup(val, lenVal);
			return;
		}
	}
	// Not found
	SC_Property *pNew = new SC_Property;
	if (pNew) {
		pNew->hash = hash;
		pNew->key = StringDup(key, lenKey);
		pNew->val = StringDup(val, lenVal);
		pNew->next = props[hash % hashRoots];
		props[hash % hashRoots] = pNew;
	}
}

void SC_PropSet::Set(const char *keyVal) {
	while (IsASpace(*keyVal))
		keyVal++;
	const char *endVal = keyVal;
	while (*endVal && (*endVal != '\n'))
		endVal++;
	const char *eqAt = strchr(keyVal, '=');
	if (eqAt) {
		Set(keyVal, eqAt + 1, eqAt-keyVal, endVal - eqAt - 1);
	} else if (*keyVal) {	// No '=' so assume '=1'
		Set(keyVal, "1", endVal-keyVal, 1);
	}
}

void SC_PropSet::Unset(const char *key, int lenKey) {
	if (!*key)	// Empty keys are not supported
		return;
	if (lenKey == -1)
		lenKey = static_cast<int>(strlen(key));
	unsigned int hash = HashString(key, lenKey);
	SC_Property *pPrev = NULL;
	for (SC_Property *p = props[hash % hashRoots]; p; p = p->next) {
		if ((hash == p->hash) &&
			((strlen(p->key) == static_cast<unsigned int>(lenKey)) &&
				(0 == strncmp(p->key, key, lenKey)))) {
			if (pPrev)
				pPrev->next = p->next;
			else
				props[hash % hashRoots] = p->next;
			if (p == enumnext)
				enumnext = p->next; // Not that anyone should mix enum and Set / Unset.
			delete [](p->key);
			delete [](p->val);
			delete p;
			return;
		} else {
			pPrev = p;
		}
	}
}

void SC_PropSet::SetMultiple(const char *s) {
	const char *eol = strchr(s, '\n');
	while (eol) {
		Set(s);
		s = eol + 1;
		eol = strchr(s, '\n');
	}
	Set(s);
}

SString SC_PropSet::Get(const char *key) const {
	unsigned int hash = HashString(key, strlen(key));
	for (SC_Property *p = props[hash % hashRoots]; p; p = p->next) {
		if ((hash == p->hash) && (0 == strcmp(p->key, key))) {
			return p->val;
		}
	}
    return "";
}

// There is some inconsistency between GetExpanded("foo") and Expand("$(foo)").
// A solution is to keep a stack of variables that have been expanded, so that
// recursive expansions can be skipped.  For now I'll just use the C++ stack
// for that, through a recursive function and a simple chain of pointers.

struct VarChain {
	VarChain(const char*var_=NULL, const VarChain *link_=NULL): var(var_), link(link_) {}

	bool contains(const char *testVar) const {
		return (var && (0 == strcmp(var, testVar)))
			|| (link && link->contains(testVar));
	}

	const char *var;
	const VarChain *link;
};

static int ExpandAllInPlace(const SC_PropSet &props, SString &withVars, int maxExpands, const VarChain &blankVars = VarChain()) {
	int varStart = withVars.search("$(");
	while ((varStart >= 0) && (maxExpands > 0)) {
		int varEnd = withVars.search(")", varStart+2);
		if (varEnd < 0) {
			break;
		}

		// For consistency, when we see '$(ab$(cde))', expand the inner variable first,
		// regardless whether there is actually a degenerate variable named 'ab$(cde'.
		int innerVarStart = withVars.search("$(", varStart+2);
		while ((innerVarStart > varStart) && (innerVarStart < varEnd)) {
			varStart = innerVarStart;
			innerVarStart = withVars.search("$(", varStart+2);
		}

		SString var(withVars.c_str(), varStart + 2, varEnd);
		SString val = props.Get(var.c_str());

		if (blankVars.contains(var.c_str())) {
			val.clear(); // treat blankVar as an empty string (e.g. to block self-reference)
		}

		if (--maxExpands >= 0) {
			maxExpands = ExpandAllInPlace(props, val, maxExpands, VarChain(var.c_str(), &blankVars));
		}

		withVars.remove(varStart, varEnd-varStart+1);
		withVars.insert(varStart, val.c_str(), val.length());

		varStart = withVars.search("$(");
	}

	return maxExpands;
}

SString SC_PropSet::GetExpanded(const char *key) const {
	SString val = Get(key);
	ExpandAllInPlace(*this, val, 100, VarChain(key));
	return val;
}

SString SC_PropSet::Expand(const char *withVars, int maxExpands) const {
	SString val = withVars;
	ExpandAllInPlace(*this, val, maxExpands);
	return val;
}
 
int SC_PropSet::GetInt(const char *key, int defaultValue) const {
	SString val = GetExpanded(key);
	if (val.length())
		return val.value();
	return defaultValue;
}

bool SC_isprefix(const char *target, const char *prefix) {
	while (*target && *prefix) {
		if (*target != *prefix)
			return false;
		target++;
		prefix++;
	}
	if (*prefix)
		return false;
	else
		return true;
}

void SC_PropSet::Clear() {
	for (int root = 0; root < hashRoots; root++) {
		SC_Property *p = props[root];
		while (p) {
			SC_Property *pNext = p->next;
			p->hash = 0;
			delete []p->key;
			p->key = 0;
			delete []p->val;
			p->val = 0;
			delete p;
			p = pNext;
		}
		props[root] = 0;
	}
}

char *SC_PropSet::ToString() const {
	size_t len=0;
	for (int r = 0; r < hashRoots; r++) {
		for (SC_Property *p = props[r]; p; p = p->next) {
			len += strlen(p->key) + 1;
			len += strlen(p->val) + 1;
		}
	}
	if (len == 0)
		len = 1;	// Return as empty string
	char *ret = new char [len];
	if (ret) {
		char *w = ret;
		for (int root = 0; root < hashRoots; root++) {
			for (SC_Property *p = props[root]; p; p = p->next) {
				strcpy(w, p->key);
				w += strlen(p->key);
				*w++ = '=';
				strcpy(w, p->val);
				w += strlen(p->val);
				*w++ = '\n';
			}
		}
		ret[len-1] = '\0';
	}
	return ret;
}

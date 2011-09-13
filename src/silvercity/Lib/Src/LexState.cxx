// Stuff from Scintilla
/** @file LexState.cxx
 **/
// Copyright (C) 2000-2011 by ActiveState Software Inc.
// The License.txt file describes the conditions under which this software may be distributed.

#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdio.h>
#include <assert.h>

#include "ILexer.h"
#include "SciLexer.h"
#include "WordList.h"
#include "LexerModule.h"

#include <BufferAccessor.h>
#include "Catalogue.h"

#include "LexState.h"

LexState::LexState() : pAccess(0), instance(0) {
	lexCurrent = 0;
	lexLanguage = SCLEX_CONTAINER;
}

void LexState::Colourise() {
    int bufLen = pAccess->Length();
    if (bufLen > 0) {
        instance->Lex(0, bufLen, 0, pAccess);
    }
}

void LexState::SetDocument(BufferAccessor *pdoc_) {
    pAccess = pdoc_;
}

LexState::~LexState() {
	if (instance) {
		instance->Release();
		instance = 0;
	}
}

void LexState::SetLexer(int lexLanguage) {
	if (lexLanguage == SCLEX_CONTAINER) {
		SetLexerModule(0);
	} else {
		const LexerModule *lex = Catalogue::Find(lexLanguage);
		if (!lex)
			lex = Catalogue::Find(SCLEX_NULL);
		SetLexerModule(lex);
	}
}

void LexState::SetLexerLanguage(const char *languageName) {
	const LexerModule *lex = Catalogue::Find(languageName);
	if (!lex)
		lex = Catalogue::Find(SCLEX_NULL);
	if (lex)
		lexLanguage = lex->GetLanguage();
	SetLexerModule(lex);
}

void LexState::SetLexerModule(const LexerModule *lex) {
	if (lex != lexCurrent) {
		if (instance) {
			instance->Release();
			instance = 0;
		}
		lexCurrent = lex;
		if (lexCurrent) {
			instance = lexCurrent->Create();
            // Pointer to either a LexerSimple or an ILexer object
        }
	}
}

const char *LexState::DescribeWordListSets() {
	if (instance) {
		return instance->DescribeWordListSets();
	} else {
		return 0;
	}
}

void LexState::SetWordList(int n, const char *wl) {
	if (instance) {
		instance->WordListSet(n, wl);
	}
}

int LexState::GetStyleBitsNeeded() const {
    // Not implemented.
    return 0;
}

const char *LexState::GetName() const {
	return lexCurrent ? lexCurrent->languageName : "";
}

void *LexState::PrivateCall(int operation, void *pointer) {
    // Not implemented.
    return 0;
}

const char *LexState::PropertyNames() {
	if (instance) {
		return instance->PropertyNames();
	} else {
		return 0;
	}
}

int LexState::PropertyType(const char *name) {
	if (instance) {
		return instance->PropertyType(name);
	} else {
		return SC_TYPE_BOOLEAN;
	}
}

const char *LexState::DescribeProperty(const char *name) {
	if (instance) {
		return instance->DescribeProperty(name);
	} else {
		return 0;
	}
}

void LexState::PropSet(const char *key, const char *val) {
	props.Set(key, val);
	if (instance) {
		instance->PropertySet(key, val);
	}
}

const char *LexState::PropGet(const char *key) const {
	return props.Get(key);
}

int LexState::PropGetInt(const char *key, int defaultValue) const {
	return props.GetInt(key, defaultValue);
}

int LexState::PropGetExpanded(const char *key, char *result) const {
	return props.GetExpanded(key, result);
}


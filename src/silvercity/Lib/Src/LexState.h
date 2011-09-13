// Scintilla source code edit control
/** @file LexState.h
 **/
// Copyright (C) 2000-2011 by ActiveState Software Inc.
// The License.txt file describes the conditions under which this software may be distributed.

#ifndef LEXSTATE_H
#define LEXSTATE_H

#include "ILexer.h"

class BufferAccessor;
class LexerModule;
#include "PropSetSimple.h"

class LexState {
	PropSetSimple props;
	BufferAccessor *pAccess;
	ILexer *instance;
public:
	const LexerModule *lexCurrent;
	int lexLanguage;

	LexState();
    void SetDocument(BufferAccessor *pdoc_);
	void Colourise();

	virtual ~LexState();
	void SetLexer(int lexerID);
	void SetLexerLanguage(const char *languageName);
	void SetLexerModule(const LexerModule *lex);
	const char *DescribeWordListSets();
	void SetWordList(int n, const char *wl);
	int GetStyleBitsNeeded() const;
	const char *GetName() const;
	void *PrivateCall(int operation, void *pointer);
	const char *PropertyNames();
	int PropertyType(const char *name);
	const char *DescribeProperty(const char *name);
	void PropSet(const char *key, const char *val);
	const char *PropGet(const char *key) const;
	int PropGetInt(const char *key, int defaultValue=0) const;
	int PropGetExpanded(const char *key, char *result) const;
};


#endif /* LEXSTATE_H */

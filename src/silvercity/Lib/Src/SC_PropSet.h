// Scintilla source code edit control
/** @file SC_PropSet.h
 ** A Java style properties file module.
 **/
// Copyright 1998-2002 by Neil Hodgson <neilh@scintilla.org>
// The License.txt file describes the conditions under which this software may be distributed.

// Forked from Scintilla because this class is now an
// internal class in Scintilla.

#ifndef SC_PROPSET_H
#define SC_PROPSET_H
#include "SC_SString.h"
#define SString SC_SString // for transition to scintilla v228

bool SC_EqualCaseInsensitive(const char *a, const char *b);

bool SC_isprefix(const char *target, const char *prefix);

struct SC_Property {
	unsigned int hash;
	char *key;
	char *val;
	SC_Property *next;
	SC_Property() : hash(0), key(0), val(0), next(0) {}
};

/**
 */
class SC_PropSet {
protected:
	enum { hashRoots=31 };
	SC_Property *props[hashRoots];
	SC_Property *enumnext;
	int enumhash;
	static unsigned int HashString(const char *s, size_t len) {
		unsigned int ret = 0;
		while (len--) {
			ret <<= 4;
			ret ^= *s;
			s++;
		}
		return ret;
	}

public:
	SC_PropSet();
	~SC_PropSet();
	void Set(const char *key, const char *val, int lenKey=-1, int lenVal=-1);
	void Set(const char *keyVal);
	void Unset(const char *key, int lenKey=-1);
	void SetMultiple(const char *s);
	SString Get(const char *key) const;
	SString GetExpanded(const char *key) const;
	SString Expand(const char *withVars, int maxExpands=100) const;
	int GetInt(const char *key, int defaultValue=0) const;
	void Clear();
	char *ToString() const;	// Caller must delete[] the return value

private:
	// copy-value semantics not implemented
	SC_PropSet(const SC_PropSet &copy);
	void operator=(const SC_PropSet &assign);
};

inline bool SC_IsAlphabetic(unsigned int ch) {
	return ((ch >= 'A') && (ch <= 'Z')) || ((ch >= 'a') && (ch <= 'z'));
}


#ifdef _MSC_VER
// Visual C++ doesn't like the private copy idiom for disabling
// the default copy constructor and operator=, but it's fine.
#pragma warning(disable: 4511 4512)
#endif

#endif

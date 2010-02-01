// Copyright 2002 by Brian Quinlan <brian@sweetapp.com>
// The License.txt file describes the conditions under which this 
// software may be distributed.

#ifndef PYPROPSET_H_
#define PYPROPSET_H_

#include <Python.h>

#include <SC_PropSet.h>

extern PyTypeObject PyPropSetType;

class PropSetEx : public SC_PropSet {
public:
    bool GetFirst(char **key, char **val) {
	for (int i = 0; i < hashRoots; i++) {
		for (SC_Property *p = props[i]; p; p = p->next) {
			if (p) {
				*key = p->key;
				*val = p->val;
				enumnext = p->next; // GetNext will begin here ...
				enumhash = i;		  // ... in this block
				return true;
			}
		}
	}
	return false;
    }

    /**
     * Continue enumeration.
     */
    bool GetNext(char ** key, char ** val) {
	bool firstloop = true;

	// search begins where we left it : in enumhash block
	for (int i = enumhash; i < hashRoots; i++) {
		if (!firstloop)
			enumnext = props[i]; // Begin with first property in block
		// else : begin where we left
		firstloop = false;

		for (SC_Property *p = enumnext; p; p = p->next) {
			if (p) {
				*key = p->key;
				*val = p->val;
				enumnext = p->next; // for GetNext
				enumhash = i;
				return true;
			}
		}
	}
	return false;
    }

};

typedef struct {
    PyObject_HEAD
    PropSetEx * propSet;
} PyPropSet;

#define PyPropSet_Check(op) ((op)->ob_type == &PyPropSetType)
#define PyPropSet_GET_PROPSET(op) (((PyPropSet *)(op))->propSet)

PyObject*
PyPropSet_new(PyObject *, PyObject* args);

void
initPyPropSet(void);

#endif // PYPROPSET_H_

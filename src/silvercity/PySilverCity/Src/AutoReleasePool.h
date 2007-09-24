// Copyright 2002 by Brian Quinlan <brian@sweetapp.com>
// The License.txt file describes the conditions under which this 
// software may be distributed.

#ifndef AUTORELEASEPOOL_H_
#define AUTORELEASEPOOL_H_

#include <Python.h>

class AutoReleasePool
{
public:
    AutoReleasePool(void) 
    {
        first = NULL;
    }

    void add(PyObject * obj)
    {
        Node * node = new Node();

        node->content = obj;
        node->next = first;

        first = node;
    }

    ~AutoReleasePool()
    {
        Node * node = first;

        while (node != NULL)
        {
            Node * save = node;
            
            Py_XDECREF(node->content);
            node = node->next;
            delete save;
        }
    }

protected:
    typedef struct Node {
        PyObject *      content;
        struct Node *   next;
    } Node;

    Node * first;

private:
    AutoReleasePool(AutoReleasePool &);
    AutoReleasePool& operator=(AutoReleasePool &);
};

#endif
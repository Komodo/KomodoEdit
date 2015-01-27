        /* initialize scandir types */
        if (PyType_Ready(&ScandirIteratorType) < 0)
            return NULL;
        if (PyType_Ready(&DirEntryType) < 0)
            return NULL;

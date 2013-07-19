Note that the patches here must be replicated in the XPCOM completion code, in
src/codeintel/src/komodo/xpcomJSElements.py.  This is necessary because it is
not possible to inherit from ciElementTree.Element, therefore an equivalent pure
Python version is needed.  See bug 99286.

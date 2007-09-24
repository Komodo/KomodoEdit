# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# this is an xpcom wrapper for URIlib

from xpcom import components, nsError, ServerException, COMException

from URIlib import *

#class koFileEx(object):
class koFileEx:
    _com_interfaces_ = [components.interfaces.koIFileEx]
    _reg_desc_ = "Komodo File Component"
    _reg_contractid_ = "@activestate.com/koFileEx;1"
    _reg_clsid_ = "{998EE000-28EA-4A01-B02D-56CE44AC096D}"

    def __init__(self):
        self.__dict__['_URI'] = URIParser()
        self.__dict__['_handler'] = None

    def __get_handler(self):
        handler = self._handler
        if handler is None and self._URI.scheme:
            if self._URI.scheme == 'file':
                handler = FileHandler(self._URI.path)

            elif self._URI.scheme in RemoteURISchemeTypes: # Imported from URIlib
                handler = RemoteURIHandler(self._URI.URI)

            # XXX TODO we don't really need this now, can use the below
            # chrome handler
            elif self._URI.URI == "chrome://komodo/content/startpage/startpage.xml#view-startpage":
                handler = StartPageHandler(self._URI.URI)

            elif self._URI.scheme in ['chrome','dbgp']:
                # pass through to mozilla's uri handling
                handler = xpURIHandler(self._URI.URI)

            elif self._URI.scheme in ['macro','snippet']:
                handler = projectURIHandler(self._URI)

            else:
                handler = URIHandler(self._URI.URI)

            self.__dict__['_handler'] = handler
        return handler

    def __getattr__(self, attr):
        # Shortcut for internals.
        if attr.startswith("_"):
            # need to allow pyxpcom to get the
            # interface attributes
            if hasattr(koFileEx, attr):
                return getattr(self,attr)
            raise AttributeError, attr
        handler = self.__get_handler()
        if handler is not None and hasattr(handler, attr):
            return getattr(handler, attr)
        if self._URI is not None and hasattr(self._URI, attr):
            return getattr(self._URI, attr)
        raise AttributeError, attr
  
    def __setattr__(self,name,value):
        handler = self.__get_handler()
        set_self = 1
        if handler is not None and hasattr(handler,name):
            setattr(handler,name,value)
            set_self = 0
        if self._URI is not None and hasattr(self._URI,name):
            setattr(self._URI,name,value)
            set_self = 0
        if set_self:
            self.__dict__[name] = value

    # Leave this as an xpcom "getter" - or we could just special
    # case it in __getattr__.
    def get_URI(self):
        return self._URI.URI
        
    def puts(self, text):
        self.write(text)

    def readfile(self):
        return self.read(-1)

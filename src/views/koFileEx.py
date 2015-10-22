# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

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
        if handler is None:
            scheme = self._URI.scheme
            if not scheme:
                return None

            if scheme == 'file':
                handler = FileHandler(self._URI.path)

            elif scheme in RemoteURISchemeTypes: # Imported from URIlib
                handler = RemoteURIHandler(self._URI.URI)
                
            elif self._URI.URI == "chrome://komodo/content/quickstart.xml#view-quickstart":
                handler = QuickstartHandler(self._URI.URI)

            elif scheme in ['chrome', 'dbgp']:
                # pass through to mozilla's uri handling
                handler = xpURIHandler(self._URI.URI)

            elif scheme in ['macro', 'snippet']:
                handler = projectURIHandler(self._URI)

            elif scheme in ['macro2', 'snippet2']:
                handler = projectURI2_Handler(self._URI)

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
        if handler is not None:
            # XXX - This is hack to avoid updating the stats via 'hasChanged',
            #       as the hasattr(handler, 'hasChanged') will actually update
            #       stat information inadvertently, causing the getattr to then
            #       always return False (no file change). See bug:
            #       http://bugs.activestate.com/show_bug.cgi?id=73435
            if hasattr(handler.__class__, attr) or hasattr(handler, attr):
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

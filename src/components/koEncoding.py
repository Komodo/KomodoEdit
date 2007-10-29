#!python
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

from xpcom import components

class koEncoding:
    _com_interfaces_ = [components.interfaces.koIEncoding]
    _reg_desc_ = "Encoding Service"
    _reg_clsid_ = "{760875e5-c732-4f85-9440-a4f8e8e58824}"
    _reg_contractid_ = "@activestate.com/koEncoding;1"

    def __init__(self):
        self.encodingServices = components.classes['@activestate.com/koEncodingServices;1'].\
            getService(components.interfaces.koIEncodingServices)
        self.use_byte_order_marker = 0
        self.python_encoding_name = ''
    
    def _setToDefaultEncoding(self):
        self._globalPrefs = components.classes["@activestate.com/koPrefService;1"].\
                            getService(components.interfaces.koIPrefService).prefs
        encoding_name = self._globalPrefs.getStringPref('encodingDefault')
        self.python_encoding_name = self.encodingServices.\
                        get_encoding_info(encoding_name).\
                        python_encoding_name.lower()
    
    def set_python_encoding_name(self, value):
        if value == 'Default Encoding':
            self._setToDefaultEncoding()
        else:
            self.python_encoding_name = value.lower()
        
    def get_friendly_encoding_name(self):               
        return self.encodingServices.get_encoding_info(self.python_encoding_name).friendly_encoding_name        

    def get_short_encoding_name(self):               
        return self.encodingServices.get_encoding_info(self.python_encoding_name).short_encoding_name        
        
    def get_encoding_info(self):
        return self.encodingServices.get_encoding_info(self.python_encoding_name) 
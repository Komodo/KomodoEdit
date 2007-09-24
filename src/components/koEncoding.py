#!python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

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
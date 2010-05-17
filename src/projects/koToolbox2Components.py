#!/usr/bin/env python
# Copyright (c) 2010 ActiveState
# See the file LICENSE.txt for licensing information.

"""KoToolboxDatabaseService - A service for
accessing the new toolbox service.
"""

import json
import os
import os.path
import re
import sys
import logging
from xpcom import components, COMException, ServerException, nsError
import koToolbox2

# This is just a singleton for access to the database.
# Python-side code is expected to unwrap the object to get
# at the underlying database object, while
# JS-side code will have to go through the interface.

class KoToolboxDatabaseService:
    _com_interfaces_ = [components.interfaces.koIToolboxDatabaseService]
    _reg_clsid_ = "{a68427e7-9180-40b3-89ad-91440714dede}"
    _reg_contractid_ = "@activestate.com/KoToolboxDatabaseService;1"
    _reg_desc_ = "Access the toolbox database"
    
    db = None
    toolManager = None
    def initialize(self, db_path):
        self.db = koToolbox2.Database(db_path)
        
    def terminate(self):
        self.db = self.toolManager = None
    
    # Python-side methods only:
    
    def getToolById(self, id):
        return self.toolManager.getToolById(id)    
    
    def __getattr__(self, attr):
        return getattr(self.db, attr)
        
        

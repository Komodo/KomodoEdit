#!/usr/bin/env python
# In order to create and use Python COM components, you must have the
# Python Win32 extensions.  If you are using ActivePython
# (http://www.activestate.com/activepython) then you already
# have them.  If you are using another Python distribution you can get
# these extensions here:
#   http://starship.python.net/crew/mhammond/win32/

import win32com.client

myObject = win32com.client.Dispatch("MyName.MyComponent")
myObject.myMethod('test')
myObject.myAttribute1 = 'New value'


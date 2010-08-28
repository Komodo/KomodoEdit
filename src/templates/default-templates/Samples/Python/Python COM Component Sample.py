#!/usr/bin/env python
# In order to create and use Python COM components, you must have the
# Python Win32 extensions.  If you are using ActivePython
# (http://www.activestate.com/activepython) then you already
# have them.  If you are using another Python distribution you can get
# these extensions here:
#   http://starship.python.net/crew/mhammond/win32/

class MyComponent:
    _reg_clsid_ = '{[[%guid]]}'
    _reg_desc_ = 'MyComponent Server'
    _reg_progid_ = 'MyName.MyComponent'

    _public_methods_ = ['myMethod']
    _public_attrs_ = ['myAttribute1', 'myAttribute2']
    _readonly_attrs_ = ['myAttribute2']

    def __init__(self):
        self.myAttribute1 = 'Some value'
        self.myAttribute2 = "Can't touch this"
        
    def myMethod(self, *myArgs):
        return 'myMethod called with arguments:' + repr(myArgs)


if __name__ == '__main__':
    import win32com.server.register 
    win32com.server.register.UseCommandLine(MyComponent)


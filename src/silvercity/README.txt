This is SilverCity
==================

Copyright (c) 2002 Brian Quinlan.
All rights reserved.

License information
-------------------

See the file "LICENSE.txt" for information on the history of this
software, terms & conditions for usage, and a DISCLAIMER OF ALL
WARRANTIES.

This distribution contains no GNU General Public Licensed
(GPLed) code so it may be used in proprietary projects.

All trademarks referenced herein are property of their respective
holders.

What is SilverCity?
-------------------

SilverCity is a lexing package, based on Scintilla, that can provide 
lexical analysis for over 20 programming and markup langauges. 

SilverCity can be used as a C++ library and also has scripting language
bindings for Python.


How do I use SilverCity?
------------------------

Documentation for SilverCity is available at:
http://silvercity.sourceforge.net/


Bug reports
-----------

To report or search for bugs, please use the Bug
https://sourceforge.net/tracker/?group_id=45693&atid=443739.


Patches and contributions
-------------------------

To submit a patch or other contribution, please use the Patch
Manager at https://sourceforge.net/tracker/?group_id=45693&atid=443741.


Build instructions
==================

In order to build any of the SilverCity components, scintilla
must be in the SilverCity directory i.e.:

/silvercity
	CSS
	Lib
	MANIFEST.IN
	...
	scintilla/
		bin/
		...
		zipsrc.bat
	...

To build SilverCity as a standalone library on Windows, use the
project file:
SilverCity/Lib/PCBuild/SilverCityLib.dsw

To build SilverCity as a Python extension, use the Distutils 
setup script:
SilverCity/setup.py

Contributions are welcome for a build system for the standalone
library on UNIX and for bindings to other languages.


Testing
-------

There is a simple test suite for the Python extension:
SilverCity/PySilverCity/Scripts/test.py

 - Brian Quinlan (brian@sweetapp.com)

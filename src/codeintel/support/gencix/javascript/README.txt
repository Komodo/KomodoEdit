README for codeintel javascript standard library CIX generation
===============================================================


Overview
--------

Todd found an XML file describing the JavaScript standard library. This xml
file (it is beleived) was generated from a website scrape... ahhh the hacks...
http://bluefish.clansco.org/ref/bflib_ECMAScript.xml

The XML file is translated using a XSL transformation (XSLT) to a codeintel
format and then it's tweaked by the python script to update certain elements.

Alternatives doc sources might be:

* Michael A Nachbaur, see:
  http://cvs.nachbaur.com/cgi-bin/viewcvs.cgi/MozillaAOMReference/
* Scraping from Mozilla JavaScript 1.5 reference:
  http://developer.mozilla.org/en/docs/Core_JavaScript_1.5_Reference

Dom
---

http://www.w3.org/DOM/

DOM Level 0
===========

This is generally what the host environment (browser) defines to support
the Javascript DOM environment. This is not actually a specification, but each
browser (firefox, ie, opera...) generally supplies the same functions. I.e.

* window (global object, does not need to be prefixed)
* window.document (information about the current page)
* window.navigator (which contains userAgent, plugins, javaEnabled, etc...)

DOM Level 1
===========

First specification of the DOM, used by some older programs and browsers.

http://www.w3.org/DOM/DOMTR#dom1

DOM Level 2
===========

Second specification of the DOM, supported and used by most browsers today.

http://www.w3.org/DOM/DOMTR#dom2

DOM Level 3
===========

Third specification of the DOM, this is mostly still a working draft, and as
such there is not a lot of support for DOM Level 3 as yet.

http://www.w3.org/DOM/DOMTR#dom3


Requirements for building
-------------------------

The following python modules are required:

* libxml2
* libxslt
* elementtree (or cElementTree)
* BeautifulSoup


Building
--------

ECMAScript (JavaScript)
=======================

1. python ecmaToCodeintel.py

This produces a file named javascript.cix, which can then be copied to the
appropriate directory (i.e. lib/codeintel2/stdlibs/).

DOM0
====

1. python dom0_to_cix.py

This produces a file named dom0.cix.

DOM1
====

1. python dom1_to_cix.py

This produces a file named dom1.cix.

DOM2
====

1. python dom2_to_cix.py

This produces a file named dom2.cix.

DOM3
====

Note: This is work in progess...

1. python dom3_to_cix.py

This produces a file named dom3.cix.


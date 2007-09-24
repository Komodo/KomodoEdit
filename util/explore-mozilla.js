/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */


/* these things don't work in mozilla.  -- they're from the rhino book */
function funcname(f) {
  var s = f.toString().match(/function (\w*)/)[0];
  if (s == null || s.length == 0) return "anonymous";
  return s;
}

function stacktrace(n) {
  var s = "";
  for (var a = arguments.caller; --n != 0 && a; a = a.caller) {
    s += funcname(a.callee) + "\n";
    if (a.caller == a) break;
  }
  return s;
}

/* end things that don't work */

/* Find ProgIDs with the given regular expression */
function findComp(re) {
    var regExp = new RegExp(re, 'i');
    for (var el in Components.classes)
        if (el.search(regExp) > -1) dump(el + "\n");
}
 
/* List all interfaces supported by a given component */
function findInterfaces(obj) {
    for (var el in Components.interfaces) {
    try {
    obj.QueryInterface(Components.interfaces[el]);
    dump(el + "\n"); 
} catch(e) {}
    }
}

function reverseLookup(iface) {
  var found = 0;
  var components = new Array();
  var foo;

  for (var el in Components.classes) {
     dump ("looking up class " + el + "\n");
     if (el.indexOf("@mozilla") != 0) {
	continue;
     } else if (el.indexOf("@mozilla/intl/") == 0) {
	continue;
     } else if (el.indexOf("@mozilla/browser/bookmarks") == 0) {
	continue;
     }
     try {
	if (
	    // XXX These cause segfaults when createInstance() is called.
	    // Should file some bugs.
	    el == "@mozilla.org/scroll-port-view;1"
	    || el == "@mozilla.org/rdf/datasource;1?name=charset-menu"
	    || el == "@mozilla.org/view;1"
	    || el == "@mozilla.org/intl/stringcharsetdetect;1?type=koclassic"
	    ) continue;
	// These cause other problems

	if (
	    el == "@mozilla.org/scrolling-view;1"
	    || el == "@mozilla.org/intl/charsetdetect;1?type=jams"
	    || el == "@mozilla.org/messenger/server;1?type=nntp"
	    || el == "@mozilla.org/intl/charsetdetect;1?type=koclassic"
	    || el == "@mozilla.org/intl/charsetdetect;1?type=jaclassic"
	    || el == "@mozilla.org/rdf/datasource;1?name=bookmarks"
	    || el == "@mozilla.org/view-manager;1"
	    || el == "@mozilla.org/network/dns-service;1"
	    || el == "@mozilla.org/sidebar;1"
	    || el == "@mozilla.org/browser/bookmarks-service;1"
	    || el == "@mozilla.org/intl/nslocale;1"
	    || el == "@mozilla.org/"
	    || el == "@mozilla.org/"
	    || el == "@mozilla.org/"
	    || el == "@mozilla.org/"
	    )
	  continue;
	foo = Components.classes[el].createInstance();
	if (foo.QueryInterface(iface)) {
	   components[found] = el;
	   found++;
	}
     } catch (e) {
     }
  }
  dump("found " + found + " component" + (found - 1 ? "s" : "") + "\n");
  for (var i in components) dump(components[i] + "\n");
}

reverseLookup(Components.interfaces.nsIIOService);


/*

To search for components implementing interface nsIFoo, you would do:
reverseLookup(Components.interfaces.nsIFoo);



For example:
js> findComp('url');
component://netscape/network/standard-url
component://netscape/network/standard-urlparser
component://netscape/network/no-authority-urlparser
component://netscape/network/authority-urlparser
js>
js> URL=Components.classes['component://netscape/network/standard-url'].createInstance(); [xpconnect wrapped nsISupports]
js>
js> findInterfaces(URL);

nsIURL
nsIFileURL
nsIURI
nsISupports
js>
 
Both methods use brute force, but in a interactive environment, when debugging, speed isn't too high a priority. Both methods are certainly fast enough for me.
 
For quick introspection, one can also list all supported attributes and functions on an object with the following function:
 
*/

/* List attributes of a given object */
function introspect(obj) {
   for (var elt in obj) {
      if (elt == 'style') {
	 continue;
      }
      try {
	 dump(elt + "=" + obj[elt] + "\n");
      } catch(e) {
	 dump(elt + ": unknown" + "\n");
      }
   }
}
 
/*
js> URL = URL.QueryInterface(Components.interfaces.nsIURL);
[xpconnect wrapped nsIURL]
js> introspect(URL)
function: QueryInterface
string: spec
object: scheme
object: preHost
object: username
object: password
object: host
number: port
string: path
object: URLParser
function: equals
function: clone
function: setRelativePath
function: resolve
string: filePath
object: param
object: query
object: ref
unknown: directory
object: fileName
object: fileBaseName
object: fileExtension
js> 
 
*/

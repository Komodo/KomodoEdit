/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

function findComp(re) {
     var regExp = new RegExp(re, 'i');
     for (var el in Components.classes)
         if (el.search(regExp) > -1) print(el);
}
/* List all interfaces supported by a given component */
function findInterfaces(obj) {
     for (var el in Components.interfaces) {
        try {
       obj.QueryInterface(Components.interfaces[el]);
       print(el); 
   } catch(e) {}
     }
}
> For example:
> js> findComp('url');
> component://netscape/network/standard-url
> component://netscape/network/standard-urlparser
> component://netscape/network/no-authority-urlparser
> component://netscape/network/authority-urlparser
> js>
> js> URL=Components.classes['component://netscape/network/standard-url'].createInstance();
> [xpconnect wrapped nsISupports]
> js>
> js> findInterfaces(URL);
> nsIURL
> nsIFileURL
> nsIURI
> nsISupports
> js>
> 
> Both methods use brute force, but in a interactive environment, when
> debugging, speed isn't too high a priority. Both methods are certainly
> fast enough for me.
> 
> For quick introspection, one can also list all supported attributes and
> functions on an object with the following function:
> 
> /* List attributes of a given object */
> function introspect(obj) {
>     for (var el in obj)
>         try { print(typeof obj[el] + ': ' + el); }
>   catch(e) { print('unknown: ' + el); }
> }
> 
> js> URL = URL.QueryInterface(Components.interface.nsIURL);
> [xpconnect wrapped nsIURL]
> js> introspect(URL)
> function: QueryInterface
> string: spec
> object: scheme
> object: preHost
> object: username
> object: password
> object: host
> number: port
> string: path
> object: URLParser
> function: equals
> function: clone
> function: setRelativePath
> function: resolve
> string: filePath
> object: param
> object: query
> object: ref
> unknown: directory
> object: fileName
> object: fileBaseName
> object: fileExtension
> js> 
> 
> I have no idea why directory is 'unknown' (typeof of the attribute throws
> an NS_ERROR_FAILURE), but nsIURL.idl claims it should be a string. Oh 
> well.
> 
> Hope this helps!
>

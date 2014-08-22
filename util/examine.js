/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 * 
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 * 
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 * 
 * The Original Code is Komodo code.
 * 
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
 * ActiveState Software Inc. All Rights Reserved.
 * 
 * Contributor(s):
 *   ActiveState Software Inc
 * 
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 * 
 * ***** END LICENSE BLOCK ***** */

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

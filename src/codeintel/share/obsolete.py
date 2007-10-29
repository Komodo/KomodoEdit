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

"""Some obsolete code that might prove useful again sometime soon."""

#---- Python completion fallback handling
#
#_gPyFuncTypes = (
#    types.BuiltinFunctionType,
#    types.BuiltinMethodType,
#    types.FunctionType,
#    types.GeneratorType,
#    types.LambdaType,
#    types.MethodType,
#    types.UnboundMethodType,
#    types.ModuleType,
#    types.ClassType,
#)
#def _getTypeNameForPyObj(obj):
#    if isinstance(obj, _gPyFuncTypes):
#        typeName = "function"
#    elif isinstance(obj, types.ModuleType):
#        typeName = "module"
#    elif isinstance(obj, types.ClassType):
#        typeName = "class"
#    else:
#        typeName = "variable"
#    return typeName
#
#def _getPyClassMembers(obj):
#    # Recurse into base classes looking for attributes
#    typesAndMembers = []
#    try:
#        members = dir(obj)
#        for b in obj.__bases__:
#            for m in _getPyClassMembers(b):
#                if m not in members:
#                    members.append(m)
#    except AttributeError:
#        pass
#    return members
#
#def _findPyClassConstructor(classObj):
#    # Given a class object, return a function object used for the
#    # constructor (ie, __init__() ) or None if we can't find one.
#    try:
#        return classObj.__init__.im_func
#    except AttributeError:
#        for base in classObj.__bases__:
#            rc = _findPyClassConstructor(base)
#            if rc is not None:
#                return rc
#    return None
#
#def _getPyObjCallTip(obj):
#    """Return a suitable call tip for the given Python object."""
#    if obj is None:
#        return ""
#
#    name = ""
#    argStr = ""
#    doc = None
#    argOffset = 0
#    if type(obj) == types.ClassType:
#        # Look for the highest __init__ in the class chain.
#        funcObj = _findPyClassConstructor(obj)
#        if funcObj is None:
#            funcObj = lambda: None
#        else:
#            argOffset = 1
#        name = "%s.%s" % (obj.__name__, funcObj.__name__)
#    elif type(obj) == types.MethodType:
#        # bit of a hack for methods - turn it into a function
#        # but we drop the "self" param.
#        funcObj = obj.im_func
#        argOffset = 1
#        name = funcObj.__name__
#    else:
#        funcObj = obj
#        try:
#            name = funcObj.__name__
#        except AttributeError:
#            pass
#    # Try and build one for Python defined functions
#    if type(funcObj) in (types.FunctionType, types.LambdaType):
#        try:
#            realArgs = funcObj.func_code.co_varnames[argOffset:funcObj.func_code.co_argcount]
#            defaults = funcObj.func_defaults or []
#            defaults = list(map(lambda name: "=%s" % name, defaults))
#            defaults = [""] * (len(realArgs)-len(defaults)) + defaults
#            items = map(lambda arg, dflt: arg+dflt, realArgs, defaults)
#            if funcObj.func_code.co_flags & 0x4:
#                items.append("...")
#            if funcObj.func_code.co_flags & 0x8:
#                items.append("***")
#            argStr = ", ".join(items)
#            argStr = "(%s)" % argStr
#        except:
#            pass
#    # See if we can use the docstring.
#    if hasattr(obj, "__doc__") and obj.__doc__:
#        pos = obj.__doc__.find("\n")
#        if pos<0 or pos>70: pos=70
#        doc = obj.__doc__[:pos]
#    # Put it together.
#    calltip = name+argStr
#    if doc:
#        if calltip: calltip += "\n"  # calltip can be empty for, e.g., str(
#        calltip += doc
#    return calltip
#


#    def _getMembersPyEvalFallback(self, symbolRef):
#        """See if the symbol reference matches one of the modules in the
#        current process run-time. ...to ensure being no worse that previous
#        AutoComplete implementations in Komodo.
#        
#        Returns None if nothing suitable was found.
#        """
#        try:
#            namespace = sys.modules.copy()
#            #NOTE: the PythonWin equivalent code also has:
#            #      - namespace.update(__main__.__dict__); and
#            #      - Adds the current context from its Interactive Shell.
#            #      Do we want to add those?
#            obj = eval(symbolRef, namespace)
#        except:
#            return None
#        typesAndMembers = None
#        if obj is not None:
#            members = []
#            try:
#                members += dir(obj)
#            except AttributeError:
#                pass # object has no __dict__
#            if hasattr(obj, "__class__"):
#                members += _getPyClassMembers(obj.__class__)
#            typesAndMembers = []
#            for m in members:
#                if m[0] == '_':
#                    continue # drop pseudo-private and special attrs
#                typeName = _getTypeNameForPyObj(getattr(obj, m))
#                typesAndMembers.append((typeName, m))
#
#            # The object may be a COM object with typelib support - lets see
#            # if we can get its props. (contributed by Stefan Migowsky)
#            try:
#                # Get the automation attributes
#                typesAndProps = [("function", p) for p in
#                                 obj.__class__._prop_map_get_.keys()]
#                # See if there is an write only property 
#                # could be optimized
#                for p in obj.__class__._prop_map_put_.keys():
#                    tp = ("function", p)
#                    if tp not in typesAndProps:
#                        typesAndProps.append(tp)
#                typesAndMembers += typesAndProps
#            except AttributeError:
#                pass
#            
#            if not typesAndMembers:
#                typesAndMembers = None
#        return typesAndMembers
#
#    def _getMembersFallback(self, expr, content, line, language):
#        """A dumb fallback mechanism for finding members.
#        
#            "expr" is the CITDL expression.
#            "content" is the file content.
#            "line" is the line in the content on which AutoComplete was
#                triggered.
#            "language" is the file's language.
#        
#        Basic algorithms from PythonWin. Returns a list of 2-tuples:
#            (<codeintel-type-name>, <member-name>)
#        of found members; the empty list if none found.
#        """
#        symbolRef = self._parseCITDLExpr(expr)[0]
#        typesAndMembers = None
#        if language == "Python" and '(' not in symbolRef:
#            #XXX Technically eval'ing any "symbolRef" is potentially
#            #    dangerous. __getattr__ code *will* be run. We specifically
#            #    disallow eval'ing expressions with "()" because those are
#            #    more likely to have a side-effect.
#            typesAndMembers = self._getMembersPyEvalFallback(symbolRef)
#        if typesAndMembers is None:
#            # Heuristics a-la "complete word": The idea is to find other
#            # usages of the current binding and assume, that it refers to the
#            # same object (or at least, to an object of the same type)
#            # Contributed to PythonWin by Vadim Chugunov [vadimch@yahoo.com]
#
#            #NOTE: PythonWin limits the search to the current class using
#            #      its class browser. Perhaps we should do that here with
#            #      our scope information?
#
#            if language == "Python":
#                pattern = re.compile(r"\b%s(\.)(\w+)(\s*\()?" % re.escape(symbolRef))
#            elif language == "Perl":
#                pattern = re.compile(r"%s(->|::)(\w+)(\s*\()?" % re.escape(symbolRef))
#            else:
#                raise CodeIntelError("don't know how to make a suitable "
#                                     "dumb-get-members pattern for %s"
#                                     % language)
#            try:
#                hits = pattern.findall(content)
#            except re.error:
#                # With the added "re.escape()" (when this code was adapted
#                # for use in the CodeIntel system) this should not raise, but
#                # let's be paranoid.
#                hits = []
#
#            # If the word currently to the right of the dot is the only
#            # such occurrence, it is probably a red-herring.
#            lines = content.splitlines()
#            herrings = re.findall(pattern, lines[line-1])
#            for herring in herrings: # Can be multiple on this one line.
#                if herring in hits:
#                    hits.remove(herring)
#
#            # Remove duplicates names.
#            unique = {}
#            for hit in hits:
#                unique[hit[1]] = hit
#            hits = unique.values()
#
#            typesAndMembers = []
#            if language == "Python":
#                for trigger,name,call in hits:
#                    # Only filter out __*__ members and not _* members because
#                    # local private and protected attributes on a class should be
#                    # included.
#                    if name[:2]=="__" and name[-2:]=="__": continue
#                    typeName = call and "function" or "variable"
#                    typesAndMembers.append( (typeName, name) )
#            elif language == "Perl":
#                symbolPrefix = re.search(r'(.?)\b\w', symbolRef).group(1)
#                for trigger,name,call in hits:
#                    if call or trigger == "->" or symbolPrefix in ' &':
#                        typeName = "function"
#                    elif symbolPref:
#                        typeName = "variable"
#                    typesAndMembers.append( (typeName, name) )
#            else:
#                raise NotImplementedError("fallback member type determination "
#                                          "not implemented for '%s'" % language)
#
#        log.info("    fallback members: %r", typesAndMembers)
#        return typesAndMembers or []
#
#    def _getCallTipsPyEvalFallback(self, symbolRef):
#        """See if the symbol reference matches one of the modules in the
#        current process run-time. ...to ensure being no worse that previous
#        AutoComplete implementations in Komodo.
#        
#        Returns None if nothing suitable was found.
#        """
#        try:
#            namespace = sys.modules.copy()
#            #NOTE: the PythonWin equivalent code also has:
#            #      - namespace.update(__main__.__dict__); and
#            #      - Adds the current context from its Interactive Shell.
#            #      Do we want to add those?
#            obj = eval(symbolRef, namespace)
#        except:
#            return None
#        calltips = None
#        if obj is not None and type(obj) != types.ModuleType:
#            calltip = _getPyObjCallTip(obj)
#            if calltip: calltips = [calltip]
#        return calltips
#
#    def _getCallTipsFallback(self, expr, content, line, language):
#        """A dumb fallback mechanism for finding calltips.
#        
#            "expr" is the CITDL expression.
#            "content" is the file content.
#            "line" is the line in the content on which a CallTip was
#                triggered.
#            "language" is the file's language.
#        
#        Basic algorithms from PythonWin. Returns a list of found CallTips
#        (the empty list if none found).
#        """
#        symbolRef = self._parseCITDLExpr(expr)[0]
#        calltips = None
#        if language == "Python" and '(' not in symbolRef:
#            #XXX Technically eval'ing any "symbolRef" is potentially
#            #    dangerous. __getattr__ code *will* be run. We specifically
#            #    disallow eval'ing expressions with "()" because those are
#            #    more likely to have a side-effect.
#            calltips = self._getCallTipsPyEvalFallback(symbolRef)
#        citdl.log.info("    fallback calltips: %r", calltips)
#        return calltips or []
#

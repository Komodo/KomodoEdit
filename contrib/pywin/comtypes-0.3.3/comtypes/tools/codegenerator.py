# Code generator to generate code for everything contained in COM type
# libraries.
import os
from comtypes.tools import typedesc
import comtypes.client
import comtypes.client._generate

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

class lcid(object):
    def __repr__(self):
        return "_lcid"
lcid = lcid()
        
class dispid(object):
    def __init__(self, memid):
        self.memid = memid

    def __repr__(self):
        return "dispid(%s)" % self.memid

class helpstring(object):
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return "helpstring(%r)" % self.text


# XXX Should this be in ctypes itself?
ctypes_names = {
    "unsigned char": "c_ubyte",
    "signed char": "c_byte",
    "char": "c_char",

    "wchar_t": "c_wchar",

    "short unsigned int": "c_ushort",
    "short int": "c_short",

    "long unsigned int": "c_ulong",
    "long int": "c_long",
    "long signed int": "c_long",

    "unsigned int": "c_uint",
    "int": "c_int",

    "long long unsigned int": "c_ulonglong",
    "long long int": "c_longlong",

    "double": "c_double",
    "float": "c_float",

    # Hm...
    "void": "None",
}

def get_real_type(tp):
    if type(tp) is typedesc.Typedef:
        return get_real_type(tp.typ)
    elif isinstance(tp, typedesc.CvQualifiedType):
        return get_real_type(tp.typ)
    return tp

ASSUME_STRINGS = True

def _calc_packing(struct, fields, pack, isStruct):
    # Try a certain packing, raise PackingError if field offsets,
    # total size ot total alignment is wrong.
    if struct.size is None: # incomplete struct
        return -1
    if struct.name in dont_assert_size:
        return None
    if struct.bases:
        size = struct.bases[0].size
        total_align = struct.bases[0].align
    else:
        size = 0
        total_align = 8 # in bits
    for i, f in enumerate(fields):
        if f.bits: # this code cannot handle bit field sizes.
##            print "##XXX FIXME"
            return -2 # XXX FIXME
        s, a = storage(f.typ)
        if pack is not None:
            a = min(pack, a)
        if size % a:
            size += a - size % a
        if isStruct:
            if size != f.offset:
                raise PackingError, "field %s offset (%s/%s)" % (f.name, size, f.offset)
            size += s
        else:
            size = max(size, s)
        total_align = max(total_align, a)
    if total_align != struct.align:
        raise PackingError, "total alignment (%s/%s)" % (total_align, struct.align)
    a = total_align
    if pack is not None:
        a = min(pack, a)
    if size % a:
        size += a - size % a
    if size != struct.size:
        raise PackingError, "total size (%s/%s)" % (size, struct.size)

def calc_packing(struct, fields):
    # try several packings, starting with unspecified packing
    isStruct = isinstance(struct, typedesc.Structure)
    for pack in [None, 16*8, 8*8, 4*8, 2*8, 1*8]:
        try:
            _calc_packing(struct, fields, pack, isStruct)
        except PackingError, details:
            continue
        else:
            if pack is None:
                return None
            return pack/8
    raise PackingError, "PACKING FAILED: %s" % details

class PackingError(Exception):
    pass

# XXX These should be filtered out in gccxmlparser.
dont_assert_size = set(
    [
    "__si_class_type_info_pseudo",
    "__class_type_info_pseudo",
    ]
    )

def storage(t):
    # return the size and alignment of a type
    if isinstance(t, typedesc.Typedef):
        return storage(t.typ)
    elif isinstance(t, typedesc.ArrayType):
        s, a = storage(t.typ)
        return s * (int(t.max) - int(t.min) + 1), a
    return int(t.size), int(t.align)

################################################################

class Generator(object):

    def __init__(self, ofi, known_symbols=None):
        self._externals = {}
        self.output = ofi
        self.stream = StringIO.StringIO()
        self.imports = StringIO.StringIO()
##        self.stream = self.imports = self.output
        self.known_symbols = known_symbols or {}

        self.done = set() # type descriptions that have been generated
        self.names = set() # names that have been generated

    def generate(self, item):
        if item in self.done:
            return
        if isinstance(item, typedesc.StructureHead):
            name = getattr(item.struct, "name", None)
        else:
            name = getattr(item, "name", None)
        if name in self.known_symbols:
            mod = self.known_symbols[name]
            print >> self.imports, "from %s import %s" % (mod, name)
            self.done.add(item)
            if isinstance(item, typedesc.Structure):
                self.done.add(item.get_head())
                self.done.add(item.get_body())
            return
        mth = getattr(self, type(item).__name__)
        # to avoid infinite recursion, we have to mark it as done
        # before actually generating the code.
        self.done.add(item)
        mth(item)

    def generate_all(self, items):
        for item in items:
            self.generate(item)

    def cmpitems(a, b):
	a = getattr(a, "location", None)
	b = getattr(b, "location", None)
	if a is None: return -1
	if b is None: return 1
	return cmp(a[0],b[0]) or cmp(int(a[1]),int(b[1]))
    cmpitems = staticmethod(cmpitems)

    def _make_relative_path(self, path1, path2):
        """path1 and path2 are pathnames.
        Return path1 as a relative path to path2, if possible.
        """
        path1 = os.path.abspath(path1)
        path2 = os.path.abspath(path2)
        common = os.path.commonprefix([os.path.normcase(path1),
                                       os.path.normcase(path2)])
        if not os.path.isdir(common):
            return path1
        if not common.endswith("\\"):
            return path1
        if not os.path.isdir(path2):
            path2 = os.path.dirname(path2)
        # strip the common prefix
        path1 = path1[len(common):]
        path2 = path2[len(common):]

        parts2 = path2.split("\\")
        return "..\\" * len(parts2) + path1

    def generate_code(self, items, filename=None):
        self.filename = filename
        if filename is not None:
            if os.path.isabs(filename):
                # absolute path
                print >> self.output, "typelib_path = %r" % filename
            elif not os.path.dirname(filename) and not os.path.isfile(filename):
                # no directory given, and not in current directory.
                print >> self.output, "typelib_path = %r" % filename
            else:
                # relative path; make relative to comtypes.gen.
                path = self._make_relative_path(filename, comtypes.gen.__path__[0])
                print >> self.output, "import os"
                print >> self.output, "typelib_path = os.path.normpath("
                print >> self.output, "    os.path.abspath(os.path.join(os.path.dirname(__file__),"
                print >> self.output, "                                 %r)))" % path

                p = os.path.normpath(os.path.abspath(os.path.join(comtypes.gen.__path__[0],
                                                                  path)))
                assert os.path.isfile(p)
        print >> self.imports, "_lcid = 0 # change this if required"
        print >> self.imports, "from ctypes import *"
        items = set(items)
        loops = 0
        while items:
            loops += 1
            self.more = set()
            self.generate_all(sorted(items, self.cmpitems))

            items |= self.more
            items -= self.done

        self.output.write(self.imports.getvalue())
        self.output.write("\n\n")
        self.output.write(self.stream.getvalue())

        import textwrap
        wrapper = textwrap.TextWrapper(subsequent_indent="           ",
                                       break_long_words=False)
        text = "__all__ = [%s]" % ", ".join([repr(str(n)) for n in self.names])

        for line in wrapper.wrap(text):
            print >> self.output, line
        return loops

    def type_name(self, t, generate=True):
        # Return a string, containing an expression which can be used
        # to refer to the type. Assumes the 'from ctypes import *'
        # namespace is available.
        if isinstance(t, typedesc.SAFEARRAYType):
            return "_midlSAFEARRAY(%s)" % self.type_name(t.typ)
##        if isinstance(t, typedesc.CoClass):
##            return "%s._com_interfaces_[0]" % t.name
        if isinstance(t, typedesc.Typedef):
            return t.name
        if isinstance(t, typedesc.PointerType):
            if ASSUME_STRINGS:
                x = get_real_type(t.typ)
                if isinstance(x, typedesc.FundamentalType):
                    if x.name == "char":
                        self.need_STRING()
                        return "STRING"
                    elif x.name == "wchar_t":
                        self.need_WSTRING()
                        return "WSTRING"

            result = "POINTER(%s)" % self.type_name(t.typ, generate)
            # XXX Better to inspect t.typ!
            if result.startswith("POINTER(WINFUNCTYPE"):
                return result[len("POINTER("):-1]
            if result.startswith("POINTER(CFUNCTYPE"):
                return result[len("POINTER("):-1]
            elif result == "POINTER(None)":
                return "c_void_p"
            return result
        elif isinstance(t, typedesc.ArrayType):
            return "%s * %s" % (self.type_name(t.typ, generate), int(t.max)+1)
        elif isinstance(t, typedesc.FunctionType):
            args = [self.type_name(x, generate) for x in [t.returns] + list(t.iterArgTypes())]
            if "__stdcall__" in t.attributes:
                return "WINFUNCTYPE(%s)" % ", ".join(args)
            else:
                return "CFUNCTYPE(%s)" % ", ".join(args)
        elif isinstance(t, typedesc.CvQualifiedType):
            # const and volatile are ignored
            return "%s" % self.type_name(t.typ, generate)
        elif isinstance(t, typedesc.FundamentalType):
            return ctypes_names[t.name]
        elif isinstance(t, typedesc.Structure):
            return t.name
        elif isinstance(t, typedesc.Enumeration):
            if t.name:
                return t.name
            return "c_int" # enums are integers
        return t.name

    def need_VARIANT_imports(self, value):
        text = repr(value)
        if "Decimal(" in text:
            print >> self.imports, "from decimal import Decimal"
        if "datetime.datetime(" in text:
            print >> self.imports, "import datetime"

    _STRING_defined = False
    def need_STRING(self):
        if self._STRING_defined:
            return
        print >> self.imports, "STRING = c_char_p"
        self._STRING_defined = True

    _WSTRING_defined = False
    def need_WSTRING(self):
        if self._WSTRING_defined:
            return
        print >> self.imports, "WSTRING = c_wchar_p"
        self._WSTRING_defined = True

    _arraytypes = 0
    def ArrayType(self, tp):
        self._arraytypes += 1
        self.generate(get_real_type(tp.typ))
        self.generate(tp.typ)

    _enumvalues = 0
    def EnumValue(self, tp):
        value = int(tp.value)
        print >> self.stream, \
              "%s = %d" % (tp.name, value)
        self.names.add(tp.name)
        self._enumvalues += 1

    _enumtypes = 0
    def Enumeration(self, tp):
        self._enumtypes += 1
        print >> self.stream
        if tp.name:
            print >> self.stream, "# values for enumeration '%s'" % tp.name
        else:
            print >> self.stream, "# values for unnamed enumeration"
        # Some enumerations have the same name for the enum type
        # and an enum value.  Excel's XlDisplayShapes is such an example.
        # Since we don't have separate namespaces for the type and the values,
        # we generate the TYPE last, overwriting the value. XXX
        for item in tp.values:
            self.generate(item)
        if tp.name:
            print >> self.stream, "%s = c_int # enum" % tp.name
            self.names.add(tp.name)

    _GUID_defined = False
    def need_GUID(self):
        if self._GUID_defined:
            return
        self._GUID_defined = True
        modname = self.known_symbols.get("GUID")
        if modname:
            print >> self.imports, "from %s import GUID" % modname

    _typedefs = 0
    def Typedef(self, tp):
        self._typedefs += 1
        if type(tp.typ) in (typedesc.Structure, typedesc.Union):
            self.generate(tp.typ.get_head())
            self.more.add(tp.typ)
        else:
            self.generate(tp.typ)
        if self.type_name(tp.typ) in self.known_symbols:
            stream = self.imports
        else:
            stream = self.stream
        if tp.name != self.type_name(tp.typ):
            print >> stream, "%s = %s" % \
                  (tp.name, self.type_name(tp.typ))
        self.names.add(tp.name)

    def FundamentalType(self, item):
        pass # we should check if this is known somewhere

    def StructureHead(self, head):
        for struct in head.struct.bases:
            self.generate(struct.get_head())
            self.more.add(struct)
        if head.struct.location:
            print >> self.stream, "# %s %s" % head.struct.location
        basenames = [self.type_name(b) for b in head.struct.bases]
        if basenames:
            self.need_GUID()
            method_names = [m.name for m in head.struct.members if type(m) is typedesc.Method]
            print >> self.stream, "class %s(%s):" % (head.struct.name, ", ".join(basenames))
            print >> self.stream, "    _iid_ = GUID('{}') # please look up iid and fill in!"
            if "Enum" in method_names:
                print >> self.stream, "    def __iter__(self):"
                print >> self.stream, "        return self.Enum()"
            elif method_names == "Next Skip Reset Clone".split():
                print >> self.stream, "    def __iter__(self):"
                print >> self.stream, "        return self"
                print >> self.stream
                print >> self.stream, "    def next(self):"
                print >> self.stream, "         arr, fetched = self.Next(1)"
                print >> self.stream, "         if fetched == 0:"
                print >> self.stream, "             raise StopIteration"
                print >> self.stream, "         return arr[0]"
        else:
            methods = [m for m in head.struct.members if type(m) is typedesc.Method]
            if methods:
                # Hm. We cannot generate code for IUnknown...
                print >> self.stream, "assert 0, 'cannot generate code for IUnknown'"
                print >> self.stream, "class %s(_com_interface):" % head.struct.name
                print >> self.stream, "    pass"
            elif type(head.struct) == typedesc.Structure:
                print >> self.stream, "class %s(Structure):" % head.struct.name
                if hasattr(head.struct, "_recordinfo_"):
                    print >> self.stream, "    _recordinfo_ = %r" % (head.struct._recordinfo_,)
                else:
                    print >> self.stream, "    pass"
            elif type(head.struct) == typedesc.Union:
                print >> self.stream, "class %s(Union):" % head.struct.name
                print >> self.stream, "    pass"
        self.names.add(head.struct.name)

    _structures = 0
    def Structure(self, struct):
        self._structures += 1
        self.generate(struct.get_head())
        self.generate(struct.get_body())

    Union = Structure
        
    def StructureBody(self, body):
        fields = []
        methods = []
        for m in body.struct.members:
            if type(m) is typedesc.Field:
                fields.append(m)
                if type(m.typ) is typedesc.Typedef:
                    self.generate(get_real_type(m.typ))
                self.generate(m.typ)
            elif type(m) is typedesc.Method:
                methods.append(m)
                self.generate(m.returns)
                self.generate_all(m.iterArgTypes())
            elif type(m) is typedesc.Constructor:
                pass

        # we don't need _pack_ on Unions (I hope, at least), and not
        # on COM interfaces:
        if not methods:
            try:
                pack = calc_packing(body.struct, fields)
                if pack is not None:
                    print >> self.stream, "%s._pack_ = %s" % (body.struct.name, pack)
            except PackingError, details:
                # if packing fails, write a warning comment to the output.
                import warnings
                message = "Structure %s: %s" % (body.struct.name, details)
                warnings.warn(message, UserWarning)
                print >> self.stream, "# WARNING: %s" % details

        if fields:
            if body.struct.bases:
                assert len(body.struct.bases) == 1
                self.generate(body.struct.bases[0].get_body())
            # field definition normally span several lines.
            # Before we generate them, we need to 'import' everything they need.
            # So, call type_name for each field once,
            for f in fields:
                self.type_name(f.typ)
            print >> self.stream, "%s._fields_ = [" % body.struct.name
            if body.struct.location:
                print >> self.stream, "    # %s %s" % body.struct.location
            # unnamed fields will get autogenerated names "_", "_1". "_2", "_3", ...
            unnamed_index = 0
            for f in fields:
                if not f.name:
                    if unnamed_index:
                        fieldname = "_%d" % unnamed_index
                    else:
                        fieldname = "_"
                    unnamed_index += 1
                    print >> self.stream, "    # Unnamed field renamed to '%s'" % fieldname
                else:
                    fieldname = f.name
                if f.bits is None:
                    print >> self.stream, "    ('%s', %s)," % (fieldname, self.type_name(f.typ))
                else:
                    print >> self.stream, "    ('%s', %s, %s)," % (fieldname, self.type_name(f.typ), f.bits)
            print >> self.stream, "]"
            # generate assert statements for size and alignment
            if body.struct.size and body.struct.name not in dont_assert_size:
                size = body.struct.size // 8
                print >> self.stream, "assert sizeof(%s) == %s, sizeof(%s)" % \
                      (body.struct.name, size, body.struct.name)
                align = body.struct.align // 8
                print >> self.stream, "assert alignment(%s) == %s, alignment(%s)" % \
                      (body.struct.name, align, body.struct.name)

        if methods:
            self.need_COMMETHOD()
            # method definitions normally span several lines.
            # Before we generate them, we need to 'import' everything they need.
            # So, call type_name for each field once,
            for m in methods:
                self.type_name(m.returns)
                for a in m.iterArgTypes():
                    self.type_name(a)
            print >> self.stream, "%s._methods_ = [" % body.struct.name
            if body.struct.location:
                print >> self.stream, "# %s %s" % body.struct.location

            for m in methods:
                if m.location:
                    print >> self.stream, "    # %s %s" % m.location
                print >> self.stream, "    COMMETHOD([], %s, '%s'," % (
                    self.type_name(m.returns),
                    m.name)
                for a in m.iterArgTypes():
                    print >> self.stream, \
                          "               ( [], %s, )," % self.type_name(a)
                    print >> self.stream, "             ),"
            print >> self.stream, "]"

    _midlSAFEARRAY_defined = False
    def need_midlSAFEARRAY(self):
        if self._midlSAFEARRAY_defined:
            return
        print >> self.imports, "from comtypes.automation import _midlSAFEARRAY"
        self._midlSAFEARRAY_defined = True

    _CoClass_defined = False
    def need_CoClass(self):
        if self._CoClass_defined:
            return
        print >> self.imports, "from comtypes import CoClass"
        self._CoClass_defined = True

    _dispid_defined = False
    def need_dispid(self):
        if self._dispid_defined:
            return
        print >> self.imports, "from comtypes import dispid"
        self._dispid_defined = True

    _COMMETHOD_defined = False
    def need_COMMETHOD(self):
        if self._COMMETHOD_defined:
            return
        print >> self.imports, "from comtypes import helpstring"
        print >> self.imports, "from comtypes import COMMETHOD"
        self._COMMETHOD_defined = True

    _DISPMETHOD_defined = False
    def need_DISPMETHOD(self):
        if self._DISPMETHOD_defined:
            return
        print >> self.imports, "from comtypes import DISPMETHOD, DISPPROPERTY, helpstring"
        self._DISPMETHOD_defined = True

    ################################################################
    # top-level typedesc generators
    #
    def TypeLib(self, lib):
        # lib.name, lib.gui, lib.major, lib.minor, lib.doc

        # Hm, in user code we have to write:
        # class MyServer(COMObject, ...):
        #     _com_interfaces_ = [MyTypeLib.IInterface]
        #     _reg_typelib_ = MyTypeLib.Library._reg_typelib_
        #                               ^^^^^^^
        # Should the '_reg_typelib_' attribute be at top-level in the
        # generated code, instead as being an attribute of the
        # 'Library' symbol?
        print >> self.stream, "class Library(object):"
        if lib.doc:
            print >> self.stream, "    %r" % lib.doc
        if lib.name:
            print >> self.stream, "    name = %r" % lib.name
        print >> self.stream, "    _reg_typelib_ = (%r, %r, %r)" % (lib.guid, lib.major, lib.minor)
        print >> self.stream

    def External(self, ext):
        # ext.docs - docstring of typelib
        # ext.symbol_name - symbol to generate
        # ext.tlib - the ITypeLib pointer to the typelibrary containing the symbols definition
        #
        # ext.name filled in here

        libdesc = str(ext.tlib.GetLibAttr()) # str(TLIBATTR) is unique for a given typelib
        if libdesc in self._externals: # typelib wrapper already created
            modname = self._externals[libdesc]
            # we must fill in ext.name, it is used by self.type_name()
            ext.name = "%s.%s" % (modname, ext.symbol_name)
            return

        modname = comtypes.client._generate._name_module(ext.tlib)
        ext.name = "%s.%s" % (modname, ext.symbol_name)
        self._externals[libdesc] = modname
        print >> self.imports, "import", modname
        comtypes.client.GetModule(ext.tlib)

    def Constant(self, tp):
        print >> self.stream, \
              "%s = %r # Constant %s" % (tp.name,
                                         tp.value,
                                         self.type_name(tp.typ, False))
        self.names.add(tp.name)

    def SAFEARRAYType(self, sa):
        self.generate(sa.typ)
        self.need_midlSAFEARRAY()

    _pointertypes = 0
    def PointerType(self, tp):
        self._pointertypes += 1
        if type(tp.typ) is typedesc.ComInterface:
            # this defines the class
            self.generate(tp.typ.get_head())
            # this defines the _methods_
            self.more.add(tp.typ)
        elif type(tp.typ) is typedesc.PointerType:
            self.generate(tp.typ)
        elif type(tp.typ) in (typedesc.Union, typedesc.Structure):
            self.generate(tp.typ.get_head())
            self.more.add(tp.typ)
        elif type(tp.typ) is typedesc.Typedef:
            self.generate(tp.typ)
        else:
            self.generate(tp.typ)

    def CoClass(self, coclass):
        self.need_GUID()
        self.need_CoClass()
        print >> self.stream, "class %s(CoClass):" % coclass.name
        doc = getattr(coclass, "doc", None)
        if doc:
            print >> self.stream, "    %r" % doc
        print >> self.stream, "    _reg_clsid_ = GUID(%r)" % coclass.clsid
        print >> self.stream, "    _idlflags_ = %s" % coclass.idlflags
        if self.filename is not None:
            print >> self.stream, "    _typelib_path_ = typelib_path"
##X        print >> self.stream, "POINTER(%s).__ctypes_from_outparam__ = wrap" % coclass.name

        libid = coclass.tlibattr.guid
        wMajor, wMinor = coclass.tlibattr.wMajorVerNum, coclass.tlibattr.wMinorVerNum
        print >> self.stream, "    _reg_typelib_ = (%r, %s, %s)" % (str(libid), wMajor, wMinor)

        for itf, idlflags in coclass.interfaces:
            self.generate(itf.get_head())
        implemented = [i[0].name for i in coclass.interfaces
                       if i[1] & 2 == 0]
        sources = [i[0].name for i in coclass.interfaces
                       if i[1] & 2 == 2]
        if implemented:
            print >> self.stream, "%s._com_interfaces_ = [%s]" % (coclass.name, ", ".join(implemented))
        if sources:
            print >> self.stream, "%s._outgoing_interfaces_ = [%s]" % (coclass.name, ", ".join(sources))
        print >> self.stream
        self.names.add(coclass.name)

    def ComInterface(self, itf):
        self.generate(itf.get_head())
        self.generate(itf.get_body())
        self.names.add(itf.name)

    def _is_enuminterface(self, itf):
        # Check if this is an IEnumXXX interface
        if not itf.name.startswith("IEnum"):
            return False
        member_names = [mth.name for mth in itf.members]
        for name in ("Next", "Skip", "Reset", "Clone"):
            if name not in member_names:
                return False
        return True

    def ComInterfaceHead(self, head):
        if head.itf.name in self.known_symbols:
            return
        base = head.itf.base
        if head.itf.base is None:
            # we don't beed to generate IUnknown
            return
        self.generate(base.get_head())
        self.more.add(base)
        basename = self.type_name(head.itf.base)

        self.need_GUID()
        print >> self.stream, "class %s(%s):" % (head.itf.name, basename)
        print >> self.stream, "    _case_insensitive_ = True"
        doc = getattr(head.itf, "doc", None)
        if doc:
            print >> self.stream, "    %r" % doc
        print >> self.stream, "    _iid_ = GUID(%r)" % head.itf.iid
        print >> self.stream, "    _idlflags_ = %s" % head.itf.idlflags

        if self._is_enuminterface(head.itf):
            print >> self.stream, "    def __iter__(self):"
            print >> self.stream, "        return self"
            print >> self.stream

            # Well, not sure if they are really broken, but sometimes
            # the last parameter to Next is marked [in, out],
            # sometimes it is only [out].
            NextIsBroken = False
            for mth in head.itf.members:
                if mth.name == "Next":
                    NextIsBroken = 'in' in mth.arguments[-1][2]
                    break

            print >> self.stream, "    def next(self):"
            if NextIsBroken:
                print >> self.stream, "        item, fetched = self.Next(1, 0)"
            else:
                print >> self.stream, "        item, fetched = self.Next(1)"
            print >> self.stream, "        if fetched:"
            print >> self.stream, "            return item"
            print >> self.stream, "        raise StopIteration"
            print >> self.stream

            print >> self.stream, "    def __getitem__(self, index):"
            print >> self.stream, "        self.Reset()"
            print >> self.stream, "        self.Skip(index)"
            if NextIsBroken:
                print >> self.stream, "        item, fetched = self.Next(1, 0)"
            else:
                print >> self.stream, "        item, fetched = self.Next(1)"
            print >> self.stream, "        if fetched:"
            print >> self.stream, "            return item"
            print >> self.stream, "        raise IndexError, index"
            print >> self.stream

    def ComInterfaceBody(self, body):
        # The base class must be fully generated, including the
        # _methods_ list.
        self.generate(body.itf.base)

        # make sure we can generate the body
        for m in body.itf.members:
            for a in m.arguments:
                self.generate(a[0])
            self.generate(m.returns)

        self.need_COMMETHOD()
        self.need_dispid()
        print >> self.stream, "%s._methods_ = [" % body.itf.name
        for m in body.itf.members:
            if isinstance(m, typedesc.ComMethod):
                self.make_ComMethod(m, "dual" in body.itf.idlflags)
            else:
                raise TypeError, "what's this?"
        print >> self.stream, "]"

    def DispInterface(self, itf):
        self.generate(itf.get_head())
        self.generate(itf.get_body())
        self.names.add(itf.name)

    def DispInterfaceHead(self, head):
        self.generate(head.itf.base)
        basename = self.type_name(head.itf.base)

        self.need_GUID()
        print >> self.stream, "class %s(%s):" % (head.itf.name, basename)
        print >> self.stream, "    _case_insensitive_ = True"
        doc = getattr(head.itf, "doc", None)
        if doc:
            print >> self.stream, "    %r" % doc
        print >> self.stream, "    _iid_ = GUID(%r)" % head.itf.iid
        print >> self.stream, "    _idlflags_ = %s" % head.itf.idlflags
        print >> self.stream, "    _methods_ = []"

    def DispInterfaceBody(self, body):
        # make sure we can generate the body
        for m in body.itf.members:
            if isinstance(m, typedesc.DispMethod):
                for a in m.arguments:
                    self.generate(a[0])
                self.generate(m.returns)
            elif isinstance(m, typedesc.DispProperty):
                self.generate(m.typ)
            else:
                raise TypeError, m

        self.need_dispid()
        self.need_DISPMETHOD()
        print >> self.stream, "%s._disp_methods_ = [" % body.itf.name
        for m in body.itf.members:
            if isinstance(m, typedesc.DispMethod):
                self.make_DispMethod(m)
            elif isinstance(m, typedesc.DispProperty):
                self.make_DispProperty(m)
            else:
                raise TypeError, m
        print >> self.stream, "]"

    ################################################################
    # non-toplevel method generators
    #
    def make_ComMethod(self, m, isdual):
        # typ, name, idlflags, default
        if isdual:
            idlflags = [dispid(m.memid)] + m.idlflags
        else:
            # We don't include the dispid for non-dispatch COM interfaces
            idlflags = m.idlflags
        if __debug__ and m.doc:
            idlflags.insert(1, helpstring(m.doc))
        code = "    COMMETHOD(%r, %s, '%s'" % (
            idlflags,
            self.type_name(m.returns),
            m.name)

        if not m.arguments:
            print >> self.stream, "%s)," % code
        else:
            print >> self.stream, "%s," % code
            self.stream.write("              ")
            arglist = []
            for typ, name, idlflags, default in m.arguments:
                if 'lcid' in idlflags:# and 'in' in idlflags:
                    default = lcid
                if default is not None:
                    self.need_VARIANT_imports(default)
                    arglist.append("( %r, %s, '%s', %r )" % (
                        idlflags,
                        self.type_name(typ),
                        name,
                        default))
                else:
                    arglist.append("( %r, %s, '%s' )" % (
                        idlflags,
                        self.type_name(typ),
                        name))
            self.stream.write(",\n              ".join(arglist))
            print >> self.stream, "),"

    def make_DispMethod(self, m):
        idlflags = [dispid(m.dispid)] + m.idlflags
        if __debug__ and m.doc:
            idlflags.insert(1, helpstring(m.doc))
        # typ, name, idlflags, default
        code = "    DISPMETHOD(%r, %s, '%s'" % (
            idlflags,
            self.type_name(m.returns),
            m.name)

        if not m.arguments:
            print >> self.stream, "%s)," % code
        else:
            print >> self.stream, "%s," % code
            self.stream.write("               ")
            arglist = []
            for typ, name, idlflags, default in m.arguments:
                self.need_VARIANT_imports(default)
                if default is not None:
                    arglist.append("( %r, %s, '%s', %r )" % (
                        idlflags,
                        self.type_name(typ),
                        name,
                        default))
                else:
                    arglist.append("( %r, %s, '%s' )" % (
                        idlflags,
                        self.type_name(typ),
                        name,
                        ))
            self.stream.write(",\n               ".join(arglist))
            print >> self.stream, "),"

    def make_DispProperty(self, prop):
        idlflags = [dispid(prop.dispid)] + prop.idlflags
        if __debug__ and prop.doc:
            idlflags.insert(1, helpstring(prop.doc))
        print >> self.stream, "    DISPPROPERTY(%r, %s, '%s')," % (
            idlflags,
            self.type_name(prop.typ),
            prop.name)

# shortcut for development
if __name__ == "__main__":
    import tlbparser
    tlbparser.main()

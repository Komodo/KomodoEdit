import imp
import new
import os
import sys
import comtypes.client

import logging
logger = logging.getLogger(__name__)

__verbose__ = __debug__

def _my_import(fullname):
    # helper function to import dotted modules
    return __import__(fullname, globals(), locals(), ['DUMMY'])

def _name_module(tlib):
    # Determine the name of a typelib wrapper module.
    libattr = tlib.GetLibAttr()
    modname = "_%s_%s_%s_%s" % \
              (str(libattr.guid)[1:-1].replace("-", "_"),
               libattr.lcid,
               libattr.wMajorVerNum,
               libattr.wMinorVerNum)
    return "comtypes.gen." + modname

def GetModule(tlib):
    """Create a module wrapping a COM typelibrary on demand.

    'tlib' must be an ITypeLib COM pointer instance, the pathname of a
    type library, or a tuple/list specifying the arguments to a
    comtypes.typeinfo.LoadRegTypeLib call:

      (libid, wMajorVerNum, wMinorVerNum, lcid=0)

    Or it can be an object with _reg_libid_ and _reg_version_
    attributes.

    A relative pathname is interpreted as relative to the callers
    __file__, if this exists.

    This function determines the module name from the typelib
    attributes, then tries to import it.  If that fails because the
    module doesn't exist, the module is generated into the
    comtypes.gen package.

    It is possible to delete the whole comtypes\gen directory to
    remove all generated modules, the directory and the __init__.py
    file in it will be recreated when needed.

    If comtypes.gen __path__ is not a directory (in a frozen
    executable it lives in a zip archive), generated modules are only
    created in memory without writing them to the file system.

    Example:

        GetModule("shdocvw.dll")

    would create modules named
    
       comtypes.gen._EAB22AC0_30C1_11CF_A7EB_0000C05BAE0B_0_1_1
       comtypes.gen.SHDocVw

    containing the Python wrapper code for the type library used by
    Internet Explorer.  The former module contains all the code, the
    latter is a short stub loading the former.
    """
    pathname = None
    if isinstance(tlib, basestring):
        # pathname of type library
        if not os.path.isabs(tlib):
            # If a relative pathname is used, we try to interpret
            # this pathname as relative to the callers __file__.
            frame = sys._getframe(1)
            _file_ = frame.f_globals.get("__file__", None)
            if _file_ is not None:
                directory = os.path.dirname(os.path.abspath(_file_))
                abspath = os.path.normpath(os.path.join(directory, tlib))
                # If the file does exist, we use it.  Otherwise it may
                # still be that the file is on Windows search path for
                # typelibs, and we leave the pathname alone.
                if os.path.isfile(abspath):
                    tlib = abspath
        logger.info("GetModule(%s)", tlib)
        pathname = tlib
        tlib = comtypes.typeinfo.LoadTypeLibEx(tlib)
    elif isinstance(tlib, (tuple, list)):
        # sequence containing libid and version numbers
        logger.info("GetModule(%s)", (tlib,))
        tlib = comtypes.typeinfo.LoadRegTypeLib(comtypes.GUID(tlib[0]), *tlib[1:])
    elif hasattr(tlib, "_reg_libid_"):
        # a COMObject implementation
        logger.info("GetModule(%s)", tlib)
        tlib = comtypes.typeinfo.LoadRegTypeLib(comtypes.GUID(tlib._reg_libid_),
                                                *tlib._reg_version_)
    else:
        # an ITypeLib pointer
        logger.info("GetModule(%s)", tlib.GetLibAttr())

    # create and import the module
    is_current, mod = _CreateWrapper(tlib, pathname)
    try:
        modulename = tlib.GetDocumentation(-1)[0]
    except comtypes.COMError:
        return mod
    if modulename is None:
        return mod
    modulename = modulename.encode("mbcs")

    # create and import the friendly-named module
    if is_current: 
        try:
            return _my_import("comtypes.gen." + modulename)
        except:
            pass
        # this way, the module is always regenerated if importing it
        # fails.  It would probably be better to check for the
        # existance of the module first with imp.find_module (but
        # beware of dotted names), and only regenerate if if not
        # found.  Other errors while importing should probably make
        # this function fail.
    if __verbose__:
        print "# Generating comtypes.gen.%s" % modulename
    # determine the Python module name
    fullname = _name_module(tlib)
    modname = fullname.split(".")[-1]
    code = "from comtypes.gen import %s\nglobals().update(%s.__dict__)\n" % (modname, modname)
    code += "__name__ = 'comtypes.gen.%s'" % modulename
    if comtypes.client.gen_dir is None:
        mod = new.module("comtypes.gen." + modulename)
        mod.__file__ = os.path.join(os.path.abspath(comtypes.gen.__path__[0]),
                                    "<memory>")
        exec code in mod.__dict__
        sys.modules["comtypes.gen." + modulename] = mod
        setattr(comtypes.gen, modulename, mod)
        return mod
    # create in file system, and import it
    ofi = open(os.path.join(comtypes.client.gen_dir, modulename + ".py"), "w")
    ofi.write(code)
    ofi.close()
    return _my_import("comtypes.gen." + modulename)

def _module_is_current(tlib, tlib_path, module_path):
    # If the timestamp of the typelibrary file is later the the
    # timestamp of the Python module the module is out of date and
    # needs to be regenerated.
    if tlib_path is None:
        # try to find pathname of type library
        from comtypes.typeinfo import QueryPathOfRegTypeLib
        libattr = tlib.GetLibAttr()
        try:
            tlib_path = QueryPathOfRegTypeLib(libattr.guid, libattr.wMajorVerNum, libattr.wMinorVerNum)
        except WindowsError:
            return True

    # Search for the actual typelib file (it seems Windows searches
    # along $PATH, although that is not documented)
    if not os.path.isfile(tlib_path) and not os.path.isabs(tlib_path):
        for directory in os.environ["PATH"].split(";"):
            what = os.path.join(directory, tlib_path)
            if os.path.isfile(what):
                tlib_path = what
                break

    if not os.path.isfile(tlib_path):
        # Cannot find the file, so cannot check timestamps.
        # Assume the module is current.
        return True

    return os.stat(module_path).st_mtime > os.stat(tlib_path).st_mtime

def _CreateWrapper(tlib, pathname=None):
    # helper which creates and imports the real typelib wrapper module.
    fullname = _name_module(tlib)
    try:
        return True, sys.modules[fullname]
    except KeyError:
        pass

    modname = fullname.split(".")[-1]
    is_current = True
    try:
        file_, module_path, desc = imp.find_module(modname, comtypes.gen.__path__)
    except ImportError:
        pass
    else:
        is_current = _module_is_current(tlib, pathname, module_path)
        if not is_current:
            print "# comtypes.gen.%s must be regenerated" % modname
        else:
            try:
                return True, imp.load_module(modname, file_, module_path, desc)
            finally:
                if file_:
                    file_.close()

    # generate the module since it doesn't exist or is out of date
    from comtypes.tools.tlbparser import generate_module
    if comtypes.client.gen_dir is None:
        import cStringIO
        ofi = cStringIO.StringIO()
    else:
        ofi = open(os.path.join(comtypes.client.gen_dir, modname + ".py"), "w")
    # use warnings.warn, maybe?
    if __verbose__:
        print "# Generating comtypes.gen.%s" % modname
    generate_module(tlib, ofi, pathname)

    if comtypes.client.gen_dir is None:
        code = ofi.getvalue()
        mod = new.module(fullname)
        mod.__file__ = os.path.join(os.path.abspath(comtypes.gen.__path__[0]),
                                    "<memory>")
        exec code in mod.__dict__
        sys.modules[fullname] = mod
        setattr(comtypes.gen, modname, mod)
    else:
        ofi.close()
        mod = _my_import(fullname)
        # why the reload here?
        reload(mod)
    return is_current, mod

################################################################

if __name__ == "__main__":
    # When started as script, generate typelib wrapper from .tlb file.
    GetModule(sys.argv[1])

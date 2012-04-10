# Fake _winreg implementation
# This is a mock implementation so that we can use _winreg from the unit tests
# without actually ever writing anything

import _winreg
from _winreg import REG_BINARY, REG_DWORD, REG_DWORD_LITTLE_ENDIAN, \
    REG_DWORD_BIG_ENDIAN, REG_EXPAND_SZ, REG_LINK, REG_MULTI_SZ, REG_NONE, \
    REG_RESOURCE_LIST, REG_FULL_RESOURCE_DESCRIPTOR, \
    REG_RESOURCE_REQUIREMENTS_LIST, REG_SZ, \
    KEY_ALL_ACCESS, KEY_WRITE, KEY_READ, KEY_EXECUTE, KEY_QUERY_VALUE, \
    KEY_SET_VALUE, KEY_CREATE_SUB_KEY, KEY_ENUMERATE_SUB_KEYS, KEY_NOTIFY, \
    KEY_CREATE_LINK
import logging
log = logging.getLogger("winreg.mock")
#log.setLevel(logging.DEBUG)

data = {}
""" The fake registry data.
    HKLM\Foo\Bar    <- a value in HKLM\Foo named Bar
    HKLM\Foo\Bar\   <- the default value in the key HKLM\Foo\Bar
    If the default value has a value of None, it's a placeholder to indicate
    that the key exists but there are no values.
"""

elevated = False
""" If true, allow writes to HKLM """

def access_str(bits):
    """ Return string representation of access mode bits """
    result = []
    write = {"SetValue": KEY_SET_VALUE,
             "CreateSubKey": KEY_CREATE_SUB_KEY}
    read = {"QueryValue": KEY_QUERY_VALUE,
            "EnumerateSubKeys": KEY_ENUMERATE_SUB_KEYS,
            "Notify": KEY_NOTIFY}
    if all(map(lambda x: bits & x, write.values() + read.values() + [KEY_CREATE_LINK])):
        return "AllAccess"
    if all(map(lambda x: bits & x, write.values())):
        result.append("Write")
    else:
        for name, bit in write.items():
            if bits & bit:
                result.append(name)
    if all(map(lambda x: bits & x, read.values())):
        result.append("Read")
    else:
        for name, bit in read.items():
            if bits & bit:
                result.append(name)
    if bits and KEY_CREATE_LINK:
        result.append("CreateLink")
    return ",".join(result) or "None"

class HKey(object):
    def __init__(self, path, access):
        log.debug('HKey(): "%s" access=%s', path, access_str(access))
        if not path.endswith("\\"):
            raise AssertionError("HKey created with path %s that doesn't end in backslash")
        self.path = path
        self.access = access

    def Close(self):
        self.access = 0

    def Detach(self):
        self.Close()

    def __enter__(self):
        return self
    def __exit__(self, *exc_info):
        self.Close()

def CloseKey(hkey):
    log.debug("CloseKey: %s", hkey.path)
    hkey.Close()

def ConnectRegistry(computer_name, key):
    raise WindowsError(50, "ERROR_NOT_SUPPORTED")

def CreateKey(key, sub_key):
    log.debug("CreateKey: %s, %s", key.path, sub_key)
    if not sub_key:
        return key
    # the actual access rules is more complex, but basically we can create
    # anything under HKCU, and nothing under HKLM (and we ignore the access
    # bits on the open handle)
    if key.path.startswith("HKLM") and not elevated:
        log.debug("CreateKey: access denied creating %s::%s (have %s)",
                  key.path, sub_key, access_str(key.access))
        raise WindowsError(5, "ERROR_ACCESS_DENIED")
    path = "\\".join(map(lambda x: x.strip("\\"), [key.path, sub_key, ""]))
    data[path] = None
    access = KEY_READ if path.startswith("HKLM") else KEY_ALL_ACCESS
    return HKey(path, access=access)

def DeleteKey(key, sub_key):
    log.debug("DeleteKey: %s, %s", key.path, sub_key)
    if key.path.startswith("HKLM") and not elevated:
        log.debug("DeleteKey: access denied deleting %s::%s (have %s)",
                  key.path, sub_key, access_str(key.access))
        raise WindowsError(5, "ERROR_ACCESS_DENIED")
    path = "\\".join(map(lambda x: x.strip("\\"), [key.path, sub_key, ""]))
    path_lower = path.lower()
    for k, v in data.items():
        if not k.lower().startswith(path_lower): continue # not relevant
        if k.lower() == path_lower:
            path = k
            if v is None:
                continue # empty stub
        log.warn("DeleteKey: path %s has subkeys or values %s = %r", path, k, v)
        raise WindowsError(4, "ERROR_TOO_MANY_OPEN_FILES")
    parent = path.rsplit("\\", 2)[0] + "\\"
    if not parent in data:
        # put in a stub for the parent
        log.debug("DeleteKey: deleted %s, adding parent %s", path, parent)
        data[parent] = None
    else:
        log.debug("DeleteKey: deleted %s", path)
    del data[path]

def DeleteValue(key, value):
    log.debug("DeleteValue: %s, %s", key.path, value)
    if (key.path.startswith("HKLM") and not elevated) or not (key.access & KEY_SET_VALUE):
        log.debug("DeleteValue: access denied deleting %s::%s (have %s)",
                  key.path, value, access_str(key.access))
        raise WindowsError(5, "ERROR_ACCESS_DENIED")
    if value is None:
        value = "" # default
    path = key.path + value
    for p in data.keys():
        if p.lower() == path.lower():
            log.debug("DeleteValue: deleting %s", p)
            del data[p]
            data[key.path] = None
            break
    else:
        raise WindowsError(2, "ERROR_FILE_NOT_FOUND")

def EnumKey(key, index):
    log.debug("EnumKey: %s, %s", key.path, index)
    if not key.access & KEY_ENUMERATE_SUB_KEYS:
        log.debug("EnumKey: access denied enumerting %s (have %s)",
                  key.path, access_str(key.access))
        raise WindowsError(5, "ERROR_ACCESS_DENIED")
    results = set()
    if key.path.startswith("HKCR"):
        partial = key.path[len("HKCR"):].lower()
        candidates = map(lambda x: ("%s\Software\Classes%s" % (x, partial)).lower(), ["HKCU", "HKLM"])
    else:
        candidates = [key.path.lower()]
    for path in candidates:
        for key in data.keys():
            if not key.lower().startswith(path): continue
            rest = key[len(path):].split("\\", 1)
            if len(rest) < 2: continue # this is a value
            results.add(rest[0])
    results = list(results)
    results.sort()
    log.debug("EnumKey: results=%r, index=%i/%i", results, index, len(results))
    if index >= len(results):
        log.debug("EnumKey: index %r not found", index)
        raise WindowsError(18, "ERROR_NO_MORE_FILES")
    log.debug("EnumKey: result=%s", results[index])
    return results[index]

def EnumValue(key, index):
    log.debug("EnumValue: %s, %s", key.path, index)
    if not key.access & KEY_QUERY_VALUE:
        log.debug("EnumValue: access denied enumerting %s (have %s)",
                  key.path, access_str(key.access))
        raise WindowsError(5, "ERROR_ACCESS_DENIED")
    results = {}
    if key.path.startswith("HKCR"):
        partial = key.path[len("HKCR"):].lower()
        candidates = map(lambda x: ("%s\Software\Classes%s" % (x, partial)).lower(), ["HKCU", "HKLM"])
    else:
        candidates = [key.path.lower()]
    for path in candidates:
        for key, value in data.items():
            if not key.lower().startswith(path): continue
            if key.lower() == path and value is None: continue
            rest = key[len(path):].split("\\", 1)
            if len(rest) > 1: continue # this is a value
            results[rest[0]] = data[key]
    keys = list(results)
    keys.sort()
    log.debug("EnumValue: results=%r, index=%i/%i", keys, index, len(keys))
    if index >= len(keys):
        log.debug("EnumValue: index %r not found", index)
        raise WindowsError(18, "ERROR_NO_MORE_FILES")
    value = results[keys[index]]
    log.debug("EnumValue: key=%s value=%r", keys[index], value)
    return (keys[index], value, REG_DWORD if isinstance(value, int) else REG_SZ)

def ExpandEnvironmentStrings(string):
    log.debug("ExpandEnvironmentStrings: %s", string)
    raise WindowsError(50, "ERROR_NOT_SUPPORTED")

def FlushKey(key):
    log.debug("FlushKey: %s", key.path)
    raise WindowsError(50, "ERROR_NOT_SUPPORTED")

def LoadKey(key):
    log.debug("LoadKey: %s", key.path)
    raise WindowsError(50, "ERROR_NOT_SUPPORTED")

def OpenKey(key, sub_key, res=0, sam=KEY_READ):
    log.debug("OpenKey: %s, %s, access=%s", key.path, sub_key, access_str(sam))
    if res != 0:
        log.debug("OpenKey got invalid res=%r (key=%s sub_key=%s)",
                  res, key.path, sub_key)
        raise WindowsError(87, "ERROR_INVALID_PARAMETER")
    if key.path.startswith("HKLM") and (sam & (KEY_SET_VALUE | KEY_CREATE_SUB_KEY)) and not elevated:
        log.debug(r"Attempted to open %s::%s with write", key.path, sub_key)
        raise WindowsError(5, "ERROR_ACCESS_DENIED")
    if not sub_key:
        path = key.path
    else:
        path = "\\".join(map(lambda x: x.strip("\\"), [key.path, sub_key, ""]))
    if path.startswith("HKCR"):
        partial = path[len("HKCR"):]
        candidates = [r"%s\Software\Classes%s" % (x, partial) for x in ["HKCU", "HKLM"]]
    else:
        candidates = [path]
    for candidate in candidates:
        if filter(lambda k: k.lower().startswith(candidate.lower()), data.keys()):
            break
    else:
        log.debug("OpenKey: path %s not found", path)
        raise WindowsError(2, "ERROR_FILE_NOT_FOUND")
    return HKey(path, access=sam)

def OpenKeyEx(*args, **kwargs):
    return OpenKey(*args, **kwargs)

def QueryInfoKey(key):
    log.debug("QueryInfoKey: %s", key.path)
    raise WindowsError(50, "ERROR_NOT_SUPPORTED")

def QueryValue(key, sub_key):
    log.debug("QueryValue: %s, %s", key.path, sub_key)
    if not key.access & KEY_QUERY_VALUE:
        log.debug(r"Access denied querying %s\%s", key.path, sub_key)
        raise WindowsError(5, "ERROR_ACCESS_DENIED")
    raise WindowsError(50, "ERROR_NOT_SUPPORTED")

def QueryValueEx(key, value_name):
    log.debug("QueryValueEx: %s, %s", key.path, value_name)
    if not key.access & KEY_QUERY_VALUE:
        log.debug(r"Access denied querying %s\%s", key.path, value_name)
        raise WindowsError(5, "ERROR_ACCESS_DENIED")
    path = r"%s\%s" % (key.path.strip("\\"), value_name or "")

    if path.startswith("HKCR"):
        partial = path[len("HKCR"):]
        if (r"HKCU\Software\Classes" + partial).lower() in map(lambda x: x.lower(), data.keys()):
            path = r"HKCU\Software\Classes" + partial
        else:
            path = r"HKLM\Software\Classes" + partial

    for key in data.keys():
        if path.lower() == key.lower():
            path = key
            break
    else:
        log.debug("QueryValueEx: value %s not found", path)
        raise WindowsError(2, "ERROR_FILE_NOT_FOUND")

    if data[path] is None:
        # dummy data to have a key with no default value
        log.debug("QueryValueEx: value %s is None", path)
        raise WindowsError(2, "ERROR_FILE_NOT_FOUND")
    elif isinstance(data[path], int):
        log.debug("QueryValueEx: %s: REG_DWORD %s", path, data[path])
        return (data[path], REG_DWORD)
    else:
        log.debug("QueryValueEx: %s: REG_SZ %s", path, data[path])
        return (str(data[path]), REG_SZ)

def SaveKey(key, file_name):
    log.debug("SaveKey: %s, %s", key.path, file_name)
    raise WindowsError(50, "ERROR_NOT_SUPPORTED")

def SetValue(key, sub_key, value_type, value):
    log.debug("SetValue: %s, %s, %s, %s", key.path, sub_key, value_type, value)
    raise WindowsError(50, "ERROR_NOT_SUPPORTED")

def SetValueEx(key, value_name, reserved, value_type, value):
    log.debug("SetValueEx: %s, %s, %s, %s", key.path, value_name, value_type, value)
    if reserved != 0:
        log.debug("SetValueEx got invalid reserved=%r (key=%s value_name=%s value=%r)",
                  reserved, key.path, value_name, value)
        raise WindowsError(87, "ERROR_INVALID_PARAMETER")
    if not (key.access & KEY_SET_VALUE):
        log.debug(r"Access denied setting %s\%s (have %s)",
                  key.path, value_name, access_str(key.access))
        raise WindowsError(5, "ERROR_ACCESS_DENIED")
    if value_name is None:
        value_name = "" # default
    if "\\" in value_name:
        log.debug(r"Can't set key %s with value name %s to %r",
                  key.path, value_name, value)
        raise WindowsError(50, "ERROR_NOT_SUPPORTED")
    path = "\\".join(map(lambda x: x.strip("\\"), [key.path, value_name]))
    if path.startswith("HKCR"):
        # write into the HKCU equivalent
        path = r"HKCU\Software\Classes" + path[len("HKCR"):]
    if value_type in (REG_SZ, REG_EXPAND_SZ):
        data[path] = str(value)
    elif value_type == REG_DWORD:
        data[path] = int(value)
    else:
        log.debug(r"Setting %s\%s to %r type %r is unsupported",
                  key.path, value_name, value, value_type)
        raise WindowsError(50, "ERROR_NOT_SUPPORTED")


def DisableReflectionKey(key):
    log.debug("DisableReflectionKey: %s", key.path)
    raise WindowsError(50, "ERROR_NOT_SUPPORTED")

def EnableReflectionKey(key):
    log.debug("EnableReflectionKey: %s", key.path)
    raise WindowsError(50, "ERROR_NOT_SUPPORTED")

def QueryReflectionKey(key):
    log.debug("QueryReflectionKey: %s", key.path)
    raise WindowsError(50, "ERROR_NOT_SUPPORTED")

HKEY_CLASSES_ROOT = HKey("HKCR\\", KEY_ALL_ACCESS)
HKEY_CURRENT_USER = HKey("HKCU\\", KEY_ALL_ACCESS)
HKEY_LOCAL_MACHINE = HKey("HKLM\\", KEY_READ)

# additional methods
def setData(newData):
    global data
    data = {}
    data.update(newData)
    # force the special keys that HKCR maps to to exist
    data["HKCU\\Software\\Classes\\"] = None
    data["HKLM\\Software\\Classes\\"] = None
    from pprint import pformat
    log.debug("setData:\n%s", pformat(data))
def getData():
    global data
    result = {}
    for key, value in data.items():
        if value is None: continue
        result[key] = value
    return result

__all__ = ["setData", "getData", "elevated"] + dir(_winreg)

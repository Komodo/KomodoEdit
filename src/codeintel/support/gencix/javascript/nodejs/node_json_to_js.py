#!/usr/bin/env python
# JSON-based Node documentation parser
# requires pyYaml for order/override files

import argparse
import logging
import json
import re
import os, subprocess
import textwrap
from pprint import pformat

DEFAULT_NODE_VERSION = "0.8.0"

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)

def striphtml(string, tags=["pre"]):
    for tag in tags:
        string = re.sub("<%s[^>]*>.*?</%s>" % (tag, tag),
                        "",
                        string,
                        flags=(re.IGNORECASE|re.DOTALL))
    string = re.sub("<[^>]*?>", "", string)
    return string.replace("&apos;", "'").replace("&quot;", '"')

def default_get(dictionary, *args):
    """ Helper to chain dict.get(arg, {}) since we can't make yaml use defaultdict """
    result = dictionary
    for arg in args:
        result = result.get(arg, {})
    return result

class Processor(object):
    def __init__(self, version=DEFAULT_NODE_VERSION, cache=False):
        self.version = version
        self.cache = cache
        self.data = {}
        self.overrides = {}
        version_str = version.replace(".", "_")
        for override_file in ("override_%s.yml" % (version_str,), "override.yml"):
            if os.path.exists(override_file):
                try:
                    import yaml
                    with open(override_file, "r") as f:
                        self.overrides = yaml.load(f)
                    log.warning("Loaded override file %s", override_file)
                except ImportError:
                    log.error("Failed to import yaml, overrides are disabled")
                break

    def _getFile(self, filename):
        """ Get the given file and return a file-like object """
        cache_name = "docs_%s_%s" % (self.version.replace(".", "_"), filename)
        if not os.path.exists(cache_name):
            import urllib
            if filename.endswith(".markdown"):
                url = "https://raw.github.com/joyent/node/v%s/doc/api/%s" % (self.version, filename)
            else:
                url = "http://nodejs.org/docs/v%s/api/%s" % (self.version, filename)
            if self.cache:
                log.info("Downloading from %s and saving to %s", url, cache_name)
                urllib.urlretrieve(url, cache_name)
            else:
                log.info("Downloading from %s (not saving)", url)
                return urllib.urlopen(url)
        else:
            log.info("Re-using existing documentation from %s", cache_name)
        return open(cache_name, "r")

    def getDocs(self, sections=[]):
        """ Read the contents of the appropriate documentation """
        # unfortunately, urllib.urlopen doesn't support __exit__
        # also, all.json is missing https :/
        if not sections:
            section_data = self._getFile("all.markdown")
            try:
                for line in section_data.readlines():
                    if not line.startswith("@include"):
                        continue
                    name = line.split(" ", 2)[1].strip()
                    sections.append(name)
            finally:
                section_data.close()
        found_sections = []
        for section in sections:
            f = self._getFile("%s.json" % (section,))
            try:
                section = self.overrides.get(section, {}).get("name", section)
                found_sections.append(section)
                self.data[section] = data = json.load(f)
                data["name"] = section
                section_overrides = self.overrides.get(section, {})
                if "vars" in data:
                    if not "globals" in data:
                        data["globals"] = data["vars"]
                    else:
                        data["globals"].extend(data["vars"])
                    del data["vars"]
                for kind in ["globals"]:
                    if kind in section_overrides:
                        for name, mapping in section_overrides[kind].items():
                            new_kind = mapping.get("kind")
                            if not new_kind:
                                continue
                            old_data = data.get(kind, [])
                            for item in old_data:
                                if item.get("name") == name:
                                    log.debug("converting %s %s %s to %s",
                                              section, kind, name, new_kind)
                                    if not new_kind in data:
                                        data[new_kind] = []
                                    data[new_kind].append(item)
                                    old_data.remove(item)
                                    break
                            else:
                                log.debug("Failed to override %s %s to %s",
                                          kind, name, new_kind)

                for module in data.get("modules", []):
                    mod_name = module.get("name")
                    module_overrides = default_get(section_overrides, "modules", mod_name)
                    if not module_overrides:
                        module_overrides = default_get(self.overrides, section, "module")
                    for kind in ("properties", "classes", "methods", "modules"):
                        for name, mapping in default_get(module_overrides, kind).items():
                            new_kind = mapping.get("kind")
                            if not new_kind:
                                continue
                            old_data = module.get(kind, [])
                            for item in old_data:
                                if item.get("name") == name:
                                    log.debug("converting %s::%s %s %s to %s",
                                              section, mod_name, kind, name, new_kind)
                                    if not new_kind in module:
                                        module[new_kind] = []
                                    module[new_kind].append(item)
                                    old_data.remove(item)
                                    break
            except:
                log.error("While loading section %s", section)
                raise
            finally:
                f.close()
        return found_sections

    @property
    def shortVersion(self):
        return ".".join(self.version.split(".", 2)[:2])

    def process(self, sections=[]):
        sections = self.getDocs(sections=sections)
        sections_written = 0
        for section in map(Section, sections):
            if section.name.startswith("appendix"):
                # skip "Appendix 1 - Third Party Modules"
                continue
            data = self.data.get(section.name)
            if not data:
                log.warn("Data for section %s not found", section.name)
                continue

            if not data.get('modules', []) + data.get('globals', []):
                log.warn("Section %s appears to be empty", section.name)
                continue

            dirname = os.sep.join(os.path.abspath(__file__).split(os.sep)[:-5] +
                                  ["lib", "codeintel2", "lib_srcs", "node.js",
                                   self.shortVersion])
            filename = os.path.join(dirname, "%s.js" % (section.name,))
            log.warning("Writing section %s to %s", section.name, filename)

            if not os.path.isdir(dirname):
                os.makedirs(dirname, mode=0755)

            overrides = self.overrides.get(section.name, {})

            with open(filename, "w") as f:
                for module_data in data.get("modules", []):
                    module = Module(module_data, section)
                    module_overrides = default_get(overrides, "modules", module.name)
                    if not module_overrides:
                        module_overrides = default_get(overrides, "module")
                    module.write(f, module_overrides)
                props = [GlobalProperty(d, section) for d in data.get("globals", [])]
                methods = [GlobalMethod(d, section) for d in data.get("methods", [])]
                toplevels = order(props + methods, section.name)
                for item in order(props + methods, section.name):
                    item.write(f, default_get(overrides, "globals", item.name))

                if "extra" in self.overrides.get(section.name, {}):
                    f.write("\n" + self.overrides[section.name]["extra"])

                f.write("\nexports = %s;\n\n" % (section.name,))

            sections_written += 1
        log.warn("Wrote docs for %r sections", sections_written)

class Node(object):
    def __init__(self, data=None):
        self.overrides = {}
        self.data = data

    @property
    def doc(self):
        lines = []
        for line in striphtml(self.data.get("desc", "")).splitlines():
            line = re.sub("\s+", " ", line)
            lines.append(line)
            if not line or line[-1] in ".:":
                break
        return "\n".join(textwrap.wrap("\n".join(lines), width=72))

    @property
    def name(self):
        return self.data["name"]

    @property
    def validName(self):
        """ Check whether the name is a valid JavaScript identifier
        See ECMAScript Ed 5 section 7.6
        """
        import unicodedata
        i = 0
        while i < len(self.name):
            try:
                c = self.name[i]
                u = unicodedata.category(unicode(c))
                if u in ("Lu", "Ll", "Lt", "Lm", "Lo", "Nl"):
                    continue
                if c in "$_":
                    continue
                if c == "\\":
                    if len(self.name) < i + 6:
                        return False
                    if self.name[i + 1] != "u":
                        return False
                    for j in range(i + 2, i + 6):
                        if self.name[j].lower() not in "0123456789abcdef":
                            return False
                    i = i + 5
                    continue
                if i != 0:
                    if u in ("Mn", "Mc", "Nd", "Pc"):
                        continue
                    if c in u"\u200c\u200d": # ZWNJ, ZWJ
                        continue
                return False
            finally:
                i = i + 1
        return True

    @property
    def methods(self):
        if not hasattr(self, "_methods"):
            self._methods = [Method(data, self)
                             for data in self.data.get("methods", [])]
        return self._methods

    @property
    def classes(self):
        if not hasattr(self, "_classes"):
            self._classes = [Class(data, self)
                             for data in self.data.get("classes", [])]
        return self._classes

    @property
    def properties(self):
        if not hasattr(self, "_properties"):
            # need to skip array accessors
            self._properties = [Property(data, self)
                                for data in self.data.get("properties", [])
                                if not data.get("name").startswith("[")]
        return self._properties

    @property
    def events(self):
        if not hasattr(self, "_events"):
            self._events = [Event(data, self)
                            for data in self.data.get("events", [])]
        return self._events

    @property
    def parentName(self):
        return self.parent.name

class Section(Node):
    def __init__(self, section):
        super(type(self), self).__init__()
        self.section = section
    def __repr__(self):
        return "<Section %r>" % (self.section,)
    @property
    def name(self):
        return self.section

class Module(Node):
    def __init__(self, data, parent):
        super(Module, self).__init__(data=data)
        self.parent = parent
        self._name = None

    @property
    def name(self):
        """ Get the module name, as used in require('x') """
        if self._name is not None:
            return self._name
        # look in the module description; strip out all the examples, first
        desc = re.sub("<pre>.*?</pre>", "", self.data.get("desc", ""), flags=re.DOTALL)
        # un-HTML-escape bits we care about
        desc = desc.replace("&apos;", "'").replace("&quot;", '"')
        # grab it from the description
        match = re.search(r"""<code>require\((['"])([^'"]*)\1\)""", desc)
        if match is not None:
            return match.group(2)
        return self.data["name"].lower()

    def write(self, f, overrides={}):
        if "name" in overrides:
            self._name = overrides["name"]
        if not self.validName:
            log.warn("Skipping invalid identifier %s", self.name)
            return
        f.write("/**\n")
        for line in filter(bool, self.doc.splitlines()):
            f.write(" * %s\n" % (line.rstrip(),))
        if "__proto__" in overrides:
            f.write(" * @base {%s}\n" % (overrides.get("__proto__")),)
        f.write(" */\n")
        f.write("var %s = {};\n" % (self.name,))
        for child in order(self.methods + self.classes + self.properties, self.name):
            child.write(f, overrides=overrides.get(child.name, {}))

class Method(Node):
    def __init__(self, data, parent):
        super(Method, self).__init__(data=data)
        self.parent = parent
        self.overrides = {}

    def write(self, f, overrides={}):
        log.debug("Method %s: overrides=%s", self.name, pformat(overrides))
        self.overrides = overrides
        if not self.validName:
            log.warn("Skipping invalid identifier %s", self.name)
            return
        f.write("\n/**\n")
        for line in filter(bool, self.doc.splitlines()):
            f.write(" * %s\n" % (line.rstrip(),))
        for param in self.params:
            if param.name:
                param.overrides = self.overrides.get("params", {}).get(param.name, {})
                f.write(" * @param %s\n" % (param.desc,))
        if self.returnDescription:
            f.write(" * @returns %s\n" % (self.returnDescription,))
        f.write(" */\n")
        param_names = [p.name for p in self.params if p.name]
        f.write("%s = function(%s) {}\n" % (self.declaration, ", ".join(param_names)))
        for child in order(self.methods + self.properties, self.name):
            child.write(f, overrides=overrides.get(child.name, {}))

    @property
    def parentName(self):
        return self.parent.name

    @property
    def signature(self):
        return self.data.get("signatures", [{}])[0]

    @property
    def params(self):
        for param in self.signature.get("params", []):
            if "(" in param["name"] or ")" in param["name"]:
                # asser.ok() is broken, skip these arguments
                continue
            yield Param(param, self)

    @property
    def declaration(self):
        return "%s.%s" % (self.parentName, self.name)

    @property
    def returnDescription(self):
        if "returns" in self.overrides:
            typeInfo = self.overrides["returns"]
            if not " " in typeInfo:
                typeInfo = "{%s}" % (typeInfo,)
            return typeInfo

        desc = self.signature.get("return", {}).get("desc")
        typeInfo = None
        if desc:
            desc = desc.strip()
            if desc.endswith(" object"):
                typeInfo = desc[:-len(" object")].rstrip()

        if not desc and self.doc:
            doc = " ".join(self.doc.splitlines())
            # remove the link syntax
            doc = re.sub(r"\[([^\]]+)\]\[\]", r"\1", doc)
            match = re.search("(?:^|\.)\s*Returns (.*)", doc, re.MULTILINE)
            if not match:
                match = re.search("(?:^|\.)\s*Creates (.*)", doc, re.MULTILINE)
            if match:
                desc = match.group(1).split(". ")[0].strip().rstrip(".").rstrip()
                log.debug("desc: %s", desc)

        if desc:
            match = re.match("(?:a )new (\S+)(?: object)?", desc)
            if match is None:
                match = re.match("(?:an )instance of (.*)", desc)
            if match is not None:
                typeInfo = match.group(1)
            elif re.match("(?:an )array of", desc):
                typeInfo = "Array"
            elif re.match("(?:the )number of", desc):
                typeInfo = "Number"
            elif desc.endswith(" string value"):
                typeInfo = "String"

        if typeInfo and desc:
            if not "." in typeInfo:
                # try to match for class names in the current module
                module = self.parent
                while module and not isinstance(module, Module):
                    module = module.parent
                # some times we want capitalization, see buffer.Buffer.slice
                for typeCandidate in (typeInfo, typeInfo.capitalize()):
                    fullType = "%s.%s" % (module.name, typeCandidate)
                    for clazz in module.classes:
                        if clazz.name == fullType:
                            typeInfo = fullType
                            break

            return "{%s} %s" % (typeInfo, desc)
        return desc

        return None

class GlobalMethod(Method):
    @property
    def declaration(self):
        return "%s" % (self.name,)

class InstanceMethod(Method):
    @property
    def parentName(self):
        return "%s.prototype" % (self.parent.name,)

class Param(object):
    def __init__(self, data, method=None, overrides={}):
        self.data = data
        self.method = method
        self.overrides = overrides

    @property
    def name(self):
        # strip of trailing periods because some of them are "arguments..."
        # to indicate an unspecified number of them
        return self.data["name"].rstrip(".")

    @property
    def desc(self):
        value = self.overrides.get("default")
        typeDesc = self.overrides.get("type")
        log.debug("Param.desc: %s: %s (%r)", self.name, pformat(self.overrides), value)

        if not value and self.method and self.method.doc:
            doc = " ".join(self.method.doc.splitlines())
            match = re.search("%s \(defaults to ([^)]+)\)" % (self.name,), doc)
            if match:
                value = match.group(1)

        desc = [d.strip() for d in self.data.get("desc", "").split(", ")]
        if not value:
            descDefault = filter(lambda x: x.startswith("Default: "), desc)
            if descDefault:
                # have a default value in the description
                value = descDefault[0].split(":", 1)[1].strip()
        if typeDesc is None:
            for t in ("Number", "String"):
                if t in desc:
                    typeDesc = t
                    break

        if not value and self.method and self.method.doc:
            doc = " ".join(self.method.doc.splitlines())
            match = re.search("%s defaults to ([^\s)]+)" % (self.name,), doc)
            if match:
                value = match.group(1).rstrip(".") # strip sentence-ending periods

        if not typeDesc:
            typeDesc = self.data.get("type")

        if value is not None and typeDesc is None:
            if value.startswith("'") or value.startswith('"'):
                typeDesc = "String"
            elif (value + "_")[0] in "0123456789":
                typeDesc = "Number"
            elif value.endswith(".length"):
                typeDesc = "Number"
            elif value in ("true", "false"):
                typeDesc = "Boolean"

        if typeDesc and typeDesc.endswith(" object"):
            typeDesc = typeDesc[:-len(" object")]

        result = self.name
        if value is not None:
            result += "=%s" % (value,)
        if typeDesc is not None:
            result += " {%s}" % (typeDesc,)
        return result

class Event(Node):
    def __init__(self, data, parent):
        super(Event, self).__init__(data=data)
        self.parent = parent

    @property
    def doc(self):
        lines = []
        for line in striphtml(self.data["desc"], tags=["pre"]).splitlines():
            line = re.sub("\s+", " ", line)
            if not line:
                continue
            if re.match("function \([^)]*\) { *}", line):
                continue
            lines.append(line)
        return "\n".join(textwrap.wrap("\n".join(lines), width=72))

    @property
    def params(self):
        param_overrides = None
        if isinstance(self.overrides, (list, tuple)):
            param_overrides = self.overrides
        elif isinstance(self.overrides, dict) and "params" in self.overrides:
            param_overrides = self.overrides["params"]
        if param_overrides is not None:
            params = []
            for param in param_overrides:
                if isinstance(param, dict):
                    name = param.keys()[0]
                    value = param[name]
                    data = {"name": name }
                    if isinstance(value, dict):
                        if "default" in value:
                            data["desc"] = "Default: %s" % (value["default"],)
                        if "type" in value:
                            data["type"] = value["type"]
                    else:
                        data["type"] = str(value)
                else:
                    data = {"name": str(param)}
                params.append(Param(data))
            return params

        for line in striphtml(self.data["desc"]).splitlines():
            match = re.match("function \(([^)]*)\)", line)
            if match:
                break
        else:
            return []
        params = [p.strip() for p in match.group(1).split(",")]
        return [Param({"name": p}) for p in params]

    def write(self, f, overrides={}):
        self.overrides = overrides
        log.debug("Event %s: overrides=%r", self.name, self.overrides)
        if not self.validName:
            log.warn("Skipping invalid identifier %s", self.name)
            return
        f.write("\n/**\n")
        for line in filter(bool, self.doc.splitlines()):
            f.write(" * %s\n" % (line.rstrip(),))
        for param in self.params:
            if param.name:
                f.write(" * @param %s\n" % (param.desc,))
        f.write(" */\n")
        param_names = ", ".join([p.name for p in self.params])
        f.write("%s.__events__.%s = function(%s) {};\n" % (self.parentName,
                                                           self.name,
                                                           param_names))

class Class(Node):
    def __init__(self, data, module):
        super(type(self), self).__init__(data=data)
        self.parent = module

    @property
    def name(self):
        name = self.data["name"]
        if not "." in name:
            name = "%s.%s" % (self.parent.name, name)
        if "name" in self.overrides:
            return self.overrides["name"]
        return name

    def write(self, f, overrides={}):
        self.overrides = overrides
        log.debug("Class %s: overrides=%s", self.name, pformat(overrides))
        f.write("\n/**\n")
        for line in filter(bool, self.doc.splitlines()):
            f.write(" * %s\n" % (line.rstrip(),))
        f.write(" * @constructor\n")
        f.write(" */\n")
        f.write("%s = function() {}\n" % (self.name,))
        if "__proto__" in overrides:
            protos = overrides["__proto__"]
            if not isinstance(protos, (list, tuple)):
                protos = [protos]
            for proto in protos:
                f.write("%s.prototype = new %s();\n" % (self.name, proto))
        for child in order(self.methods + self.properties + self.classMethods, self.name):
            child.write(f, overrides=overrides.get(child.name, {}))
        if self.events:
            f.write("\n/** @__local__ */ %s.__events__ = {};\n" % (self.name,))
            for child in self.events:
                child.write(f, overrides=default_get(overrides, "__events__", child.name))

    @property
    def methods(self):
        return [InstanceMethod(data, self) for data in self.data.get("methods", [])]

    @property
    def classMethods(self):
        return [Method(data, self) for data in self.data.get("classMethods", [])]

    @property
    def properties(self):
        results = []
        for data in self.data.get("properties", []):
            if data.get("name").startswith("["):
                continue # skip array accessors
            results.append(InstanceProperty(data, self))
        return results

class Property(Node):
    def __init__(self, data, parent):
        super(Property, self).__init__(data=data)
        self.parent = parent

    def __repr__(self):
        if self.parent:
            return "<Property %s of %r>" % (self.name, self.parent)
        else:
            return "<Property %s>" % (self.name,)

    @property
    def typeDesc(self):
        """ JSDoc-style parameter description for this parameter """
        typeDesc = None
        for expr in ("The (\S+) object",
                     "The [^.]+ as a (\S+)\.",
                     "A (boolean|string|number)",
                     "The (string) representation",):
            match = re.match(expr, self.doc, re.IGNORECASE)
            if match:
                break
        if match is not None:
            typeDesc = match.group(1)
        if typeDesc in ("string", "boolean", "number"):
            typeDesc = typeDesc.capitalize()
        return typeDesc

    def write(self, f, overrides={}):
        log.debug("Property %s: %r", self.name, overrides)
        if not self.validName:
            log.warn("Skipping invalid identifier %s", self.name)
            return
        f.write("\n/**\n")
        for line in filter(bool, self.doc.splitlines()):
            f.write(" * %s\n" % (line.rstrip(),))
        typeDesc = overrides.get("type", self.typeDesc)
        if typeDesc:
            if not " " in typeDesc:
                typeDesc = "{%s}" % (typeDesc,)
            f.write(" * @type %s\n" % (typeDesc,))
        f.write(" */\n")
        defaultValue = overrides.get("value", None)
        for piece in self.data.get("shortDesc", "").split(", "):
            piece = piece.strip()
            if piece == "Number" and not defaultValue:
                defaultValue = 0
            elif piece.startswith("Default: "):
                defaultValue = piece.split(":", 1)[1].strip()
        if defaultValue is not None:
            f.write("%s = %s;\n" % (self.declaration, defaultValue))
        else:
            f.write("%s = %s;\n" % (self.declaration, self.defaultValue))

        if "__proto__" in overrides:
            f.write("%s.__proto__ = %s;\n" % (self.name, overrides["__proto__"]))

        for child in order(self.methods + self.classes + self.properties, self.name):
            child.write(f, overrides.get(child.name, {}))

        if self.events:
            f.write("\n/** @__local__ */ %s.__events__ = {};\n" % (self.name,))
            for child in self.events:
                child.write(f, overrides=default_get(overrides, "__events__", child.name))

    @property
    def declaration(self):
        return "%s.%s" % (self.parentName, self.name)

    @property
    def defaultValue(self):
        return "0"

class GlobalProperty(Property):
    @property
    def declaration(self):
        return "var %s" % (self.name,)

    @property
    def defaultValue(self):
        # not sure why global props (or, to be specific, |process|) is weird...
        return "{}"

class InstanceProperty(Property):
    @property
    def parentName(self):
        return "%s.prototype" % (self.parent.name,)

def order(items, parent_name):
    """Order the given names for easier comparision
    @param item {list of Node} The names to order
    @param parent_name {str} The containing item
    @returns {list} The ordered items
    """
    try:
        import yaml
    except ImportError:
        return items
    if not os.path.exists("order.yml"):
        return items
    with open("order.yml", "r") as f:
        sort_data = yaml.load(f.read())
    if parent_name in sort_data:
        order = sort_data[parent_name]
        log.debug("using ordering for %s: %r", parent_name, order)
        def c(a, b):
            if a.name in order and b.name in order:
                return cmp(order.index(a.name), order.index(b.name))
            if a.name in order or b.name in order:
                return -1 if a.name in order else 1
            return cmp(a.name, b.name)
        items = sorted(items, c)
    log.debug("order result: %r", [c.name for c in items])
    return items

def main():
    parser = argparse.ArgumentParser(description='Node.js documentation to Komodo CIX parser.')
    parser.add_argument("--cache", dest="cache", action="store_true",
                        help="save downloaded JSON source if missing")
    parser.add_argument("--version", "-V", dest="version", action="store",
                        default=DEFAULT_NODE_VERSION,
                        help="version of Node documentation to parse, e.g. '%s'" % (DEFAULT_NODE_VERSION,))
    parser.add_argument("--verbose", "-v", dest="verbosity", action="count", default=2,
                        help="enable additional output")
    parser.add_argument("sections", nargs='*',
                        help="sections to write; by default, all sections are written")
    args = parser.parse_args()
    log.setLevel(50 - args.verbosity * 10)
    processor = Processor(version=args.version, cache=args.cache)
    processor.process(sections=args.sections)

if __name__ == '__main__':
    main()

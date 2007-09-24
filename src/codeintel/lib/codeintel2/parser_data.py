# 
# Copyright (c) 2005-2006 ActiveState Software Inc.
#
# Contributors:
#   Eric Promislow (EricP@ActiveState.com)
#
# 

VAR_KIND_UNKNOWN = 0
VAR_KIND_GLOBAL = 1
VAR_KIND_CLASS = 2
VAR_KIND_CLASSVAR = 3
VAR_KIND_INSTANCE = 4
VAR_KIND_LOCAL = 5
VAR_KIND_ALIAS = 6

class Name_LineNum:
    def __init__(self, name, line_num, type=None):
        self.line_num = line_num
        self.name = name
        self.type = type

class VarInfo:
    def __init__(self, line_num, type=None):
        self.line_num = line_num
        self.type = type

def update_collection(coll, name, line_num, type=None, attributes=None):
    if not coll.has_key(name):
        coll[name] = VarInfo(line_num, type)
    elif coll[name].type is None and type is not None:
        coll[name].type = type
    if attributes and coll['attributes'] is None:
        coll['attributes'] = attributes

class Node:
    def __init__(self, line_num, class_name=None):
        self.children = []
        self.line_num = line_num
        self.indentation = 0
        self.doc_lines = []
        self.imports = [] # require and load stmts
        self.includes = []  # include stmts

        self.class_vars = {}
        self.instance_vars = {}
        self.local_vars = {}
        self.aliases = {}
        if class_name: self.class_name = class_name
        
    def append_node(self, new_node):
        self.children.append(new_node)

    def set_line_end_num(self, line_end_num):
        self.lineend = line_end_num        
    
    def dump_kids(self, indent_level):
        for c in self.children:
            c.dump(indent_level + 2)
            
    def dump2(self, node_type_name, indent_level, *call_backs):
        print "%s %s %s - line %r:%r" % (" " * indent_level, node_type_name, self.name, self.line_num, getattr(self, 'lineend', '???'))
        if len(self.doc_lines) > 0:
            print "%s Documentation: %s" % (" " * (indent_level + 2), "\n".join(self.doc_lines))
        if len(self.imports) > 0:
            for m in self.imports:
                print "%s Import: %s" % (" " * (indent_level + 2), m.name)
        if len(self.includes) > 0:
            for m in self.includes:
                print "%s Include: %s" % (" " * (indent_level + 2), m.name)
        self.dump_collection('Globals', 'global_vars', indent_level + 2)
        self.dump_collection('Locals', 'local_vars', indent_level + 2)
        self.dump_collection('Instance vars', 'instance_vars', indent_level + 2)
        self.dump_collection('Class vars', 'class_vars', indent_level + 2)
        for cb in call_backs:
            cb()
        self.dump_kids(indent_level)
        
    def dump_collection(self, label, attr, indent_level):
        if hasattr(self, attr):
            collection = getattr(self, attr)
            if len(collection) > 0:
                print "%s %s: " % (" " * indent_level, label)
                for name, varInfo in collection.items():
                    line, type = varInfo.line_num, varInfo.type
                    if type:
                        typeString = " [" + type + "]"
                    else:
                        typeString = ""
                    print "%s %s - line %s%s" % (" " * (indent_level + 2), name, line, typeString)
            
    
class ClassNode(Node):
    def __init__(self, the_name, line_num, unused=False):
        self.name = the_name
        self.classrefs = []
        Node.__init__(self, line_num, "Class")
        
    def add_classrefs(self, class_ref_name, line_num, classref_type=None):
        if class_ref_name not in [x[0] for x in self.classrefs]:
            self.classrefs.append([class_ref_name, line_num, classref_type])
            
    def has_classref(self, name):
        return name in [x[0] for x in self.classrefs]
        
    def dump(self, indent_level):
        def cb():
            classrefs = self.classrefs
            if len(classrefs) > 0:
                for ref in classrefs:
                    print "%sClassref %s - line %s" % (" " * (indent_level + 2),
                                                       ref[0], ref[1])
        self.dump2("Class", indent_level, cb)
    
class FileNode(Node):
    def __init__(self):
        Node.__init__(self, 0)
        self.global_vars = {}  # Easy to get at
        
    def dump(self):
        self.name = ""
        self.dump2("file", 0)
        return
        indent_level = 0
        if len(self.imports) > 0:
            for m in self.imports:
                print "%s Import: %s" % (" " * (indent_level + 2), m.name)
        if len(self.includes) > 0:
            for m in self.includes:
                print "%s Include: %s" % (" " * (indent_level + 2), m.name)
        self.dump_kids(0)
        
class ArgNode:
    def __init__(self, name, extra_info, arg_attrs):
        self.name = name
        self.extra_info = extra_info
        self.arg_attrs = arg_attrs
    def get_full_name(self):
        if self.extra_info:
            return self.extra_info + self.name
        return self.name

class MethodNode(Node):
    def __init__(self, the_name, line_num, is_constructor=False):
        self.name = the_name
        self.is_constructor = is_constructor
        self.signature = ""
        self.args = []
        self.is_classmethod = False
        Node.__init__(self, line_num, "Method")

        # extra_info for Ruby, arg_attrs for Tcl's "args", like Ruby's "*args"
    def add_arg(self, name, extra_info=None, arg_attrs=None):
        self.args.append(ArgNode(name, extra_info, arg_attrs))
        
    def dump(self, indent_level):
        def cb():
            args = self.args
            for arg in args:
                print "%sArg %s" % (" " * (indent_level + 2), arg.get_full_name())
        self.dump2("Method", indent_level, cb)
        if len(self.signature) > 0:
            print "%sSignature %s" % (" " * (indent_level + 2), self.signature)

class ModuleNode(Node):
    def __init__(self, the_name, line_num, unused=False):
        self.name = the_name
        Node.__init__(self, line_num, "Module")
        
    def dump(self, indent_level):
        self.dump2("Module", indent_level)

class VariableNode(Node):
    def __init__(self, the_name, line_num):
        self.name = the_name
        Node.__init__(self, line_num, "Variable")
        
    def dump(self, indent_level):
        self.dump2("Module", indent_level)

class BlockNode(Node):
    def __init__(self, the_name, line_num):
        self.name = the_name
        Node.__init__(self, line_num, "Block")
        
    def dump(self, indent_level):
        self.dump2("Module", indent_level)

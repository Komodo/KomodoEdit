#!ruby
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

# object_to_cix.rb -- Library to return CIX for a binary object

module CIX

class Node
  attr_accessor :_inner_modules, :_inner_classes, :_inner_constants, :_included_modules, :_methods, :_instance_variables, :_class_variables, :_superclass
  attr_reader :name, :ilk

  # If ignoring case doesn't break a tie, go by the case.
  
  @@sort_name = Proc.new {|a, b| (a.name.downcase <=> b.name.downcase) || (a.name <=> b.name) }
  @@sort_str = Proc.new {|a, b| (a.to_s.downcase <=> b.to_s.downcase) || (a.to_s <=> b.to_s) }

  def Node.name_sorter
    @@sort_name
  end

  def ilk_check(ilk)
    if ilk == "module"
      return "namespace"
    end
    return ilk
  end
  
  def initialize(name, ilk)
    @name = name
    @ilk = ilk_check(ilk)
    @_inner_modules = []
    @_inner_classes = []
    @_inner_constants = {}
    @_included_modules = []
    @_methods = []
    @_instance_variables = []
    @_class_variables = []
    @_superclass = nil
  end

  def Node.h(str)
    return str.gsub("&", "&amp;").gsub("<", "&lt;").gsub(">", "&gt;")
  end

  def h(str); Node.h(str); end
  
  def dump_node(ind)
    ws = " " * ind
    curr_line = %Q(#{ws}<scope ilk="#{@ilk}" name="#{h(@name)}")
    if @_included_modules.size > 0
      curr_line += %Q( mixinrefs="#{h(@_included_modules.sort(&@@sort_str).join(" "))}")
    end
    if @_superclass
      curr_line += %Q( classrefs="#{h(@_superclass)}")
    end
    curr_line += %Q(>)
    @@lines << curr_line
    ws2 = ws + "  "
    @_inner_modules.sort(&@@sort_name).each {|mod| mod.dump_node(ind + 2)}
    @_inner_classes.sort(&@@sort_name).each {|mod| mod.dump_node(ind + 2)}
    @_methods.sort(&@@sort_str).each {|method_name|
      curr_line = %Q(#{ws2}<scope ilk="function" name=)
      if method_name == "initialize"
        curr_line += %Q("new" attributes="__ctor__")
      else
        curr_line += %Q("#{h(method_name)}")
      end
      curr_line += %Q( />)
      @@lines << curr_line
    }
    @_instance_variables.sort(&@@sort_str).each {|var|
      @@lines << %Q(#{ws2}<variable name="#{h(var)}" attributes="__instancevar__" />)
    }
    @_class_variables.sort(&@@sort_str).each {|var|
      @@lines << %Q(#{ws2}<variable name="#{h(var)}" attributes="__local__" />)
    }
    @_inner_constants.sort(&@@sort_str).each {|name, val|
      @@lines << %Q(#{ws2}<variable name="#{h(name)}" attributes="__const__" citdl="#{h(val.class.to_s)}"/>)
    }

    @@lines << %Q(#{ws}</scope>)
  end

  def dump_tree(libname, ind)
    ws = " " * ind
    @@lines = []
    dump_node(ind + 2)
    @@lines.join("\n")
  end
end

class Analyzer
  @@special_class_classes = %W/Class Object Module/

  def initialize()
    @visited = {'class' => {}, 'module' => {}}
  end

  def clear
    @visited['class'] = {}
    @visited['module'] = {}
  end
  
  def walk(obj_type, name, mc_obj)
    clear()
    return walk_module_or_class(obj_type, name, mc_obj)
  end

  def walk_module_or_class(obj_type, name, mc_obj)
    node = Node.new(name, obj_type)
    # Find ilk-specific traits first
    _instance_methods = mc_obj.instance_methods
    if obj_type == 'module':
        node._methods = (_instance_methods + mc_obj.public_methods + mc_obj.singleton_methods).uniq - Object.methods
    else
      if @@special_class_classes.member?(name)
        node._methods = _instance_methods
      else
        if mc_obj.superclass
          mc_sc = mc_obj.superclass
          node._superclass = mc_sc.name
          node._methods = _instance_methods - mc_sc.instance_methods
        else
          node._methods = _instance_methods
        end
        mc_obj.included_modules.each {|inc_mod|
          if inc_mod != Kernel
            node._methods -= inc_mod.public_methods
          end
        }
      end
    end
    if !@@special_class_classes.member?(name)
        mc_obj.constants.each {|c|
          begin
            obj = mc_obj.module_eval(c)
            # print "Class(#{c}) = #{obj.class}\n"
            case obj.class.to_s
            when 'Module'
              if ! @visited[obj_type].has_key?(c)
                @visited[obj_type][name] = nil
                node._inner_modules << walk_module_or_class("module", c, obj)
              end
            when 'Class'
              if ! @visited[obj_type].has_key?(c)
                @visited[obj_type][name] = nil
                node._inner_classes << walk_module_or_class("class", c, obj)
              end
            else
              node._inner_constants[c] = obj
            end
          rescue SyntaxError
            #XXX Return error messages in test context
            $stderr.write("Trouble eval'ing #{c}:#{$!}\n")
          end
        }
    end
    node._included_modules = mc_obj.included_modules
    node._instance_variables = mc_obj.instance_variables
    node._class_variables = mc_obj.class_variables
    return node
  end

  def sort_trees(trees)
    sorted_trees = trees.sort {|a, b|
      if a.ilk == b.ilk
        a.name.downcase <=> b.name.downcase
      elsif a.ilk == "namespace"
        -1
      else
        1
      end
    }
    sorted_trees
  end

end # class

end # module

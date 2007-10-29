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

class ObjWalker
  @@special_class_classes = %W/Class Object Module/
  
  def initialize(builtin1_names, is_binary_module=false)
    @info = {}
    @builtin1_names = builtin1_names
    @cix_generator = CixGenerator.new
    @is_binary_module = is_binary_module
    @verbose = false
  end
  
  def clear
    @visited = {}
  end
  
  def get_cix2(name, ind)
    info = @info[name]
    return nil unless info
    unless info['ilk'] && (info['name'] || info['full_name'])
      $stderr.write("Can't get reasonable info for #{name}\n")
      return
    end
    cix = @cix_generator.get_cix_from_obj(info, ind)
    return cix
  end
  
  def get_full_cix
    trees = names.map{|name| get_cix2(name, 2)}
    trees.join("\n")
  end
  
  def names()
    return @info.keys
  end
  
  def walk(obj_type, name, mc_obj)
    puts "#{obj_type}:#{name}: clearing" if @verbose
    clear()
    return walk_module_or_class(obj_type, name, mc_obj, name)
  end
  
  private

  def make_hash(a)
    h = {}
    a.each{|x| h[x] = {}}
    h
  end
  
  def walk_module_or_class(obj_type, name, mc_obj, fq_name)
    node = {'name' => name, 'ilk' => obj_type.downcase}
    # Find ilk-specific traits first
    _instance_methods = mc_obj.instance_methods(false)
    if obj_type == 'Module'
      node['instance_methods'] = make_hash(_instance_methods + mc_obj.public_methods(false) - Object.methods)
    else
      if @@special_class_classes.member?(name)
        method_names = _instance_methods
      else
        if mc_obj.superclass
          mc_sc = mc_obj.superclass
          node['superclass'] = mc_sc.name
          _instance_methods -= (mc_sc.instance_methods + mc_sc.public_methods(false))
        end
        if name != "Object"
            _instance_methods -= Object.methods
        end
        method_names = _instance_methods
        mc_obj.included_modules.each {|inc_mod|
          if inc_mod != Kernel
            method_names -= inc_mod.public_methods
          end
        }
      end
      node['instance_methods'] = make_hash(method_names)
      if node['instance_methods'].size > 0
          puts "Instance methods for class #{name}: #{node['instance_methods'].keys.join(", ")}" if @verbose
      end
    end
    class_methods = mc_obj.singleton_methods(false)
    node['class_methods'] = make_hash(mc_obj.singleton_methods(false))
    if !@@special_class_classes.member?(name)
      node['inner_scopes'] = []
      node['constants'] = []
      mc_obj.constants.each {|c|
        begin
          obj = mc_obj.module_eval(c)
          fq_child_name = "#{fq_name}.#{c}"
          # print "Class(#{c}) = #{obj.class}\n" if @verbose
          if [Class, Module].member?(obj.class)
            obj_id = obj.object_id
            if !@is_binary_module && !@visited.has_key?(obj_id) && !@builtin1_names.member?(c)
              $stderr.write("visit #{obj_type} #{c}, fq_child_name=#{fq_child_name}\n") if @verbose
              @visited[obj_id] = nil
              node['inner_scopes'] << walk_module_or_class(obj.class.name, c, obj, fq_child_name)
            end
          else
            node['constants'] << {'name' => c, 'citdl' => obj.class.name}
          end
        rescue SyntaxError
          #XXX Return error messages in test context
          # $stderr.write("Trouble eval'ing #{c}:#{$!}\n")
        end
      }
    end
    node['included_modules'] = mc_obj.included_modules.map{|mod|mod.name}
    return node
  end
end

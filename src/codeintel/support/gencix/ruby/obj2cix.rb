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

# obj2cix.rb
#
# This class is responsible for walking simple objects
# and returning CIX2

class CixGenerator
  
  def get_cix_from_obj(info, ind)
    @lines = []
    if info['blobname']
      ws =  " " * ind
      @lines << %Q(#{ws}<scope ilk="blob" lang="Ruby" name="#{h(info['blobname'])}">\n)
      ind2 = ind + 2
    else
      ind2 = ind
    end
    if ['FileTable', 'RBConfig'].member?(info['name'])
        puts "Break here"
    end
    dump_class_module_node(info, ind2)
    if info['blobname']
      @lines << %Q(#{ws}</scope>\n)
    end
    cix = @lines.join("\n")
  end
  
  def h(str) # used by the rails cix generator.
    s2 = str.gsub("&", "&amp;").gsub("<", "&lt;").gsub(">", "&gt;").
      gsub('"', "&quot;").gsub("'", "&apos;")
    return escape_nl(s2)
  end
  
  private
  
  
  def dump_class_module_node(info, ind)
    ws =  " " * ind
    name = info['name'] || info['full_name']
    curr_line = %Q(#{ws}<scope ilk="#{ilk_normalize(info['ilk'])}" name="#{h(name)}")
    if info['doc']
      curr_line += %Q( doc="#{h(info['doc'])}")
    end
    if info['superclass']
      curr_line += %Q( classrefs="#{h(info['superclass'])}")
    end
    curr_line += ">"
    @lines << curr_line
    (info['inner_scopes'] || []).sort {|a, b| a['name'].downcase <=> b['name'].downcase}.each {|inner_scope|
      dump_class_module_node(inner_scope, ind + 2)
    }
    if info['included_modules']
        # Most of the time don't bother doing this.
        if false and info['superclass']
            # Object mixes in Kernel, so nothing else needs to.
            info['included_modules'] -= ["Kernel"]
        end
        ws2 = ws + "  "
        info['included_modules'].sort.each { |mod_name|
          @lines << %Q(#{ws2}<import symbol="#{h(mod_name)}" />)
        }
    end
    info['class_methods'].keys.sort.each { |method_name|
      method_info = info['class_methods'][method_name]
      dump_method_info(method_name, method_info, ind + 2, true)
    }
    info['instance_methods'].keys.sort.each { |method_name|
      method_info = info['instance_methods'][method_name]
      dump_method_info(method_name, method_info, ind + 2, false)
    }
    info['constants'].sort {|a, b| a['name'] <=> b['name'] }.each { |item|
      dump_constant_info(item['name'], item['citdl'], ind + 2)
    }
    @lines << %Q(#{ws}</scope>\n)
  end
  
  def dump_constant_info(const_name, citdl, ind)
    ws =  " " * ind
    curr_line = %Q(#{ws}<variable name="#{h(const_name)}")
    attrs = ["__const__"]
    curr_line += %Q( attributes="#{attrs.join(" ")}")
    curr_line += %Q( citdl="#{h(citdl)}")
    curr_line += %Q(/>)
    @lines << curr_line
  end
  
  def dump_method_info(method_name, info, ind, is_class_method)
    ws =  " " * ind
    curr_line = %Q(#{ws}<scope ilk="function" name="#{h(method_name)}")
    if info['params'] && info['params'].size > 0
      curr_line += %Q( signature="#{h(info['params'].chomp)}")
    end
    attrs = []
    if is_class_method or info['is_singleton']
      attrs << "__classmethod__"
      if method_name == "new"
        attrs << "__ctor__"
      end
    end
    if info['visibility'] == "private"
      attrs << "private" #XXX Any other terms?
    end
    if attrs.size > 0
      curr_line += %Q( attributes="#{attrs.join(" ")}")
    end
    if info['doc']
      curr_line += %Q( doc="#{h(info['doc'])}")
    end
    curr_line += %Q(/>)
    @lines << curr_line
  end
  
  def escape_nl(s)
    s2 = s.gsub("\r", '').gsub("\n", '&#x0a;')
    return s2
  end
  
  def ilk_normalize(ilk)
    if ilk == "module"
      return "namespace"
    end
    return ilk
  end
end

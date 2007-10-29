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

# builtins-gencix.rb
# Usage: ruby builtins-gencix.rb

# Output: pieces of CIX for the ruby builtin modules and objects
# 
# Returns:
# 0 status on success
# 1 on command-line failure
# 2 on other failures (utter failure)


core_things = (Object.constants.grep(/[a-z]/) + ['GC', 'IO']).uniq

require 'object_to_cix'

require 'optparse'
opt_parser = OptionParser.new
opts = {}
opt_parser.on('-o', '--output FILE', String) { |val| opts['output'] = val }

rest = opt_parser.parse(ARGV)
if rest.size == 1
  obj_name = rest[0]
else
  obj_name = nil
end


trees = []
analyzer = CIX::Analyzer.new
if obj_name
  begin
    obj = eval(obj_name)
    trees << analyzer.walk(obj.class.to_s.downcase, obj_name, obj)
  rescue
    $stderr.write("Can't eval '#{obj_name}': #{$!}\n")
  end
else
  core_modules = []
  core_classes = []
  core_things.each do |obj_name|
    begin
      obj = eval(obj_name)
      if obj.class == Class
        core_classes << ['class', obj_name, obj]
      elsif obj.class == Module
        core_modules << ['module', obj_name, obj]
      else
        $stderr.write("Don't know where to place #{obj.class.to_s} #{obj_name}\n")
      end
    rescue
      $stderr.write("Can't eval #{obj.class.to_s} #{obj_name}: #{$!}\n")
    end
  end
  core_modules.each {|mod|
    begin
      trees << analyzer.walk_module_or_class(*mod)
    rescue
      $stderr.write("Can't analyze module #{mod[1]}: #{$!}\n")
    end
  }
  core_classes.each {|cls|
    begin
      trees << analyzer.walk_module_or_class(*cls)
    rescue
      $stderr.write("Can't eval class #{cls[1]}: #{$!}\n")
    end
  }
end

sorted_trees = analyzer.sort_trees(trees)
cix_items = []
sorted_trees.each do |tree|
  if tree
    cix_items << tree.dump_tree("*", 4)
  end
end

if cix_items.size > 0

if opts['output']
  begin
    fout = File.open(opts['output'], 'w')
  rescue
    $stderr.write("#{$0}: can't open file #{opts['output']}: #{$!}\n")
    exit(1)
  end
else
  fout = $stdout
end

  # Don't return the codeintel or file tags
  fout.write(%Q(    <scope ilk="blob" lang="Ruby" name="*">\n))
  fout.write(cix_items.join("\n") + "\n")
  fout.write(%Q(    </scope>\n))
end

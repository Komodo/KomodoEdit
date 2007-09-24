#!ruby
# Copyright (c) 2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

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

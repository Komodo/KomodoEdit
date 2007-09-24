#!ruby
# Copyright (c) 2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# binary-gencix.rb
# Usage: ruby binary-gencix.rb [-o output file] library-name
#
# The <library-name> arg should include any necessary directories
# off the Ruby search path, and exclude the ".so" suffix.

# Examples:
# ruby binary-gencix.rb dbm # writes output to stdout
# ruby binary-gencix.rb -o racc/cparse.cix racc/cparse
#
# Returns:
# 0 status on success
# 1 on command-line failure
# 2 if it can't process the library

# Run this out-of-process because it looks at the
# changes in loaded constants after loading a module
# to determine which names the module imports.

# Running this out-of-process lets us check for timeouts
# as well.

require 'object_to_cix'

require 'optparse'
opt_parser = OptionParser.new
opts = {}
opt_parser.on('-o', '--output FILE', String) { |val| opts['output'] = val }

rest = opt_parser.parse(ARGV)
if rest.size != 1
  $stderr.write("Usage: #{$0} [-o output-file] library\n")
  exit(1)
end

def get_obj(libname)
  before_constants = Object.constants
  begin
    require libname
  rescue LoadError
    $stderr.write("Error: #{$!}\n")
    return nil
  end
  after_constants = Object.constants
  diff_constants = after_constants - before_constants
  items = []
  accepted_types = [Module, Class]
  diff_constants.each do |obj_name|
    begin
      obj = eval(obj_name)
      if accepted_types.member?(obj.class)
        # Use order expected by Analyzer#walk_module_or_class
        items << [obj.class.to_s.downcase, obj_name, obj]
      end
    rescue SyntaxError
      $stderr.write("binary-gencix: can't eval '#{obj_name}' in library '#{libname}'\n")
    end
  end
  return items
end

# Have to open the output file before changing to safe mode
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

#XXX
# untaint the name of the library before loading it.
libname = rest[0][0 .. -1].untaint
$SAFE = 2

items = get_obj(libname)
cix_items = []
if items.size > 0
  analyzer = CIX::Analyzer.new
  trees = items.map do |item|
    # $stderr.write("Walking item #{item[0]} '#{item[1]}'\n")
    analyzer.walk(*item)
  end
  sorted_trees = analyzer.sort_trees(trees)
  sorted_trees.each do |tree|
    if tree
      cix_items << tree.dump_tree(libname, 4)
    end
  end
else
  $stderr.write("No items found for module #{libname}\n")
  exit(1)
end

if cix_items.size > 0
  # Don't return the codeintel or file tags
  fout.write(%Q(    <scope ilk="blob" lang="Ruby" name="#{CIX::Node.h(libname)}">\n))
  fout.write(cix_items.join("\n") + "\n")
  fout.write(%Q(    </scope>\n))
end

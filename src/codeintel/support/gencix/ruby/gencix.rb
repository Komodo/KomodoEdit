#!ruby
# Copyright (c) 2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# gencix.rb
# Usage: ruby gencix.rb [-o output file] library-name
#
# The <library-name> arg should include any necessary directories
# off the Ruby search path, and exclude the ".so" suffix.

# Examples:
# ruby gencix.rb dbm # writes output to stdout
# ruby gencix.rb -o racc/cparse.cix racc/cparse
#
# Returns:
# 0 status on success
# 1 on command-line failure
# 2 if it can't process the library

  
  def doit(libname)
    before_constants = Object.constants
    begin
      require libname
    rescue LoadError
      $stderr.write("Error: #{$!}\n")
      return nil
    end
    after_constants = Object.constants
    diff_constants = after_constants - before_constants
    tree = nil
    if diff_constants.size == 0
      # Try to eval it -- it's always loaded
      begin
        guess_name = libname.sub(/\.\w+$/, '').capitalize
        mod = eval(guess_name)
        tree = walk_module_or_class(mod.class.to_s, guess_name, mod)
      rescue
        $stderr.write("Library #{libname} is already loaded -- specify the obj name and retry\n")
        exit 2
      end
    else
      diff_constants.each {|mod_name|
        mod = eval(mod_name)
        if mod.class.to_s == 'Module'
          tree = walk_module_or_class('module', mod_name, mod)
        elsif mod.class.to_s == 'Class'
          tree = walk_module_or_class('class', mod_name, mod)
        else
          $stderr.write("Not sure how to work with class #{mod.class}\n")
        end
      }
    end
    return tree
  end
  


require 'optparse'
opt_parser = OptionParser.new
opts = {}
opt_parser.on('-o', '--output FILE', String) { |val| opts['output'] = val }

rest = opt_parser.parse(ARGV)
if rest.size != 1
  $stderr.write("Usage: #{$0} [-o output-file] library\n")
  exit(1)
end

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

analyzer = Analyzer.new
# untaint the name of the library before loading it.
libname = rest[0][0 .. -1].untaint
$SAFE = 2
ruby_tree = analyzer.doit(libname)
if ruby_tree
  Node.dump_tree(ruby_tree, libname, fout)
  exit(0)
else
  # Now that we're in safe mode we can't delete the created file.
  exit(2)
end

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

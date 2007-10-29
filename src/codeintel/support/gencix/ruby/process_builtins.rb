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

# process_builtins.rb -- Introspect the builtin modules and classes
# that we didn't find YAML docs on.
#
# 

core_things = (Object.constants.grep(/[a-z]/) + ['GC', 'IO']).uniq - %w/Runner ObjWalker/

require 'obj_collector'
require 'obj2cix'

class Runner
  def initialize(all_names)
    @info = {}
    @objWalker = ObjWalker.new(all_names)
    @cixgen = CixGenerator.new
  end

  def walk(name)
    begin
      obj = eval(name)
    rescue => ex
      $stderr.write("Error: #{ex}\n")
      obj = nil
    end
    if obj
      if [Class, Module].member?(obj.class)
        @info[name] = @objWalker.walk(obj.class.name, name, obj)
      else
        $stderr.write("Don't know what to do with #{obj.class.name} #{name}\n")
      end
    end
  end
  
  def size
      return @info.size
  end
  
  def get_cix2()
      trees = []
      @info.each {|name, obj|
          trees << @cixgen.get_cix_from_obj(obj, 2)
      }
      trees.join("\n")
  end
end

require 'optparse'
opt_parser = OptionParser.new
opts = {}
opt_parser.banner = "Usage: #{$0} [options] [object names ...](default: all)"
opt_parser.on('--db-dir DIR', String) { |val| opts['db-dir'] = val }
opt_parser.on('--output-dir DIR', String) { |val| opts['output-dir'] = val }
opt_parser.on('-o', '--output-file FILE', String) { |val| opts['output-file'] = val }
opt_parser.on('-v', '--verbose') { |val| opts['verbose'] = val }
opt_parser.on('-w', '--warnings') { |val| opts['warnings'] = val }

opt_parser.on_tail("-h", "--help", "Show this message") do
    puts opt_parser
    puts ""
    puts "   Object names should be in terms of Ruby names, not modules"
    puts "   e.g.: 'CGI::Session', not 'cgi/session'"
    exit(1)
end
begin
  module_names = opt_parser.parse(ARGV)
rescue => ex
  $stderr.write("#{$0}: Error: #{ex.to_s}\n\n")
  opt_parser.parse('-h') # Better way to call usage?
end
verbose = opts['verbose']
warnings = opts['warnings']

datadir = opts['output-dir'] || "tmp"
dbdir = opts['db-dir'] || "tmp"
begin
  all_names_1 = File.open("#{dbdir}/top_names_builtin_1.txt") {|io| io.read.split(/\r?\n/)}
rescue
  all_names_1 = []
end
begin
  all_names_2 = File.open("#{dbdir}/top_names_stdlib_1.txt") {|io| io.read.split(/\r?\n/)}
rescue
  all_names_2 = []
end
all_names = (all_names_1 + all_names_2)

runner = Runner.new(all_names)
if module_names.size > 0
  module_names.each {|name|
    if all_names.member?(name)
      $stderr.write("Already have info on #{name}\n") if warnings
    else
      runner.walk(name)
    end
  }
else
  final_core_names = core_things - all_names
  if verbose
    $stderr.write("Still need to know about #{final_core_names.join(', ')}\n")
  end
  final_core_names.each {|name|
    runner.walk(name)
  }
end
#
#puts 12.3e-4e6.class
#
#a3 = 12.3e-41; a = 10
#j = e13
#k = .e14
#l = 0.e14
#l2 = 0.E+15
#l3 = -12.E-223
#l5 = 0x182354.E22
#m1 = 0x22e-eEx34
#m2 = 123.456e-78e+22
#

cix = runner.get_cix2()
if runner.size == 0
    if verbose || warnings
        $stderr.write("No items to emit\n")
    end
    exit(0)
end
if opts['output-file']
  if opts['output-file'] == "-"
    fout = $stdout
  else
    fout = File.open(opts['output-file'], "w")
  end
elsif module_names.size >= 1
  fout = $stdout
else
  fout = File.open("#{datadir}/builtin_2.cix", "w")
end
fout.write(%Q(<scope ilk="blob" lang="Ruby" name="*">\n))
fout.write(cix)
fout.write(%Q(</scope>\n))
fout.close() if fout != $stdout

if module_names.size == 0
  File.open("#{dbdir}/all_names_builtin_2.txt", "w") {|io|
        io.write(final_core_names.join("\n"))
        io.write("\n")
    }
end

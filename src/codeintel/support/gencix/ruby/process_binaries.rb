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

# process_binaries.rb -- instantiate binary modules, and if we didn't
# find info on their modules in the YAML docs, introspect and generate CIX


require 'obj_collector'
require 'obj2cix'
    
class Runner
  @@accepted_types = [Module, Class]
  def initialize(all_names, options)
    @objWalker = ObjWalker.new(all_names, true)
    @cixgen = CixGenerator.new
    @all_names = all_names
    @module_items = []
    @options = options
  end

  # Find out what names the module exposes, and instantiate them
  def examine(f, given_on_cmd_line)
    if f[-3 .. -1] != ".so"
      return
    elsif File.basename(f) =~ /^(?:tcl)?tk/
      $stderr.write("Skipping tk library #{f}\n") if @options['verbose']
      return
    end
    libname = normalize(f)
    $stderr.write("Analyzing #{libname} (#{f})\n") if @options['verbose']
    before_constants = Object.constants
    begin
      require libname
    rescue LoadError
      $stderr.write("Error(#{__LINE__}): loading #{libname}: #{$!}\n")
      return
    rescue TypeError
      $stderr.write("TypeError(#{__LINE__}): while loading #{libname}: #{$!}.  Continuing...\n")
      return
    end
    after_constants = Object.constants
    diff_constants = after_constants - before_constants - @all_names
    #puts diff_constants
    diff_constants.each {|obj_name|
      begin
        if @all_names.member?(obj_name)
          $stderr.write("#{$0}: Skipping binary library for module #{obj_name}\n") \
            if @options['warnings']
        end
        obj = eval(obj_name)
        @module_items << [File.basename(f, '.*'), obj_name, obj]
      rescue
        $stderr.write("#{$0}: can't eval '#{obj_name}' in library '#{f}'\n") if \
          @options['warnings'] or @options['verbose']
        obj = nil
      end
    }
    end
    
    def size
      return @module_parts.size
    end

  def walk_items
    @module_parts = {}
    @module_items.each {|file_basename, obj_name, obj|
      (@module_parts[file_basename] ||= []) << @objWalker.walk(obj.class.name, obj_name, obj)
    }
  end

  def get_cix2()
      trees = []
      @module_parts.sort{|a, b|a[0].downcase <=> b[0].downcase}.each { | file_basename, obj_list|
          trees << %Q(  <scope ilk="blob" lang="Ruby" name="#{file_basename}">)
          obj_list.sort {|a,b| a['name'] <=> b['name']}.each {|obj|
              puts obj['name']
              trees << @cixgen.get_cix_from_obj(obj, 4)
              puts "Done"
          }
          trees << %Q(  </scope>\n)
      }
      trees.join("\n")
  end
  
  def names()
      names = []
      @module_parts.values.each {|mod|
          mod.each {|item| names << item['name']}
      }
      names
  end

  def walk(name)
    begin
      obj = eval(name)
    rescue => ex
      $stderr.write("Error(#{__LINE__}): #{ex}\n")
      obj = nil
    end
    if obj
      if [Class, Module].member?(obj.class)
        
        puts ">> @objWalker.walk(#{obj.class.name}, #{name}"
        @module_parts[name] = @objWalker.walk(obj.class.name, name, obj)
        puts "<< Done"
      else
        $stderr.write("Don't know what to do with #{obj.class.name} #{name}\n")
      end
    end
  end
  
  def normalize(f)
    return f.sub(/.so$/, '')
  end
end

require 'optparse'
opt_parser = OptionParser.new
opts = {}
opt_parser.banner = "Usage: #{$0} [options] [module names ...](default: all)"
opt_parser.on('--db-dir DIR', String) { |val| opts['db-dir'] = val }
opt_parser.on('--output-dir DIR', String) { |val| opts['output-dir'] = val }
opt_parser.on('-o', '--output-file FILE', String) { |val| opts['output-file'] = val }
opt_parser.on('--library-dir FILE', String) { |val| opts['library-dir'] = val }
opt_parser.on('-v', '--verbose') { |val| opts['verbose'] = val }
opt_parser.on('-w', '--warnings') { |val| opts['warnings'] = val }
opt_parser.on('--skip-wrap-single') { |val|   opts['skip-wrap-single'] = val }
opt_parser.on_tail("-h", "--help", "Show this message") do
    puts opt_parser
    puts ""
    puts "   Binary libraries should be in terms of system names, not modules"
    puts "   e.g.: 'digest' or 'zlib'"
    exit(1)
end

begin
  module_names = opt_parser.parse(ARGV)
rescue => ex
  $stderr.write("#{$0}: Error: #{ex.to_s}\n\n")
  opt_parser.parse('-h') # Better way to call usage?
  module_names = []
end
verbose = opts['verbose']
warnings = opts['warnings']

datadir = opts['output-dir'] || "tmp"
dbdir = opts['db-dir'] || "tmp"

all_names = []
name_files = %w/top_names_stdlib_1 top_names_builtin_1 
                top_names_stdlib_1 all_names_builtin_2/
name_files.map{|base|
  begin
    all_names += File.open("#{dbdir}/#{base}.txt"){|io| io.read.split(/\n/)}
  rescue => ex
    $stderr.write("#{$0}: Warning: #{ex}\n") if warnings || verbose
    []
  end
}

runner = Runner.new(all_names, opts)
if module_names.size > 0
    module_names.each {|f|  
      runner.examine(f, true)
    }
else
  if opts['library-dir']
    libdirs = [opts['library-dir']]
  else
    libdirs = $:.clone.sort{|a,b| a.size <=> b.size}
    libdirs.delete_at(0) if libdirs[0] == "."
    origdirs = libdirs.clone
    libdirs.delete_if {|dir| origdirs.find{|pfx| pfx != dir && dir[pfx]}}
    if libdirs.size == 0
      $stderr.write("#{$0}: Error: no system binary dir specified, and none found\n")
      opt_parser.parse('-h')
    end
  end
  require 'find'
  libdirs.each {|libdir|
      Find.find(libdir) {|f|
        runner.examine(f, false)
    }
  }
end

runner.walk_items()
if module_names.size == 0
  File.open("#{dbdir}/binary_names3.txt", "w") {|io|
        io.write(runner.names.join("\n"))
        io.write("\n")
    }
end

cix = runner.get_cix2()
full_size = runner.size
if full_size == 0
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
  fout = File.open("#{datadir}/binaries_3.cix", "w")
end

wrap_text = (full_size > 1 || !opts['skip-wrap-single'])
fout.write("<wrap1>\n") if wrap_text
fout.write(cix)
fout.write("</wrap1>\n") if wrap_text


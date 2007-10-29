#!/usr/bin/env ruby
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

# Command-line:
# ruby [-rubygems] create_rails_cix.rb -o <output-file> [-v -w]

# Create a rails environment, walk the modules, write out a CIX file.

require 'obj_collector'
require 'obj2cix'

class Runner
  
  TREETYPE_MIRROR = 1
  TREETYPE_STREAMLINED = 2
  def initialize(all_names, options)
    @objWalker = ObjWalker.new(all_names, false) # No binary (.so) modules.
    @cixgen = CixGenerator.new
    @all_names = all_names
    @module_items = []
    @options = options
    @verbose = @options['verbose']
    @warnings = @options['warnings']
    @std_class_info = {}
    tree_type = options.delete("tree-type")
    case tree_type
    when "mirror"
      @tree_type = TREETYPE_MIRROR
    when "streamlined"
      @tree_type = TREETYPE_STREAMLINED
    else
      @tree_type = tree_type
    end
    @tree_type ||= TREETYPE_STREAMLINED
    if @tree_type != TREETYPE_STREAMLINED
      raise "--tree-type = #{@tree_type} not yet supported"
    end
  end
  
  def load_env
    #XXX Set rubygems?  Set up a lib option?
    before_constants = Object.constants

    # Requires for the semi-built-in classes that
    require 'cgi'
    require 'date'
    require 'logger'
    require 'pathname'
    builtin_classes = %w/Array CGI Date Exception FalseClass Hash Integer
        Logger NilClass Numeric Object Pathname Proc
        Range String Symbol Time TrueClass/.map{|name| [name, eval(name)]}
    # From doing
    # grep '^[     ]*class' *.rb | tr "#" " " |cut -d " "  -f 2 | sort -u
    
    before_builtin_class_info = {}
    builtin_classes.each {|c, obj|
      before_builtin_class_info[c] = {
        'class_methods' => obj.singleton_methods,
        'instance_methods' => obj.instance_methods
      }
    }    
    
    puts "About to load environment..." if @options['verbose']
    
    require 'rubygems'
    require 'rails/version'
    require 'active_support'
    require 'active_record'
    require 'action_controller'
    require 'action_mailer'
    require 'action_web_service'
    puts "Done" if @options['verbose']
    
    after_constants = Object.constants
    diff_constants = (after_constants - before_constants).grep(/^Act/).sort
    expected_names = %w/ActionController ActionMailer ActionView
                      ActionWebService ActiveRecord ActiveSupport/.sort
    if diff_constants != expected_names
      raise RuntimeError("Expected names <#{expected_names.join(", ")}>, got
                #{diff_constants.join(", ")}>")
    end
    expected_names.each {|n|
      if !diff_constants.member?(n)
        raise RuntimeError, "Didn't load module #{n}"
      end
    }
    puts "Final top-level names: #{expected_names.sort.join("\n")}" if @options['verbose']
    expected_names.each {|obj_name|
      begin
        if @all_names.member?(obj_name)
          $stderr.write("#{$0}: Skipping binary library for module #{obj_name}\n") if \
            @options['warnings']
        end
        obj = eval(obj_name)
        @module_items << [obj_name, obj]
      rescue
        $stderr.write("#{$0}: can't eval '#{obj_name}' in library '#{f}'\n") if \
          @options['warnings'] or @options['verbose']
        obj = nil
      end
    }
    
    after_builtin_class_info = {}
    @diff_builtin_class_info = {}
    @diff_builtin_class_info['Object'] = {
        'class_methods' => (Object.singleton_methods - before_builtin_class_info['Object']['class_methods']).sort,
        'instance_methods' => (Object.instance_methods - before_builtin_class_info['Object']['instance_methods']).sort
      }    
    new_obj_class_methods = Object.singleton_methods - before_builtin_class_info['Object']['class_methods']
    new_obj_inst_methods = Object.singleton_methods - before_builtin_class_info['Object']['class_methods']
    builtin_classes.each {|c, obj|
        next if c == "Object"
      @diff_builtin_class_info[c] = {
        'class_methods' => (obj.singleton_methods - before_builtin_class_info[c]['class_methods'] -  @diff_builtin_class_info['Object']['class_methods']).sort,
        'instance_methods' => (obj.instance_methods - before_builtin_class_info[c]['instance_methods'] -  @diff_builtin_class_info['Object']['instance_methods']).sort
      }        
    }
  end
  
  def get_cix
    trees = [%Q(<codeintel version="2.0" name="Rails" description="Rails version #{Rails::VERSION::STRING}">),
             %Q(  <file lang="Ruby" path="rails.cix">),
             %Q(    <scope ilk="blob" lang="Ruby" name="rails">)]
    @module_parts.sort{|a, b|a[0].downcase <=> b[0].downcase}.each { | file_basename, obj|
      puts "get cix for #{obj['name']}..." if @options['verbose']
      trees << @cixgen.get_cix_from_obj(obj, 6).chomp
      puts "Done" if @options['verbose']
    }
    @diff_builtin_class_info.sort {|a,b| a[0] <=> b[0]}.each do |c, info|
      diffs = @diff_builtin_class_info[c]
      if diffs['class_methods'].size > 0 || diffs['instance_methods'].size > 0
        trees << %Q(      <scope ilk="class" name="#{c}">)
        ws = ' ' * 8
        trees += get_method_cix(diffs['class_methods'], true, ws)
        trees += get_method_cix(diffs['instance_methods'], false, ws)
        trees << %Q(      </scope>)
      end
    end
    trees << %Q(    </scope>)
    trees << %Q(  </file>)
    trees << %Q( </codeintel>)
    trees.join("\n")
  end
  
  def get_method_cix(methods, is_class_method, ws)    
    methods.map {|name| sprintf(%Q(#{ws}<scope ilk="function" name="#{@cixgen.h(name)}"%s />),
                  is_class_method ? ' attributes="__classmethod__"' : '')
    }
  end

  # For each of the top-level things T,
  # Find all instances of T::X...::ClassMethods and ...::InstanceMethods
  # (for X != "Base")
  # and hoist them into T::Base's class and instance methods

  def hoist_methods
    @module_parts.each do |mod_name, mod_info|
        base = find_base_module(mod_info)
        if (base = find_base_module(mod_info))
            puts "Hosting module #{mod_name}..." if @verbose
            hoist_module_methods(base, mod_info, true)
            puts "Done" if @verbose
        elsif @verbose
          puts "Couldn't find #{mod_name}::Base"
        end
    end
  end
  
  def walk_items
    @module_parts = {}
    @module_items.each {|obj_name, obj|
      puts "Walking module #{obj_name}..." if @options['verbose']
      @module_parts[obj_name] = @objWalker.walk(obj.class.name, obj_name, obj)
      puts "... done" if @options['verbose']
    }
  end

  private
  
  def find_base_module(mod_info)
    mod_info['inner_scopes'].each {|inner_mod|
      return inner_mod if inner_mod['name'] == "Base"
    }
    nil
  end
    
  def hoist_module_methods(base_mod, parent_mod, at_top_level)
    parent_mod['inner_scopes'].each do |mod_info|
      case mod_info['name']
      when "Base" && at_top_level
        next
      when "ClassMethods"
        puts "Found #{mod_info['name']}" if @verbose
        transfer_methods(base_mod, mod_info, 'class_methods')
      when "InstanceMethods"
        puts "Found #{mod_info['name']}" if @verbose
        transfer_methods(base_mod, mod_info, 'instance_methods')
      else
        hoist_module_methods(base_mod, mod_info, false)
      end
    end
  end

  def transfer_methods(base_mod, mod_info, method_type)
    begin
    base_mod[method_type].merge!(mod_info['class_methods'])
    base_mod[method_type].merge!(mod_info['instance_methods'])
    rescue
      puts "Stopped here: $!"
    end
  end
end


require 'optparse'
opt_parser = OptionParser.new
opts = {}
opt_parser.banner = "Usage: #{$0} [options] [module names ...](default: all)"
opt_parser.on('--rails-dir DIR', String) { |val| opts['rails-dir'] = val }
opt_parser.on('-o', '--output-file FILE', String) { |val| opts['output-file'] = val }
opt_parser.on('-v', '--verbose') { |val| opts['verbose'] = val }
opt_parser.on('-w', '--warnings') { |val| opts['warnings'] = val }
opt_parser.on('--tree-type', String) { |val| opts['tree-type'] = val }
opt_parser.on_tail("-h", "--help", "Show this message") do
    puts opt_parser
    puts ""
    puts "   Binary libraries should be in terms of system names, not modules"
    puts "   e.g.: 'digest' or 'zlib'"
    exit(1)
end

begin
  extra = opt_parser.parse(ARGV)
rescue => ex
  $stderr.write("#{$0}: Error: #{ex.to_s}\n\n")
  opt_parser.parse('-h') # Better way to call usage?
  extra = []
end
verbose = opts['verbose']
warnings = opts['warnings']
if opts.has_key?('rails-dir')
  $:.unshift(opts['rails-dir'])
  opts.delete('rails-dir')
end

all_names = []
runner = Runner.new(all_names, opts)
runner.load_env
runner.walk_items
runner.hoist_methods
cix = runner.get_cix

if opts['output-file']
  fout = File.open(opts['output-file'], "w")
else
  fout = $stdout
end
fout.write(cix)
fout.close

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

# make_big_file.rb
#
# Write out a text file with info on each object in ri
#

require 'find'
require 'yaml'
# Bring in the YAML types.
require 'rdoc/markup/simple_markup/to_flow'
# require 'rdoc/markup/simple_markup/fragments'

require 'obj2cix'

class RiWalker
  @@simple_terms = %w/name full_name superclass/
  @@simple_method_terms = %w/visibility is_singleton aliases name full_name/
  
  @@dont_require = {
    "Test::Unit" => Module,
  }
  @@match_em = Regexp.new('<em>(.*?)</em>', Regexp::MULTILINE)
  @@match_b = Regexp.new('<b>(.*?)</b>', Regexp::MULTILINE)
  @@match_tt = Regexp.new('<tt>(.*?)</tt>', Regexp::MULTILINE)
  
  # should default be 'class' or 'namespace'?
  @@classname_to_ilk = Hash.new(Class.name.downcase)
  @@classname_to_ilk[Class] = Class.name.downcase
  @@classname_to_ilk[Module] = "namespace"
  
  def initialize(dbdir)
    @info = {"builtin" => {}, "stdlib" => {}}
    ruby_ver = RUBY_VERSION.split('.')[0 .. 1].join('.')
    @prefixes = $:.map {|x| x.sub(%r(/lib/.*), '')}.
      uniq.map {|p| "#{p}/share/ri/#{ruby_ver}/system"}.
      find_all{|dir| File.directory?(dir)}
    @cix_generator = CixGenerator.new
    @builtin_names = File.open("#{dbdir}/builtin_names_1.txt"){|io| io.read.split(/\r?\n/)}
  end
  
  def get_cix2(name, which, ind)
    info = @info[which][name]
    return nil unless info
    unless info['ilk'] && (info['full_name'] || info['name'])
      $stderr.write("Can't get reasonable info for #{name}\n")
      return
    end
    cix = @cix_generator.get_cix_from_obj(info, ind)
    return cix
  end
  
  def get_cix2_with_test(name, ind)
    if @info["builtin"].has_key?(name)
      return get_cix2(name, "builtin", ind)
    else
      return get_cix2(name, "stdlib", ind)
    end
  end
  
  def get_full_cix(which)
    trees = names(which).map{|name|
      get_cix2(name, which, 2)
    }
    trees.join("\n")
  end
  
  def names(which)
    return @info[which].keys
  end
  
  def size
    return @info.inject(0){|sum, k| sum + k[1].size}
  end
  
  def this_size(which)
    return @info[which].size
  end
  
  def top_names
    return @info.inject([]){|lst, k| lst + @info[k[0]].keys()}.uniq
  end
  
  # reorder the tree so instances of Foo::Bar are placed inside Foo, etc.
  def reorder(which)
    flat_names = self.names(which)
    fixed_names = flat_names.map{|n| [n.scan("::").size, n]}.sort{|a,b| b[0] <=> a[0]}
    fixed_names.each {|depth, child_name|
      if depth > 0
        parent_name = get_parent_name(child_name)
        if flat_names.member?(parent_name)
          move_tree(which, parent_name, child_name)
        end
      else
        break
      end
    }
  end
  
  def get_parent_name(child_name)
    idx = child_name.rindex("::")
    return idx ? child_name[0 .. idx - 1] : nil
  end
  
  def finish_analysis(yaml_path, blobParts, module_require_name)
    if File.directory?(yaml_path)
      Dir.chdir(yaml_path) do
        infoObj = get_class_info(blobParts[-1], module_require_name)
        blobName = blobParts.join("::")
        if @builtin_names.member?(blobName)
          which = "builtin"
        else
          which = "stdlib"
          infoObj['blobname'] = module_require_name
        end
        @info[which][blobName] = infoObj
        return true
      end
    end 
  end
  
  def walk()
    @prefixes.each do |sysDir|
      Dir.chdir(sysDir) do
        Find.find('.') do |yaml_path|
          if File.directory?(yaml_path) && yaml_path[-1] != ?.
            yaml_path = yaml_path[2 .. -1] if yaml_path[0 .. 1] == "./"
            blobParts = yaml_path.split("/")  # Case is same in YAML dir
            finish_analysis(yaml_path, blobParts, yaml_path.downcase)
          end
        end
      end 
    end
  end
  
  def analyze(blobName)
    blobParts = blobName.split("::")
    yaml_moduleName = blobParts.join("/") # Uses same case as modules.
    module_require_name = yaml_moduleName.downcase
    @prefixes.each do |sysDir|
      yaml_path = "#{sysDir}/#{yaml_moduleName}"      
      rc = finish_analysis(yaml_path, blobParts, module_require_name)
      return if rc
    end
    $stderr.write("can't find module #{blobName}\n")
  end  
  
  def move_tree(which, parent_name, child_name)
    stdlib_info = @info[which]
    parent_obj = stdlib_info[parent_name]
    child_obj = stdlib_info[child_name]
    (parent_obj['inner_scopes'] ||= []) << child_obj
    stdlib_info.delete(child_name)
  end
  
  private    
  
  def cgi_escape(str)
    # CGI doesn't do it all
    return CGI.escape(str).gsub(/[-]/) {|s| sprintf("%%02x", s)}
  end
  
  def fix_comment(comment)                  
    # Comments are harder
    if comment.class == Array
      comment = comment[0]
      if comment.class == Hash
        comment = comment['body']
      elsif comment.class == SM::Flow::P
        comment = comment.body
      end
    end
    if comment.class == String && comment.size > 0
      return html_unescape(comment)
    end
  end
  
  def html_unescape(s)
    s2 = CGI.unescapeHTML(s).
      gsub(@@match_em) {|m| "`#{$1}'"}.
      gsub(@@match_b) {|m| "*#{$1}*"}.
      gsub(@@match_tt) {|m| $1 }.
      gsub("<tt>", "")
    return s2
  end
  
  def determine_ilk(moduleName, blobName)
    ilk = @@dont_require[blobName]
    unless ilk
      begin
        obj = eval(blobName)
        ilk = obj.class
      rescue NameError
        begin
          require moduleName
          begin
            obj = eval(blobName)
            ilk = obj.class
          rescue NameError
          end
        rescue LoadError
        end
      end
    end
    return @@classname_to_ilk[ilk] # default
  end
  
  #Precondition: we're in the directory containing the yaml info
  # for this part of a A::B::C::D ... module
  #
  # moduleName is the string a Ruby program would require to get
  # this blob
  # modulePart is the last dir of the module's filePath,
  # like "http" in "net/http"
  
  def get_class_info(modulePart, module_require_name)
    clsFile = "cdesc-#{modulePart}.yaml"
    if File.exists?(clsFile)
      begin
        clsYAML = YAML.load(File.open(clsFile) { |io| io.read})
      rescue => ex
        $stderr.write("Error YAML-loading class #{clsFile}: #{ex}\n")
        return nil
      end

      clsInfo = process_class_yaml(clsYAML)
      if !clsInfo['ilk']
        ilk = determine_ilk(module_require_name, clsInfo['full_name'] || clsInfo['name'])
        clsInfo['ilk'] = ilk if ilk
        if clsInfo['ilk'] == 'class' && !clsInfo.has_key?('superclass')
	  if (className = clsInfo['name']) == "File"
	    clsInfo['superclass'] = "IO"
	  elsif clsInfo['name'] != "Object"
	    clsInfo['superclass'] = "Object" # String, for one, doesn't have this
	  end
        end
      end
      return clsInfo
    end
  end
  
  def get_method_info(methodName, suffix)
    methodFile = "#{cgi_escape(methodName)}-#{suffix}.yaml"
    if File.exists?(methodFile)
      begin
        methodYAML = YAML.load(File.open(methodFile) { |io| io.read })
      rescue => ex
        $stderr.write("Error YAML-loading method #{methodFile}: #{ex} (#{$!})\n")
        return nil
      end
      return clsInfo = process_method_yaml(methodYAML)
    end
  end
  
  def process_class_yaml(yobj)
    info = {}
    # @@simple_terms = %w/name full_name superclass/;
    y = yobj.class == Hash ? yobj : yobj.ivars
    @@simple_terms.each {|w| info[w] = y[w] if y[w]}
    comment = fix_comment(y['comment'])
    info['doc'] = comment if comment
    info['included_modules'] = y['includes'].map {|yincl| yincl.ivars['name']}.reject{|obj| !obj}
    info['constants'] = []
    y['constants'].each {|item2|
      item = item2.class == Hash ? item2 : item2.ivars
      name = item['name']
      value = item['value']
      if value.index("rb_str_new")
        info['constants'] << {'name' => name, 'citdl' => 'String'}
      elsif value.index("INT2") == 0
        info['constants'] << {'name' => name, 'citdl' => 'Fixnum'}
      end
    }
    # Get whatever YAML files we can find for the methods
    ["instance_methods", "class_methods"].each {|idx|
      info[idx] = {}
      y[idx].each {|item|
        name = item.ivars['name']
        method_info = get_method_info(name, idx[0 .. 0])
        info[idx][name] = method_info if method_info
      }
    }
    (y['attributes'] || []).each { |attr|
      ivars = attr.ivars
      name = ivars['name']
      mode = ivars['rw']
      case mode
      when "RW"
	names = [name, name + "="]
      when "R"
	names = [name]
      else
	names = [name + '=']
      end
      comment = fix_comment(ivars['comment'])
      names.each {|nm|
	attr_info = {"name" => nm}
	attr_info['doc'] = comment if comment
	info['instance_methods'][nm] = attr_info
      }
    }
    return info
  end
  
  def process_method_yaml(yobj)
    info = {}
    y = yobj.ivars
    @@simple_method_terms.each {|w| info[w] = y[w] if y[w]}
    comment = fix_comment(y['comment'])
    info['doc'] = comment if comment   
    info['included_modules'] = y['includes']
    params = y['params']
    info['params'] = html_unescape(params) if params
    return info
  end
end

require 'optparse'
opt_parser = OptionParser.new
opts = {}
opt_parser.banner = "Usage: #{$0} [options] [object names ...](default: all)"
opt_parser.on('--db-dir DIR', String) { |val| opts['db-dir'] = val }
opt_parser.on('--output-dir DIR', String) { |val| opts['output-dir'] = val }
opt_parser.on('-o', '--output-file FILE', String) { |val| opts['output-file'] = val }
opt_parser.on('--skip-wrap-single') { |val|   opts['skip-wrap-single'] = val }
opts['']
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

datadir = opts['output-dir'] || "tmp"
dbdir = opts['db-dir'] || "tmp"
riw = RiWalker.new(dbdir)
table = ["builtin", "stdlib"]
final_cixes = {}
if module_names.size == 0
  riw.walk()
  table.each do |which|
    raw_names = riw.names(which) if dbdir
    riw.reorder(which)
    final_names = riw.names(which) if dbdir
    final_cixes[which] = riw.get_full_cix(which)
    if dbdir
      File.open("#{dbdir}/all_names_#{which}_1.txt", "w") {|io|
        io.write(raw_names.join("\n"))
        io.write("\n")
      }
      File.open("#{dbdir}/top_names_#{which}_1.txt", "w") {|io|
        io.write(final_names.join("\n"))
        io.write("\n")
      }
    end
  end
  total_num = riw.size
else
  # Collect CIXes only for requested names
  module_names.each {|name|
    riw.analyze(name)
  }
  total_num = riw.size
  if total_num == 0
    # Something must have gone wrong to end up here.
    exit(2)
  end
  table.each do |which|
    riw.reorder(which)
    final_cixes[which] = riw.get_full_cix(which)
  end
end

if opts['output-file']
  fout = File.open(opts['output-file'], "w")
elsif module_names.size >= 1
  fout = $stdout
else
  fout = nil # Default: write separate parts
end
if fout
  full_size = riw.size
  if (full_size > 1 || !opts['skip-wrap-single'])
    fout.write(%Q(<wrap>\n))
  end
end
  
table.each do |which|
  if !final_cixes[which] || final_cixes[which].size == 0
    next
  end
  if fout
    io = fout
  else
    io = File.open("#{datadir}/#{which}_1.cix", "w")
  end
  this_size = riw.this_size(which)
  if which == "builtin"
    io.write(%Q(<scope ilk="blob" lang="Ruby" name="*">\n))
    tag = 'scope'
  elsif !fout && (this_size > 1 || !opts['skip-wrap-single'])
    io.write(%Q(<wrap>\n))
    tag = 'wrap'
  else
    tag = nil
  end
  io.write(final_cixes[which])
  io.write(%Q(</#{tag}>\n)) if tag
  io.close() unless fout
end
if fout
  if (full_size > 1 || !opts['skip-wrap-single'])
    fout.write(%Q(</wrap>\n))
  end
end

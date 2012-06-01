#!/usr/bin/env ruby

# use RDoc::Ri::Store to generate a cix file for the target directory

require 'optparse'
opts = {}

def Usage(label=nil)
  puts label if label
  puts ''
  puts o
  exit(1)
end

o = OptionParser.new do |opt_parser|
  opt_parser.banner = "Usage: #{$0} [options] [object names ...](default: all)"
  opt_parser.on('--ri-dir DIR', String) { |val| opts['ri-dir'] = val }
  opt_parser.on('--lib-dir DIR', String) { |val| opts['lib-dir'] = val }
  opt_parser.on('--output-dir DIR', String) { |val| opts['output-dir'] = val }
  opt_parser.on('-o', '--output-file FILE', String) { |val| opts['output-file'] = val }
  opt_parser.on('-v', '--verbose') { |val| opts['verbose'] = val }
  opt_parser.on('-w', '--warnings') { |val| opts['warnings'] = val }
  opt_parser.on_tail("-h", "--help", "Show this message") do
    Usage()
  end
end.parse!

Usage("No ri-dir specified")  if !opts.has_key?('ri-dir')
Usage("No lib-dir specified") if !opts.has_key?('lib-dir')
opts['output-dir'] ||= Dir.pwd
opts['output-file'] ||= 'ruby.cix';



require 'rdoc/ri'
require 'rdoc/markup'
require 'rdoc/method_attr'

def blank?(s)
  return s.nil? || s.size == 0
end
class String
  def ends_with?(s)
    return self.rindex(s) == self.size - s.size
  end
end

def getFilename(m)
  begin
    fullName = fname = m.comment.parts[0].instance_eval("@file") rescue nil
    if fname
      fname = fname.sub(/^lib\//, '').sub(/\.rb$/, '')
    end
  rescue
    $stderr.puts("Error getting fname: #{$!}")
    fname = nil
  end
  return [fname, fullName]
end
  
class CacheForest
  attr_reader :root, :cache
  def initialize(opts)
    @riDir = riDir = opts['ri-dir']
    @libDir = opts['lib-dir']
    @cache = RDoc::RI::Store.new(riDir, nil) # 2nd arg => cache.type, not used
    @cache.load_cache
    @cacheDirs = Dir.entries(riDir).find_all{|p| p != "." && p != ".." && File.directory?(riDir + "/" + p)}.sort
    # For comments:
    @@line_limit = 6
    @@size_limit = 256
    @@size_ptn = Regexp.new("^.{#{@@size_limit}}\\S*")
    @failedToLoads = []
    @rejectedModules = []
    #@tracker = {}
  end
  
  def report
    $stderr.puts "# unloadable methods: #{@failedToLoads.size}"
    $stderr.puts "# rejected modules: #{@rejectedModules.size}"
  end
  
  @@badNames = ["ARGF.class", "Addrinfo", "BasicObject", "Etc", "BasicSocket",
                "CacheForest", "CGI", "Debugger", "FileUtils",
                "IPSocket", "LineCache", "Logger", "Monitor",
                "OptionParser", "PP", "PrettyPrint", "RDoc", "TraceLineNumbers",
                "URI"]
  
  def load_builtins
    @builtin_names = Object.constants.map(&:to_s).delete_if do | name |
      @@badNames.include?(name) || name['#<'] || name['::'] || name['BKTP'] || name["DBP_E"] || \
        name["FRAME_"] || name["IB_STATE_"] || name["RB_EVENT_"] || name["SCRIPT_LINES"] || \
        name["SINGLE_"] || name["STOP_REASON_"]
    end
    @builtin_names << "ARGF.class"
    @builtin_names.each do |name|
      if @cacheDirs.include?(name)
        @cacheDirs.delete(name)
      end
    end
  end
  
  def load_module(fq_module_name)
    m = @cache.load_class fq_module_name
    path, fullPath = getFilename(m)
    full_name = m.full_name
    parts = full_name.split('::')
    if path.nil?
      path, fullPath = get_src_file(m, parts.clone)
      if path.nil?
        @rejectedModules << fq_module_name
        return
      end
    end
    return m, path, fullPath
  end
  
  def get_src_file(m, parts)
    parentPath = @libDir
    kwd = m.module? ? "module" : "class"
    className = parts[-1]
    leadingParts = []
    in_first = true
    if parts.size == 1
      path = File.join(parentPath, parts[0].downcase + ".rb")
      if File.exists?(path)
        root = parts[0].downcase
        fullPart = File.basename(@libDir) + "/" + root + ".rb"
        return [root, fullPart]
      end
    end
    while parts.size > 0
      p = parts.shift
      p_lc = p.downcase
      path = File.join(parentPath, p_lc)
      if !File.exists?(path)
        break if !in_first
        in_first = false
      end
      leadingParts << p_lc
      parentPath = path
      if File.directory?(path)
        #ans = `echo '^\\s*#{kwd}\\s+#{className}' #{path}/*.rb`
        ans = `grep -l '^\s*#{kwd}\s*#{className}' #{path}/*.rb`
        if blank?(ans)
          ans = `grep -l '^\s*#{kwd}.*#{p}::#{className}' #{path}/*.rb`
        end
        if !blank?(ans)
          ans = ans.chomp
          root = leadingParts.join("/") + "/" + File.basename(ans, ".rb")
          fullPart = File.basename(@libDir) + "/" + root + ".rb"
          return [root, fullPart]
        end
      end
    end
    return [nil, nil]
  end
  
  def writeCix(opts)
    outDir = opts['output-dir']
    outFile = opts['output-file']
    #@fout = File.open(File.join(outDir, outFile), 'wb')
    @fout = $stdout; #File.open(File.join(outDir, outFile), 'wb')
    @fout.puts(<<"_EOD_")
<?xml version="1.0" encoding="utf-8" ?>
<codeintel version="2.0" name="Ruby 1.9" description="Cix data for Ruby 1.9">
  <file lang="Ruby" mtime="#{Time.now.to_i}" path="ruby-1.9.cix">
_EOD_
    ind = "    "
    @module_name = "Kernel"
    m = @cache.load_class @module_name
    writeTopLevelNames(ind, "*", m)
    @cacheDirs.each do | cacheDir |
      writeBlobFromCache(ind, cacheDir)
    end
    @fout.puts(<<'_EOD_')
  </file>
</codeintel>
_EOD_
    @fout.close
  end
  
  def writeTopLevelNames(ind, blobName, m)
    @fout.puts(%Q(#{ind}<scope ilk="blob" lang="Ruby" name="*">\n))
    # types: 1:class, 2:module, 3:kernel methods, 4:others
    ind2 = ind + "  "
    begin
      @builtin_names.each do |name|
        begin
          obj = Object.class_eval(name)
          oclass = obj.class
          if oclass == Module
            writeBuiltinItem(ind2, 2, name, obj)
          elsif oclass == Class
            writeBuiltinItem(ind2, 1, name, obj)
          else
            writeConstantItem(ind2, name, obj)
          end
        rescue
          $stderr.puts("Problem handling builtin #{name}: #{$!}")
        end
      end
      kmethodNames = (Kernel.methods - Kernel.class.methods).sort
      kmethodNames.each do |name|
        writeBuiltinItem(ind + "  ", 3, name.to_s, nil)
      end
    rescue
      $stderr.puts("writeTopLevelNames: error: #{$!}")
    ensure
      @fout.puts(%Q(#{ind}</scope>\n));
    end
  end
  
  @@ilkType = [ "**NOTUSED**", "class", "namespace", "function"]
  def writeBuiltinItem(ind, nameType, name, obj)
    begin
      if nameType == 3
        m = @cache.load_method("Kernel", "#" + name)
      else
        m = @cache.load_class name
      end
    rescue
      $stderr.puts("writeBuiltinItem: failed to rdoc/load #{name}")
      m = nil
    end
    writeBuiltinItem2(ind, name, name, @@ilkType[nameType], obj, m)
  end
  
  def writeFunctionItem(ind, name, rdocObject, args=nil)
    @fout.write(%Q(#{ind}<scope name="#{name}" ilk="function"))
    begin
      if args && args[:classFunction]
        @fout.write(%Q( attributes="__classmethods__))
        if name == 'new '
          @fout.write(%Q __ctor__ )
        end
        @fout.write(%Q("))
      end
      if rdocObject
        if rdocObject && rdocObject.respond_to?(:params) && rdocObject.params
          begin
            @fout.write(%Q( signature="#{e1(name + rdocObject.params)}"))
          rescue
            $stderr.puts "Error getting sig: #{$!}"
          end
        end
        # No point gathering doc strings for modules or classes, since they'll never show up.
        doc = shorten(flatten_comments(rdocObject.comment))
        if doc.size > 0
          @fout.write(%Q( doc="#{doc}"))
        end
      end
    rescue
      $stderr.puts("writeFunctionItem: error: #{$!}")
    ensure
      @fout.puts(" />")
    end
  end
  
  def writeBuiltinItem2(ind, name, fqname, ilk, liveObject, rdocObject, args={})
    if ilk == "function"
      writeFunctionItem(ind, name, rdocObject, args)
      return
    end
    @fout.write(%Q(#{ind}<scope name="#{name}" ilk="#{ilk}"))
    begin
      if !liveObject
        @fout.puts(" />")
        return
      end
      if ilk == "class"
        @fout.write(%Q( classrefs="#{liveObject.superclass}"))
      end
      @fout.puts(" >")
    rescue
      $stderr.puts("writeBuiltinItem2: error: #{$!}")
      @fout.puts(" />")
      return
    end
    
    begin
      # Do the nested stuff
      ind2 = ind + "  "
      begin
        (liveObject.included_modules - [Kernel]).each do |iname|
          next if iname["#<"]
          @fout.puts(%Q(#{ind2}<import symbol="#{iname}" />))
        end
      rescue
      end
      # Now get modules, classes, other constants, and methods found on this object.
      if ilk == "namespace"
        methods = (liveObject.instance_methods - Module.methods).sort
      else
        methods = (liveObject.instance_methods - liveObject.superclass.instance_methods).sort
      end
      liveObject.included_modules.each do | mod |
        methods -= mod.instance_methods
      end
      
      methods.each do |name2Sym|
        name2 = name2Sym.to_s
        next if /\A\W+\Z/.match(name2)
        m2 = nil
        begin
          m2 = @cache.load_method(name, "#" + name2)
        rescue
          @failedToLoads << "#{name}.#{name2}"
        end
        writeFunctionItem(ind2, name2, m2)
      end
      if ilk == "class"
        methods = liveObject.singleton_methods - liveObject.superclass.singleton_methods
        liveObject.included_modules.each do | mod |
          methods -= mod.methods
        end
        methods.sort.each do |name2Sym|
          name2 = name2Sym.to_s
          m2 = nil
          begin
            m2 = @cache.load_method(name, name2)
          rescue
            @failedToLoads << "#{name}.#{name2}"
          end
          writeFunctionItem(ind2, name2, m2, { :classFunction => 1 })
        end
        # Not all classes have anything to say about .new, and just inherit
        begin
          name2 = "new"
          m2 = @cache.load_method(name, name2)
          writeFunctionItem(ind2, name2, m2, { :classFunction => 1 })
        rescue
        end
      end
      
      return if ["Class", "Module", "Object"].include?(name)
      return if ["Struct::Group", "Struct::Passwd", "Struct::Tms"].include?(liveObject.name)
      sortedObjects = liveObject.constants
      begin
        sortedObjects = sortedObjects.sort
      rescue
        $stderr.puts "Error sorting: #{$!}"
      end
      sortedObjects.each do |name2sym|
        name2 = name2sym.to_s
        liveObject2 = rdocObject2 = type2 = nil
        begin
          if ilk == "class"
            fqname2 = fqname + "." + name2
          else
            fqname2 = fqname + "::" + name2
          end
          liveObject2 = liveObject.class_eval(fqname2)
          if liveObject2.is_a?(Module) || liveObject2.is_a?(Class)
            begin
              rdocObject2 = @cache.load_class(liveObject2.name)
            rescue
            end
            ilk2 = liveObject2.class == Module ? "namespace" : "class"
            writeBuiltinItem2(ind2, name2, fqname2, ilk2, liveObject2, rdocObject2)
          else
            writeConstantItem(ind2, name2, liveObject2)
          end
        rescue
        end
      end
    rescue
      $stderr.puts("writeBuiltinItem2: error: #{$!}")
    ensure
      @fout.puts(%Q(#{ind}</scope>\n));
    end
  end
  
  def writeConstantItem(ind, name, liveObject)
    @fout.puts(%Q(#{ind}<variable attributes="__const__" citdl="#{liveObject.class.to_s}" name="#{name}" />))
  end

  # Here we write out info obtained just from the rdoc/ri cache, but
  # don't instantiate any objects.
  
  def writeBlobFromCache(ind, cacheDir)
    m, path, fullPath = load_module(cacheDir)
    return if !m || blank?(path)
    @fout.puts(%Q(#{ind}<scope ilk="blob" lang="Ruby" name="#{path}">))
    begin
      writeModuleOrClass(ind + "  ", cacheDir, cacheDir, @riDir + "/" + cacheDir, m)
    ensure
      @fout.puts(%Q(#{ind}</scope>))
    end
  end

  def writeModuleOrClass(ind, name, fqName, currDir, m)
    if m.module?
      writeModuleInfo(ind, name, fqName, currDir, m)
    else
      writeClassInfo(ind, name, fqName, currDir, m)
    end
  end

  def writeModuleInfo(ind, name, fqName, currDir, m)
    @fout.puts(%Q(#{ind}<scope ilk="namespace" name="#{name}">\n))
    ind2 = ind + "  "
    begin
      writeBlobItems(ind2, fqName, m)
      writePackageChildren(ind2, fqName, "::", currDir)
    ensure
      @fout.puts(%Q(#{ind}</scope>\n));
    end
  end
  
  def writeClassInfo(ind, name, fqName, currDir, m)
    @fout.puts(%Q(#{ind}<scope ilk="class" name="#{name}">\n))
    ind2 = ind + "  "
    begin
      writeBlobItems(ind2, fqName, m)
      writePackageChildren(ind2, fqName, "::", currDir)
    ensure
      @fout.puts(%Q(#{ind}</scope>\n));
    end
  end
  
  def writePackageChildren(ind, fqName, fqSep, currDir)
    kids = Dir.entries(currDir).find_all{|p| p != "." && p != ".." && File.directory?(currDir + "/" + p)}.sort
    kids.each do | dirName |
      clsName = fqName + fqSep + dirName
      m = @cache.load_class(clsName)
      if !m
        $stderr.puts("Couldn't get class #{clsName}: {$!}")
      end
      writeModuleOrClass(ind, dirName, clsName, currDir + "/" + dirName, m)
    end
  end
  
  def writeBlobItems(ind, fqName, m)
    methods = m.method_list
    methods.each do |func|
      if func.visibility == :public
        func_name = func.name[0]
        writeMethod(ind + "  ", fqName, m, func_name, func.singleton)
      end
    end
  end
  
  def e1(s)
    s1 = s.gsub(/<\/?(?:code|em|i|tt)\b.*?>/, '');
    s2 = s1.gsub('&', '&amp;').gsub('<', '&lt;').gsub('>', '&gt;').gsub('\'', '&apos;').gsub('"', '&quot;')
    s3 = s2.gsub(/[^\t\n\x20-\x7f]/, '')
    s3
  end
  
  def writeMethod(ind, fqName, m, func_name, isSingleton)
    prefix = isSingleton ? "" : "#"
    begin
      func = @cache.load_method(fqName.gsub('.', "::"), prefix + func_name)
    rescue
      $stderr.puts("Can't load method #{fqName.gsub('.', "::")} == #{prefix + func_name}")
      return
    end
    #func = @cache.load_method(fqName.gsub('.', "::"), prefix + func_name)
    attributes = func_name == "new" ? "__ctor__" : nil
    x = []
    x.push([:name, e1(func_name)])
    x.push([:ilk, :function.to_s])
    if func.respond_to?(:params) && func.params
      begin
        x.push([:signature, e1(func_name + func.params)])
      rescue
        $stderr.puts "Error getting sig: #{$!}"
        raise
      end 
    end
    x.push([:attributes, attributes]) if attributes
    doc = shorten(flatten_comments(func.comment))
    x.push([:doc, doc]) if doc.size > 0
    
    s = ind + "<scope"
    x.each do |name, val|
      s += %Q{ #{name.to_s}="#{val}"}
    end
    s += " />"
    @fout.puts(s)
    puts "Stop here" if false
  end
  
  def flatten_comments(comment)
    s = []
    parts = comment.parts rescue [comment]
    parts.each do |part|
      # Yuk, but we need to do this....
      if part.is_a?(String)
        s << e1(part)
      elsif part.respond_to?(:text) 
        if part.class == RDoc::Markup::Verbatim
          s << e1(part.text.gsub("\r", "")).gsub("\n", '&#xA;')
        else
          s << e1(part.text)
        end
      elsif part.class == RDoc::Markup::BlankLine
        s << "&#xA;"
      elsif part.class == RDoc::Markup::Paragraph || part.class == RDoc::Markup::Document
        s << part.parts.map {|i| flatten_comments(i)}.join("&#xA;")
      elsif part.class == RDoc::Markup::List
        s << part.items.map {|i| flatten_comments(i)}.join("&#xA;")
      else
        $stderr.puts("Found unknown part type #{part.class.name}")
      end
    end
    return s.join(" ")
  end
  
  def shorten(text)
    lines = text.split('&#xA;').delete_if {|x|x.size == 0}
    if lines.size > @@line_limit
      lines = lines[0 .. @@line_limit]
      text = lines.join('&#xA;')
    end
    if text.size > @@size_limit
      m = @@size_ptn.match(text)
      if m
        text = text[0 .. m.end(0)] + "..."
      end
    end
    return text
  end
end

forest = CacheForest.new(opts)
forest.load_builtins()
forest.writeCix(opts)
forest.report
$stderr.puts "Done"

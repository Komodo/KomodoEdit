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
  opt_parser.on('-g', '--generate-lines') { |val| opts['generate-lines'] = val }
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
    @generateLines = opts['generate-lines']
    @cache = RDoc::RI::Store.new(riDir, nil) # 2nd arg => cache.type, not used
    @cache.load_cache
    @cacheDirs = Dir.entries(riDir).find_all{|p| p != "." && p != ".." && File.directory?(riDir + "/" + p)}.sort
    # For comments:
    @@line_limit = 12
    @@size_limit = 10000
    @@size_ptn = Regexp.new("^.{#{@@size_limit}}\\S*")
    @failedToLoads = []
    @failedToLoadSubpackages = []
    @rejectedModules = []
    #@tracker = {}
  end
  
  def report
    $stderr.puts "# unloadable methods: #{@failedToLoads.size}"
    $stderr.puts "# rejected modules: #{@rejectedModules.size}"
    $stderr.puts "# unloadable subpackages: #{@failedToLoadSubpackages.size}"
    
  end
  
  @@badNames = ["ARGF.class", "Addrinfo", "BasicObject", "Etc", "BasicSocket",
                "CacheForest", "CGI", "Debugger", "FileUtils",
                "IPSocket", "LineCache", "Logger",
                "OptionParser", "PP", "PrettyPrint", "RDoc", "TraceLineNumbers",
                "URI"]
  
  def load_builtins
    @builtin_names = Object.constants.map(&:to_s).delete_if do | name |
      @@badNames.include?(name) || name['#<'] || name['::'] || name['BKTP'] || name["DBP_E"] || \
        name["FRAME_"] || name["IB_STATE_"] || name["RB_EVENT_"] || name["SCRIPT_LINES"] || \
        name["SINGLE_"] || name["STOP_REASON_"]
    end
    #@builtin_names << "ARGF.class"
    if !@builtin_names.include?("Monitor")
      begin
        require "monitor"
        @builtin_names << "Monitor"
        @builtin_names << "MonitorMixin"
      rescue LoadError
        $stderr.puts("Can't load monitor")
      end
    end
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
      #if path.nil?
      #  @rejectedModules << fq_module_name
      #  return
      #end
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
<codeintel version="2.0" name="Ruby #{RUBY_VERSION}" description="Cix data for Ruby #{RUBY_VERSION}">
  <file lang="Ruby" mtime="#{Time.now.to_i}" path="ruby-#{RUBY_VERSION}.cix">
_EOD_
    ind = "    "
    @module_name = "Kernel"
    m = @cache.load_class @module_name
    @isBuiltin = true
    #XXX !!!!
    writeTopLevelNames(ind, "*", m)
    @isBuiltin = false
    @blobs = {} # map an array of XML scopes to blob names
    @currBlobLibs = [] # a stack
    @cacheDirs.each do | cacheDir |
        writeBlobFromCache(ind, cacheDir)
    end
    @blobs.sort.each do | libname, scopeArray |
      next if scopeArray.size == 0
      @fout.puts(%Q(#{ind}<scope name="#{libname}" ilk="blob" lang="Ruby">))
      # Collapse duplicate outer things
      fixedScopeArray = []
      scPrevLines = scopeArray[0].split("\n")
      prevFirstLine = scPrevLines[0]
      lim = scopeArray.size
      i = 1
      while i < lim
        sc = scopeArray[i]
        scLines = sc.split("\n")
        if (currFirstLine = scLines[0]) == prevFirstLine
          fixedScopeArray += scPrevLines[0 .. -2]
          scPrevLines = scLines[1 .. -1]
        else
          fixedScopeArray += scPrevLines
          prevFirstLine = currFirstLine
          scPrevLines = scLines
        end
        i += 1
      end
      fixedScopeArray += scPrevLines
      @fout.puts(fixedScopeArray.join("\n"))
      @fout.puts(%Q(#{ind}</scope>))
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
        @fout.write(%Q( attributes="__classmethod__))
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
        (liveObject.included_modules - [Kernel]).each do |inameMod|
          iname = inameMod.name
          next if iname["#<"]
          @fout.puts(%Q(#{ind2}<import symbol="#{iname}" />))
        end
      rescue
        $stderr.puts("Error getting included modules from #{name}: #{$!}")
      end
      # Now get modules, classes, other constants, and methods found on this object.
      if ilk == "namespace"
        methods = (liveObject.instance_methods + liveObject.methods - Module.methods).sort
      else
        methods = (liveObject.instance_methods - liveObject.superclass.instance_methods).sort
      end
      if name != "Object" && name != "BasicObject"
        liveObject.included_modules.each do | mod |
          methods -= mod.instance_methods
        end
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
          next if mod == Kernel
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
      #if name == "File"
      #  puts "Stop here"
      #end
      sortedObjects = liveObject.constants
      begin
        if sortedObjects.include?(:Constants)
          sortedObjects -= liveObject.class_eval("Constants").constants
        end
        sortedObjects = sortedObjects.sort
      rescue
        $stderr.puts "Error sorting: #{$!}"
      end
      sortedObjects.each do |name2sym|
        name2 = name2sym.to_s
        liveObject2 = rdocObject2 = type2 = nil
        begin
          fqname2 = fqname + "::" + name2
          #if ilk == "class"
          #  fqname2 = fqname + "." + name2
          #else
          #  fqname2 = fqname + "::" + name2
          #end
          liveObject2 = liveObject.class_eval(name2)
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
    #TODO Add line/lineend attributes
    @fout.puts(%Q(#{ind}<variable name="#{name}" attributes="__const__" citdl="#{liveObject.class.to_s}" />))
  end

  # Here we write out info obtained just from the rdoc/ri cache, but
  # don't instantiate any objects.
  
  def getFileLines(path)
    return [] unless @generateLines
    begin
      lines = []
      File.open(File::join(@libDir, path + ".rb"), 'r') do |fd|
        fd.readlines.each_with_index do |item, index|
          if item =~ /\A\s*(?:def|class|module|end)\b/
            lines << [index + 1, item]
          end
        end
      end
    rescue
    end
    return lines
  end
  
  def getLineBoundaries(name, type, lines)
    ptn = /\A(\s*)#{type}\s*#{name}/
    lineStart = nil
    nextIdx = 0
    targetPtn = otherPtn = nil
    firstInnerIdx = 0
    lines.each_with_index do |linePair, i|
      index, line = linePair
      if m = (ptn.match(line))
        lineStart = index
        targetPtn = /\A#{m[1]}end\b/
        otherPtn = /\A#{m[1]}(?:class|module|def)\b/
        firstInnerIdx = i + 1
        break
      end
    end
    return [nil, nil, []] if !lineStart
    nesting = 0
    lines[firstInnerIdx .. -1].each do | i, line |
      if line =~ otherPtn
        nesting += 1
      elsif line =~ targetPtn
        nesting -= 1
        if nesting <= 0
          return [lineStart, i, lines[firstInnerIdx .. i]]
        end
      end
    end
    return [nil, nil, []]
  end

  def getRequirablePathFromPath(path)
    match = /\Aext\/(.*)\/[^\/]+\.c\Z/.match(path)
    if match
      return match[1]
    else
      match = /\Aext\/.*?\/lib\/(.*)\Z/.match(path)
      if match
        return match[1]
      else
        return path
      end
    end
  end
  
  def writeBlobFromCache(ind, cacheDir)
    m, path, fullPath = load_module(cacheDir)
    return if !m
    if blank?(path)
      # Just guess what the path would be
      if cacheDir[':']
        $stderr.puts("can't get a path for lib #{cacheDir}, giving up")
        @rejectedModules << cacheDir
        return
      else
        cpath = path = cacheDir.downcase
        begin
          require cpath
        rescue LoadError
          return
        end
        $stderr.puts("Faking it for library #{cacheDir}")
      end
      lines = []
    else
      lines = getFileLines(path)
      cpath = getRequirablePathFromPath(path)
    end
    return if cpath.ends_with?(".c")
    @currBlob = ""
    @blobs[cpath] = [] if !@blobs.has_key?(cpath)
    peers = writeModuleOrClass(ind + "  ", cacheDir, cacheDir, @riDir + "/" + cacheDir, m, path, lines)
    @blobs[cpath] << @currBlob
    peers.each do | peerName |
      writePeerBlobFromCache(ind, peerName)
    end
  end
  
  def writePeerBlobFromCache(ind, cacheDir)
    # cacheDir is probably fully-qualified, but we want to start at the top name,
    # but pull info from an ri-subdir
    m, path, fullPath = load_module(cacheDir)
    return if !m || blank?(path)
    lines = getFileLines(path)
    cpath = getRequirablePathFromPath(path)
    return if cpath.ends_with?(".c")
    @currBlobLibs.push(@currBlob)
    @currBlob = ""
    @blobs[cpath] = [] if !@blobs.has_key?(cpath)
    peers = []
    begin
      # Write out module and class headers for the leading parts until we get to the main item.
      parts = cacheDir.split("::")
      leadingParts = parts[0 .. -2]
      writeLeadingParts(ind + "  ", leadingParts, lines) do | ind2, narrowedLines |
        peers = writeModuleOrClass(ind2, parts[-1], cacheDir, @riDir + "/" + cacheDir.gsub('::', '/'), m, path, lines)
      end
    rescue
      $stderr.puts("Error in writeModuleOrClass:#{$!}")
    end
    @blobs[cpath] << @currBlob
    @currBlob = @currBlobLibs.pop
    peers.each do | peerName |
      writePeerBlobFromCache(ind, peerName)
    end
  end
  
  def writeLeadingParts(ind, parts, lines, &blk)
    # Find the start of the first part, either a module or class
    if parts.size == 0
      blk.call(ind, lines)
      return
    end
    part = parts[0]
    ptn = /\A(\s*)(class|module)\s+(.*?#{part})/
    ws = cixIlk = ilk = target = startingIndex = nil
    lines.each_with_index do | linePair, i |
      m = ptn.match(linePair[1])
      if m
        ws = m[1]
        ilk = m[2]
        cixIlk = ilk == "module" ? "namespace" : "class"
        target = m[3]
        startingIndex = i
        break
      end
    end
    # If we don't know what it is, guess and call it a module (namespace)
    stag = %Q(#{ind}<scope name="#{part}" ilk="#{cixIlk || "namespace"}")
    if !ws.nil?
      lineStart, lineEnd, narrowedLines = getLineBoundaries(target, ilk, lines)
      if lineStart && lineEnd
        stag += %Q( line="#{lineStart}" lineend="#{lineEnd}")
      end
    end
    @currBlob += stag + ">\n"
    begin
      writeLeadingParts(ind + "  ", parts[1 .. -1], narrowedLines || [], &blk)
    rescue
      $stderr.puts("Error writing nested writeLeadingParts: #{$!}")
    ensure
      @currBlob += %Q(#{ind}</scope>\n)
    end
  end

  def writeModuleOrClass(ind, name, fqName, currDir, m, path, flines)
    if m.module?
      ilk = "namespace"
      rubyIlk = "module"
    else
      ilk = rubyIlk = "class"
    end
    lineStart, lineEnd, innerLines = getLineBoundaries(name, rubyIlk, flines)
    peers = []
    stag = %Q(#{ind}<scope name="#{name}" ilk="#{ilk}")
    if ilk == "class" && (superclass = m.superclass)
      stag += %Q( classrefs="#{superclass}")
    end
    if lineStart && lineEnd
      stag += %Q( line="#{lineStart}" lineend="#{lineEnd}")
    end
    stag += ">\n"
    @currBlob += stag
    ind2 = ind + "  "
    begin
      begin
        (m.includes.map(&:full_name) - ["Kernel"]).sort.each do |iname|
          next if iname["#<"]
          @currBlob += %Q(#{ind2}<import symbol="#{iname}" />\n)
        end
      rescue
        $stderr.puts("Error getting include out of #{rubyIlk} #{name}")
      end
      writeBlobItems(ind2, fqName, m, innerLines)
      peers = writePackageChildren(ind2, fqName, "::", currDir, path, innerLines)
    ensure
      @currBlob += %Q(#{ind}</scope>\n)
    end
    return peers
  end
  
  def writePackageChildren(ind, fqName, fqSep, currDir, path, flines)
    peers = []
    kids = Dir.entries(currDir).find_all{|p| p != "." && p != ".." && File.directory?(currDir + "/" + p)}.sort
    kids.each do | dirName |
      clsName = fqName + fqSep + dirName
      #m = @cache.load_class(clsName)
      m, path2, fullPath2 = load_module(clsName)
      if !m
        @failedToLoadSubpackages << clsName
        next
      end
      if path2.nil?
        path2 = path
        flines2 = flines
      elsif path2 == path
        flines2 = flines
      else
        #peers << [ dirName, m, path2]
        peers << clsName
        next
      end
      writeModuleOrClass(ind, dirName, clsName, currDir + "/" + dirName, m, path2, flines2)
    end
    return peers
  end
  
  def writeBlobItems(ind, fqName, m, flines)
    methods = m.method_list
    methods.each do |func|
      if func.visibility == :public
        func_name = func.name
        func_name = func_name[0] unless func_name.class == String
        writeMethod(ind, fqName, m, func_name, func.singleton, flines)
      end
    end
    attributes = m.attributes.sort { |a1, a2| a1.name <=> a2.name }
    attributes.each do | attr |
      @currBlob += %Q(#{ind}<scope ilk="function" name="#{e1(attr.name)}" />\n) if attr.rw["R"]
      @currBlob += %Q(#{ind}<scope ilk="function" name="#{e1(attr.name)}=" />\n) if attr.rw["W"]
    end
    m.constants.map(&:name).find_all{|s| s =~ /\A[A-Z_]+\Z/}.each do |s|
      @currBlob += %Q(#{ind}<variable name="#{s}" attributes="__const__" citdl="Object" />\n)
    end
  end
  
  def e1(s)
    s1 = s.gsub(/<\/?(?:code|em|i|tt)\b.*?>/, '');
    s2 = s1.gsub('&', '&amp;').gsub('<', '&lt;').gsub('>', '&gt;').gsub('\'', '&apos;').gsub('"', '&quot;')
    s3 = s2.gsub(/[^\t\n\x20-\x7f]/, '')
    s4 = s3.gsub('#=', '=') # marshal artefact?
    s4
  end
  
  def writeMethod(ind, fqName, m, func_name, isSingleton, flines)
    return if func_name =~ /\A\W+\Z/
    if isSingleton
      attributes = "__classmethod__"
      attributes += " __ctor__" if func_name == "new"
      prefix = "#"
    else
      prefix = ""
      attributes = nil
    end
    prefix = isSingleton ? "" : "#"
    begin
      func = @cache.load_method(fqName.gsub('.', "::"), prefix + func_name)
    rescue
      $stderr.puts("Can't load method #{fqName.gsub('.', "::")} == #{prefix + func_name}")
      return
    end
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
    
    lineStart, lineEnd, innerLines = getLineBoundaries(func_name == "new" ? "initialize" : func_name, "def", flines)
    if lineStart
      x.push([:line, lineStart])
      x.push([:lineend, lineEnd || lineStart])
    end
    
    doc = shorten(flatten_comments(func.comment))
    x.push([:doc, doc]) if doc.size > 0
    
    s = ind + "<scope"
    x.each do |name, val|
      s += %Q{ #{name.to_s}="#{val}"}
    end
    s += " />\n"
    @currBlob += s
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
      elsif part.class == RDoc::Markup::Rule
        # do nothing, it's a horiz bar
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

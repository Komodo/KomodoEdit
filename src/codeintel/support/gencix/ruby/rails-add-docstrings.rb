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

# walk the yaml files, build a list of files and info

require 'optparse'
require 'ostruct'
# $stderr.puts("[#{ARGV.join('] [')}]")
options = OpenStruct.new(
  'outfile'      => nil,
  'rdoc' => 'rdoc',
  'gemdir' => nil,
  'force' => false,
  'override' => false,
  'verbose'   => 0
)

opts = OptionParser.new do |opts|
  opts.banner = <<EOB
Usage: #{$0} [options] input-file (rails.cix)
EOB
  opts.separator ""
  opts.separator "Options:"
  opts.on("-o", String) {|val| puts "-o:#{val}"; options.outfile=val}
#  opts.on("-o", "--output", String) {|val| puts "-o:#{val}"; options.outfile=val}
  opts.on("-v", "--verbose", "add a verbose level") {puts "**verbose";options.verbose += 1}
  opts.on("--rdoc", String, "name of rdoc dir") {|rdoc| options.rdoc = rdoc}
  opts.on("--gemdir", String, "path to Ruby gems dir") {|rdoc| options.gemdir = rdoc}
  opts.on("--override", "override existing comments") {options.override += 1}
  opts.separator ""
  opts.separator "Common options:"
  opts.on_tail("--help", "Show this message") do
    puts opts
    exit
  end
end

def Usage(opts, s=nil)
  puts s if s
  puts opts
  exit(-1)
end

# Not working
# opts.parse! ARGV

argv = []
while ARGV.size > 0
  arg = ARGV.shift
  case arg
  when '-v'
    options.verbose += 1
  when '-o', '--output'
    options.outfile = ARGV.shift
  when '--force'
    options.force = true
  when '--rdoc'
    options.rdoc = ARGV.shift
  when '--gemdir'
    options.gemdir = ARGV.shift
  when '--override'
    options.override = true
  when '-h'
    Usage(opts)
  when '^(-[^=]+)=(.*)'
    ARGV.unshift $2
    ARGV.unshift $1
  else
    argv << arg
  end
end

Usage(opts, "No input file given") if argv.empty?
if options.outfile && File.exists?(options.outfile) && !options.force
    Usage(opts, "File #{options.outfile} exists")
end

require 'cgi'
require 'pp'
require 'find'
require 'rdoc/markup/simple_markup/to_flow'
require 'yaml'

class Finder
  attr_reader :changes
  def initialize(override=false)
    @flist = {}
    @is_yaml = /\.yaml$/
    @level = /^(.*)-([ci])\.yaml$/
    @empty = '()'
    @changes = 0
    @override = override
    @LINE_LIMIT = 5      # limit full number of lines this number
    @LINE_WIDTH = 60     # wrap doc summaries to this width
  end
  def dump
    pp @flist
  end
  def build(rdoc_dir)
    Find.find(rdoc_dir) do |f|
      next unless @is_yaml =~ f
      path, base = File.split(f)
      if /Test\b/ =~ path || base.index('cdesc-') == 0
        #puts "Skipping file #{f}"
        next
      end
      data = YAML.load(File.open(f))
      ivars = data.ivars
      begin
        comment = ivars['comment'].map {|c| c.body}.join("\n")
      rescue Exception
        comment = nil
      end
      if ivars['params'] != @empty || comment
        if @level !~ base
          puts "Can't figure out type of #{f}"
          next
        end
        ftype = $2
        base2 = CGI.unescape($1)
        # puts "Adding file #{f} (#{base2})"
        (@flist[base2] ||= []) << {'params' => ivars['params'],
          'comment' => comment,
          'dir' => path.split('/')[1 .. -1].join('/'),
        }
      else
        if false
          puts "Skipping file #{f}, data is"
          pp data
        end
      end
    end # end Find.find
  end # end build
  def annotate(tree, parts=[])
    if !(s = tree['scope'])
      return
    end
    s.each {|subtree|
      ilk = subtree['ilk']
      if ilk == 'namespace' || ilk == 'class'
        annotate(subtree, parts + [subtree['name']])
      elsif ilk == 'function'
        info = lookup(subtree['name'], parts)
        if info
          @changes += 1
          if info['params'] && (@override || !subtree['signature'])
            subtree['signature'] = handle_nl(cix_prepare(info['params']))
            spacer = subtree['signature'][0] == ?( ? "" : " "
            subtree['signature'] = subtree['name'] + spacer + subtree['signature']
          end
          if info['comment'] and (@override || !subtree['doc'])
            raw_doc = cix_prepare(info['comment'])
            raw_doc_narrowed = parseDocSummary(raw_doc)
            subtree['doc'] = raw_doc_narrowed
          elsif subtree['doc']
            subtree['doc'] = handle_nl(subtree['doc'])
          end
        end
      end
    }
  end
  
  private

  def handle_nl(s)
     return s.gsub(/\r?\n/, '\\n')
  end
  
  def cix_prepare(s)
    return s.gsub(/<tt>(.*?)<\/tt>/, '\1')
  end

  def parseDocSummary(str)
    lines = str.split(/\r?\n/)
    text = ""
    num_lines = 0
    curr_line_width = 0
    line_ends = Hash.new("\n")
    line_ends[@LINE_LIMIT - 1] = "...\n" if lines.size > @LINE_LIMIT
    line_lim_sub1 = @LINE_LIMIT - 1
    lines.each do |line|
      while line.size > 0
        if curr_line_width >= @LINE_WIDTH - 10
            text += line_ends[num_lines]
            curr_line_width = 0
            num_lines += 1
            break if num_lines >= @LINE_LIMIT
        end
        if curr_line_width + line.size > @LINE_WIDTH
          space_left = @LINE_WIDTH - curr_line_width - 1
          if space_left <= 0
            text += line_ends[num_lines]
            curr_line_width = 0
            num_lines += 1
            break if num_lines >= @LINE_LIMIT
          end
          if /^(.{1,#{space_left}})([\.\w]) (\w.*)$/ =~ line
            text += $1 + $2 + line_ends[num_lines]
            num_lines += 1
            line = $3
          else
            text += line + line_ends[num_lines]
            num_lines += 1
            line = ""
          end
          curr_line_width = 0
        else
          text += line
          curr_line_width += line.size
          line = ""
        end
        break if num_lines >= @LINE_LIMIT
     end
      break if num_lines >= @LINE_LIMIT
    end
    str2 = text.gsub("\n", '\\n')
    #print("summarized <<#{str}>> to <<#{str2}>>\n")
    return str2
  end
  
  def lookup(func_name, parts)
    yaml1 = @flist[func_name]
    return nil unless yaml1
    fdir = parts.join("/")
    yaml1.each {|y|
      if y['dir'] == fdir
        #print "           lookup succeeded: (#{func_name} in #{parts.join('/')} ==> #{y.inspect}\n"
        return y
      end
    }
    #print "******** lookup failed: (#{func_name} in #{parts.join('/')} ==> #{yaml1.inspect}\n"
    return nil
  end
end # end class

infile = argv[0]
Usage(opts, "#{infile} not found") unless File.exists?(infile)


begin
  require 'xml-simple'
rescue LoadError
  require 'rubygems' unless Object.constants.find{|f| f == 'Gem'}
  require_gem 'xml-simple'
end

verbose = options.verbose
f = Finder.new(options.override)
rdocdir = options.rdoc

class Array
 def <(x)
   i = 0
   m = self.size
   m = x.size if x.size < m
   while (i < m)
     return true if self[i] < x[i]
     return false if self[i] > x[i]
     i += 1
   end
   return self.size < m
 end
end

if !File.directory?(rdocdir)
  puts "Need to specify --gemdir to find rubygems" unless options.gemdir
  thisdir = Dir.getwd
  Dir.chdir(options.gemdir)
  raw_dirs = %w/actionmailer actionpack actionwebservice activerecord activesupport/
  latest_dirs = {}
  Dir.glob("a*").each do |dirname|
    raw_dirs.each do |rd|
      if dirname.index(rd) == 0
        if !latest_dirs[rd]
          latest_dirs[rd] = dirname
        else
          new_nums = dirname[rd.size + 1 .. -1].split('.').map{|x|x.to_i}
          old_nums = latest_dirs[rd][rd.size + 1 .. -1].split('.').map{|x|x.to_i}
          if old_nums < new_nums
            puts "replace"
            latest_dirs[rd] = dirname
          end
        end
        break
      end
    end
  end
  pp latest_dirs

  cmd = %Q[rdoc --ri --op="#{thisdir}/rdoc" #{latest_dirs.values.join(" ")}]
  puts "You'll have to run this command manually from the rails dir"
  puts cmd
  exit
  system(cmd)
  Dir.chdir(thisdir)
  # Go and build it
end

$stderr.puts("Reading rails rdoc (#{options.rdoc})...") if verbose
f.build(options.rdoc)

$stderr.puts("Reading/parsing #{File.basename(infile)}...") if verbose
orig_xml = XmlSimple.xml_in(infile, {"KeepRoot" => true})
tree_file = orig_xml['codeintel'][0]['file'][0]
blob_file = tree_file['scope'][0]
$stderr.puts("Annotating tree...") if verbose
f.annotate(blob_file)
if f.changes > 0
  $stderr.puts("Made #{f.changes} insertions") if verbose
  xout = XmlSimple.xml_out(orig_xml, {"KeepRoot" => true})
  xout = xout.gsub('\\n', '&#xA;')
  outfile = options.outfile
  if outfile
    fd = File.open(outfile, 'w')
  else
    fd = $stdout
  end
  fd.write(xout + "\n")
elsif verbose
  puts "No changes made"
end

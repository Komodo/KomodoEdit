# Test driver for gencix.rb
#
# Run each binary module we find, save in the test/actual
# directory, and compare against the reference cix file.

require 'find'

class Finder

  def initialize(paths)
    @paths = paths
    @visited = {}
  end

  def found_later(fullpath)
    @paths.each {|ref_path|
      if ref_path == @path
        #puts "Skipping path #{ref_path}"
        next
      elsif ref_path.index(@path) == 0
        #puts "Path #{ref_path} looks better than current path #{@path}"
        return true
      end
    }
    false
  end
  
  def find(path)
    @path = path
    Find.find(@path) do |f|
      if File.file?(f) && f.match(/[\w\d_]\.so$/)
        if found_later(f)
          next
        end
        libname = f[@path.length + 1 .. -1][0 .. -4]
        if @visited.has_key?(libname)
          next # already saw
        else
          @visited[libname] = nil
        end
        output_file = "test/binary/output/#{libname}.cix"
        actual_file = "test/binary/actual/#{libname}.cix"
        actual_dir = File.dirname(actual_file)
        if actual_dir != "." && ! File.exists?(actual_dir)
          Dir.mkdir(actual_dir)
        end
        cmd = %Q(ruby binary-gencix.rb -o "#{actual_file}" "#{libname}")
        # puts "#{cmd}"
        if !system(cmd)
          if not %W[enumerator io/wait].include?(libname)
            puts "Failed to run #{cmd}: #{$?.exitstatus}"
          else
            puts "#{libname} skipped"
          end
        else
          cmd = %Q(diff -w "#{output_file}" "#{actual_file}")
          res = `#{cmd}`
          if $?.exitstatus > 0
            puts "#{libname} diffs failed: #{res[0 .. 200]}..."
          else
            puts "#{libname} ok"
          end
        end
      end
    end
  end
end

%w/binary builtin std/.each {|dir|
  if !File.exists?("test/#{dir}/actual")
    Dir.mkdir("test/#{dir}/actual")
  end
}

if true
finder = Finder.new($:)
$:.each {|path|
  # puts "Looking in #{path}"
  finder.find(path)
}
end

output_file = "test/builtin/output/builtins.rb.cix"
actual_file = "test/builtin/actual/builtins.rb.cix"

cmd = %Q(ruby builtins-gencix.rb -o "#{actual_file}")
if !system(cmd)
  puts "Failed to run #{cmd}: #{$?.exitstatus}"
else
  cmd = %Q(diff -w "#{output_file}" "#{actual_file}")
  res = `#{cmd}`
  if $?.exitstatus > 0
    puts "builtin diffs failed: #{res[0 .. 200]}..."
  else
    puts "builtins ok"
  end
end

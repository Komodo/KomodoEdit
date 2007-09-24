def ignore(pattern, dir)
  system "svn propset svn:ignore '#{pattern}' #{dir}"
  #puts "\t ignoring #{dir}/#{pattern}"
end

namespace :svn do

  desc "Configure svn:ignore properties"
  task :configure do
    puts "Setting svn:ignore properties:"
    ignore '*', 'tmp/cache'
    ignore '*', 'tmp/sessions'
    ignore '*', 'tmp/sockets'
    ignore '*.log', 'log'
    ignore 'lighttpd.conf', 'config'
    ignore 'schema.rb', 'db'
    puts "Done."
  end
   
  desc "Add all new files to subversion"
  task :add do
     system "svn status | grep '^\?' | sed -e 's/? *//' | sed -e 's/ /\ /g' | xargs svn add"
  end

end

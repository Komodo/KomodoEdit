require 'spec/rake/spectask'

desc 'Run all model and controller specs'
task :spec do
  Rake::Task["spec:models"].invoke       rescue got_error = true
  Rake::Task["spec:controllers"].invoke rescue got_error = true

  # not yet supported
  #if File.exist?("spec/integration")
  #  Rake::Task["spec:integration"].invoke rescue got_error = true
  #end

  raise "RSpec failures" if got_error
end

namespace :spec do
  desc "Run the specs under spec/models"
  Spec::Rake::SpecTask.new(:models => "db:test:prepare") do |t|
    t.spec_files = FileList['spec/models/**/*_spec.rb']
  end

  desc "Run the specs under spec/controllers"
  Spec::Rake::SpecTask.new(:controllers => "db:test:prepare") do |t|
    t.spec_files = FileList['spec/controllers/**/*_spec.rb']
  end
  
  desc "Print Specdoc for all specs"
  Spec::Rake::SpecTask.new('doc') do |t|
    t.spec_files = FileList[
      'spec/models/**/*_spec.rb',
      'spec/controllers/**/*_spec.rb'
    ]
    t.spec_opts = ["--format", "specdoc"]
  end

  namespace :db do
    namespace :fixtures do
      desc "Load fixtures (from spec/fixtures) into the current environment's database.  Load specific fixtures using FIXTURES=x,y"
      task :load => :environment do
        require 'active_record/fixtures'
        ActiveRecord::Base.establish_connection(RAILS_ENV.to_sym)
        (ENV['FIXTURES'] ? ENV['FIXTURES'].split(/,/) : Dir.glob(File.join(RAILS_ROOT, 'spec', 'fixtures', '*.{yml,csv}'))).each do |fixture_file|
          Fixtures.create_fixtures('spec/fixtures', File.basename(fixture_file, '.*'))
        end
      end
    end
  end
end

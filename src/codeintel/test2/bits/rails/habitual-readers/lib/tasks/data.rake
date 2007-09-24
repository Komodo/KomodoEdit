namespace :db do
  namespace :data do
    require File.dirname(__FILE__) + '/../../config/environment'
    
    def models_of_interest 
      [ 
        Reader,
        Book,
        Reading,
        Tag,
        Tagging
      ]    
    end
    
    desc "Dump models of interest to yaml"
    task :dump_models_of_interest do
      models_of_interest.each do |model|
        model.dump_to_file
      end
    end

    desc "Load models of interest from yaml"
    task :load_models_of_interest do
      models_of_interest.each do |model|
        model.load_from_file
      end
    end
  end
end
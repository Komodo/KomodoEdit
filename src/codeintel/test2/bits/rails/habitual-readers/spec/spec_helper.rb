ENV["RAILS_ENV"] = "test"
require File.expand_path(File.dirname(__FILE__) + "/../config/environment")

class SpecTestCase < Test::Unit::TestCase
  self.use_transactional_fixtures = true
  self.use_instantiated_fixtures  = false
  self.fixture_path = RAILS_ROOT + '/spec/fixtures'

  # You can set up your global fixtures here, or you
  # can do it in individual contexts
  #fixtures :table_a, :table_b

  def run(*args)
  end

  def setup
    super
  end

  def teardown
    super
  end
end

module Spec
  module Runner
    class Context
      def before_context_eval
        inherit SpecTestCase
      end
    end
  end
end

Test::Unit.run = true
require File.dirname(__FILE__) + '/../test_helper'
require 'readings_controller'

# Re-raise errors caught by the controller.
class ReadingsController; def rescue_action(e) raise e end; end

class ReadingsControllerTest < Test::Unit::TestCase
  def setup
    @controller = ReadingsController.new
    @request    = ActionController::TestRequest.new
    @response   = ActionController::TestResponse.new
  end

  # Replace this with your real tests.
  def test_truth
    assert true
  end
end

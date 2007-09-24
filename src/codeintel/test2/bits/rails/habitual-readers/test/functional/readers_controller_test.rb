require File.dirname(__FILE__) + '/../test_helper'
require 'readers_controller'

# Re-raise errors caught by the controller.
class ReadersController; def rescue_action(e) raise e end; end

class ReadersControllerTest < Test::Unit::TestCase
  def setup
    @controller = ReadersController.new
    @request    = ActionController::TestRequest.new
    @response   = ActionController::TestResponse.new
  end

  # Replace this with your real tests.
  def test_truth
    assert true
  end
end

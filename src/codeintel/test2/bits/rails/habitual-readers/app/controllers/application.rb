# Filters added to this controller will be run for all controllers in the application.
# Likewise, all the methods added will be available for all controllers.
class ApplicationController < ActionController::Base
  
  before_filter :get_logged_in_reader, :set_show_actions
  
  def check_authentication 
    unless session[:reader] 
      session[:intended_action] = action_name 
      session[:intended_controller] = controller_name 
      redirect_to :controller => "admin", :action => "signin" 
    end 
  end 

  def get_logged_in_reader
    @logged_in_reader = Reader.find(session[:reader]) if session[:reader]
  end
  
  def set_show_actions
    @show_actions = (session[:reader] != nil)
    true
  end
end
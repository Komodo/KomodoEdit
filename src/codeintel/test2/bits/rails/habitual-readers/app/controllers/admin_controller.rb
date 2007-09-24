class AdminController < ApplicationController
  before_filter :check_authentication, :except => [:signin]
  def signin 
    if request.post? 
      session[:reader] = Reader.authenticate(params[:username], params[:password]).id 
      redirect_to :controller => "home" 
    end 
  end 
  def signout 
    session[:reader] = nil 
    redirect_to :controller => "home" 
  end 
end

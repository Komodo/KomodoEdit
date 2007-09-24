class HomeController < ApplicationController
  def index
    @readings = Reading.find(:all, :limit => 10, :order => "date_read DESC", :include => ["reader", "book"])
    @tags = Book.weighted_tags
  end
end

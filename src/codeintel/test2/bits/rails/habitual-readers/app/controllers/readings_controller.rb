class ReadingsController < ApplicationController
  
  before_filter :get_book, :except => %w(update destroy)
  
  def new
    @reading = Reading.new
    set_relationships
    render :action => "form"
  end

  def create
    @reading = Reading.new(params[:reading])
    set_relationships
    if @reading.save
      @reading.book.add_tag(params[:tags])
      flash[:notice] = "Reading saved"
      redirect_to :controller => "books"
    else
      render :action => "form"
    end
  end

  def edit
    @reading = Reading.find(params[:id])
    render :action => "form"
  end

  def update
    @reading = Reading.find(params[:id])
    if @reading.update_attributes(params[:reading])
      flash[:notice] = "Reading saved"
      redirect_to :action => "show", :id => @reading
    else
      render :action => "form"
    end
  end

  def destroy
    @reading = Reading.find(params[:id])
    @reading.destroy
    redirect_to :back
  end
    
  private
    def get_book
      @book = Book.find_by_title(params[:book_id])
    end
    
    def set_relationships
      @reading.book = @book
      @reading.reader = @logged_in_reader
    end
end

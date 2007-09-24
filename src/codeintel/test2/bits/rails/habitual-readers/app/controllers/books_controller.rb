class BooksController < ApplicationController
  
  before_filter :find_book, :except => ["index", "create", "new"]
  
  def index
    @book_paginator, @books = paginate :books, :include => "tags", :order => "title"
  end

  def show
    @reading_paginator, @readings = paginate :readings, :conditions => ["book_id = ?", @book.id], :order => "date_read"
  end

  def new
    @book = Book.new
    render :action => "form"
  end

  def create
    @book = Book.new(params[:book])
    if @book.save
      flash[:notice] = "Book saved"
      redirect_to :action => "show", :id => @book
    else
      render :action => "form"
    end
  end

  def edit
    render :action => "form"
  end

  def update
    if @book.update_attributes(params[:book])
      flash[:notice] = "Book saved"
      redirect_to :action => "show", :id => @book
    else
      render :action => "form"
    end
  end

  def destroy
    @book.destroy
    redirect_to :action => "index"
  end
  
  private
  def find_book
    @book = Book.find_by_title(params[:id])
  end
end

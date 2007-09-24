class ReadersController < ApplicationController

  before_filter :find_reader, :except => ["index", "create", "new"]
  
  def index
    @reader_paginator, @readers = paginate :readers, :order => "fullname"
  end

  def show
    @reading_paginator, @readings = paginate :readings, :conditions => ["reader_id = ?", @reader.id], :order => "date_read DESC"
  end

  def new
    @reader = Reader.new
    @reader_image = ReaderImage.new
    render :action => "form"
  end

  def create
    @reader = Reader.new(params[:reader])
    if @reader.save
      flash[:notice] = "Reader saved"
      redirect_to :action => "show", :id => @reader
    else
      render :action => "form"
    end
  end

  def edit
    render :action => "form"
  end

  def update
    if @reader.update_attributes(params[:reader])
      flash[:notice] = "Reader saved"
      redirect_to :action => "show", :id => @reader
    else
      render :action => "form"
    end
  end

  def destroy
    @reader.destroy
    redirect_to :action => "list"
  end
    
  private
  def find_reader
    @reader = Reader.find_by_username(params[:id])
    @reader_image = @reader.reader_image || ReaderImage.new
  end
    
end

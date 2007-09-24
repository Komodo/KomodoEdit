class ReaderImagesController < ApplicationController
  def new
    @reader_image = ReaderImage.new
    render :action => "form"
  end
  def create
    @reader_image = ReaderImage.new(params[:reader_image])
    @reader = Reader.find_by_username(params[:reader_id])
    @reader_image.reader = @reader
    if @reader_image.save
      flash[:notice] = "Reader Image saved"
      redirect_to reader_url(@reader)
    else
      render :action => "form"
    end
  end
  def edit
    render :action => "form"
  end
  def update
    @reader_image = ReaderImage.find(params[:id])
    @reader = Reader.find_by_username(params[:reader_id])
    if @reader_image.update_attributes(params[:reader_image])
      flash[:notice] = "Reader Image saved"
      redirect_to reader_url(@reader)
    else
      render :action => "form"
    end
  end
end

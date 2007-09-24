class TagsController < ApplicationController
  def index
    @tag_paginator, @tags = paginate :tags, :order => "name"
  end

  def show
    @tag = Tag.find_by_name(params[:id])
    @books = Book.find_tagged_with(@tag.name)
  end
end

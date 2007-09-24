class AddAmazonMetadata < ActiveRecord::Migration
  def self.up
    add_column "books", "image_url_small", :string
    add_column "books", "image_url_large", :string
    add_column "books", "url", :string
  end

  def self.down
    remove_column "books", "image_url_small"
    remove_column "books", "image_url_large"
    remove_column "books", "url"
  end
end

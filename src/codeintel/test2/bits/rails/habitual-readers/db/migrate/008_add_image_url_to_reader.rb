class AddImageUrlToReader < ActiveRecord::Migration
  def self.up
    add_column "readers", "image_url", :string
  end

  def self.down
    remove_column "readers", "image_url"
  end
end

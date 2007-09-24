class AddAmazonTimeStamp < ActiveRecord::Migration
  def self.up
    add_column "books", "amazon_last_checked", :datetime
  end

  def self.down
    remove_column "books", "amazon_last_checked"
  end
end

class AddReaderIdToReaderImage < ActiveRecord::Migration
  def self.up
    add_column "reader_images", "reader_id", :integer
  end

  def self.down
    remove_column "reader_images", "reader_id"
  end
end

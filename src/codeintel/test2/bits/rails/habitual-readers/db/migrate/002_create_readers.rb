class CreateReaders < ActiveRecord::Migration
  def self.up
    create_table :readers do |t|
      t.column "username", :string
      t.column "fullname", :string
      t.column "bio", :text
    end
  end

  def self.down
    drop_table :readers
  end
end

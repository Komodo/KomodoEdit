class AddUnameAndPasswordToReaders < ActiveRecord::Migration
  def self.up
    add_column "readers", "password_salt", :string
    add_column "readers", "password_hash", :string
  end

  def self.down
    remove_column "readers", "password_salt"
    remove_column "readers", "password_hash"
  end
end

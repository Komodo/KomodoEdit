class CreateBooks < ActiveRecord::Migration
  def self.up
    create_table :books do |t|
      t.column "title", :string
      t.column "author", :string
      t.column "isbn", :string
      t.column "summary", :text
      # t.column :name, :string
    end
  end

  def self.down
    drop_table :books
  end
end

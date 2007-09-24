class CreateReadings < ActiveRecord::Migration
  def self.up
    create_table :readings do |t|
      t.column "book_id", :integer
      t.column "reader_id", :integer
      t.column "date_read", :datetime
      t.column "reading_time", :integer
      t.column "notes", :text
      # t.column :name, :string
    end
  end

  def self.down
    drop_table :readings
  end
end

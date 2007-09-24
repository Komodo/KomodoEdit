class AddTaggableSupport < ActiveRecord::Migration
  def self.up
    #Table for your Tags
    create_table :tags do |t|
      t.column :name, :string
    end

    create_table :taggings do |t|
      t.column :tag_id, :integer
      #id of tagged object
      t.column :taggable_id, :integer
      #type of object tagged
      t.column :taggable_type, :string
    end
  end

  def self.down
    drop_table :tags
    drop_table :taggings
  end
end

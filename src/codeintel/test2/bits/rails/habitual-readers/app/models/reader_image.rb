class ReaderImage < ActiveRecord::Base
  belongs_to :reader
  acts_as_attachment :storage => :file_system, :thumbnails => {:thumb => "150"}
  def as_thumb
    self.thumbnails.find_by_thumbnail("thumb").public_filename
  end
end

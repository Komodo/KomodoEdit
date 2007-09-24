class Reading < ActiveRecord::Base
  belongs_to :book
  belongs_to :reader

  def date_read_for_display
    date_read.strftime("%d %b %Y")
  end
end

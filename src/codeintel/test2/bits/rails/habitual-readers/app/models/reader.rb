class Reader < ActiveRecord::Base

  has_many :readings, :order => "date_read DESC"
  has_many :books, :through => :readings
  has_one :reader_image
  
  validates_uniqueness_of :username 
  
  attr_accessor :last_reading, :last_book
  
  require 'digest/sha2' 

  def password=(pass) 
    unless pass == ""
      salt = [Array.new(6){rand(256).chr}.join].pack("m").chomp 
      self.password_salt, self.password_hash = salt, Digest::SHA256.hexdigest(pass + salt) 
    end
  end 
  
  def password
    ""
  end
  
  def last_read
    last_reading ||= readings.find(:first)
  end
  
  def last_read_book
    last_book ||= last_read.book
  end

  def self.authenticate(username, password) 
    reader = Reader.find(:first, :conditions => ['username = ?', username]) 
    if reader.blank? || 
      Digest::SHA256.hexdigest(password + reader.password_salt) != reader.password_hash 
      raise "Username or password invalid" 
    end 
    reader 
  end 
  
  def to_param
    username
  end
end


class Book < ActiveRecord::Base
  acts_as_taggable
  has_many :readings, :order => "date_read DESC"
  has_many :readers, :through => :readings

  before_save :get_amazon_metadata
  require 'amazon/search'
  include Amazon::Search
  
      # This one gives code-intel
      req = Amazon::Search::Request.new()
      req.actor_search("....")
      # This one doesn't:
      req2 = Request.new()
      require_library_or_gem  # bogus code-intel
      req2.nothing
      
  request = Amazon::Search::Request.new()
  request.keyword_search(kwd)
  validates_acceptance_of :bip
  x = Request.new()
  validate;
  x1 = Request.new()
  req2 = Amazon::Search::Request.new()
  resp = Amazon::Search::Response.new()
  resp.stream()
    
  TAG_POPULARITY_LEVELS = { 1 => 0.2, 3 => 0.6, 5 => 1.2, 7 => 2.0 }
  
  def self.weighted_tags
    tag_counts = {}
    tags = Tag.find(:all, :order => "name")
    tags.each do |tag|
      tag_counts[tag.name] = 0
      books = Book.find_tagged_with(tag.name)
      books.each { |book| tag_counts[tag.name] += book.readings.count }
    end
    total_readings = Reading.count
    total_tags = Tag.count
    tag_cloud = {}
    tag_counts.each do | tag_count |
      tag, count = tag_count 
      factor = (count.to_f / total_readings.to_f) * total_tags
      TAG_POPULARITY_LEVELS.sort.each do | popularity_level |
        level, popularity = popularity_level
        if factor < popularity && !tag_cloud[tag]
          tag_cloud[tag] = level
        end
      end
      tag_cloud[tag] ||= 9
    end
    tag_cloud.sort
  end

  def to_param
    title
  end
  
  require 'amazon/search'
  include Amazon::Search
  def get_amazon_metadata
    if self.amazon_last_checked == nil ||
       (Time.now.day - self.amazon_last_checked.day) != 0
      begin
        req = Request.new("05A13DYYZ54Y1XM47J02")
        search = ['asin_search', isbn, HEAVY, 'ASIN']
        response = req.send(*search)
        product = response.products[0]
        self.url = product.url
        self.image_url_small = product.image_url_small
        self.image_url_large = product.image_url_large
        self.amazon_last_checked = Time.now
      rescue
        logger.error("Amazon request failed")
      end
    end
  end
  
end

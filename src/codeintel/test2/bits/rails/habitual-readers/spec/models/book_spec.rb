require File.dirname(__FILE__) + '/../spec_helper'

context "The Book model" do
  fixtures :books

  specify "should count two Books" do
    Book.count.should_be 2
  end

  specify "should find HHGTTG" do
    book = Book.find(1)
    book.should_equal books(:HHGTTG)
    book.title.should_equal "Hitchhikers Guide To The Galaxy"
    book.author.should_equal "Douglas Adams"
    book.isbn.should_equal "0345391802"
    book.summary.should_equal "Laugh a minute satirical sci-fi"
  end
end

context "A new book" do
  fixtures :books
  
  specify "should have no data" do
    book = Book.new
    book.title.should_be nil
    book.author.should_be nil
    book.isbn.should_be nil
    book.summary.should_be nil
  end

  specify "should have no readers" do
    book = Book.new
    book.should_have(0).readers
  end
  
end

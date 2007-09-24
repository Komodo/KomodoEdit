require File.dirname(__FILE__) + '/../spec_helper'

context "The Reader model" do
  fixtures :readers

  specify "should count two Readers" do
    Reader.count.should_be 2
  end

  specify "should find Ben" do
    reader = Reader.find(1)
    reader.should_equal readers(:Ben)
    reader.username.should_equal "benj72"
    reader.fullname.should_equal "Ben Askins"
    reader.bio.should_equal "Eats books for breakfast"
  end
end

context "A new reader" do
  
  specify "should have no data" do
    reader = Reader.new
    reader.username.should_be nil
    reader.fullname.should_be nil
    reader.bio.should_be nil
  end

  specify "should have read no books" do
    reader = Reader.new
    reader.should_have(0).books
  end
end

context "Ben" do
  fixtures :readers, :books, :readings
  specify "should have read HHGTTG" do
    ben = readers(:Ben)
    ben.should_have(1).books
    ben.books.to_a.should_include books(:HHGTTG)
  end
  
  specify "should not have read LOTR" do
    ben = readers(:Ben)
    ben.should_have(1).books
    ben.books.to_a.should_not_include books(:LOTR)  
  end
end
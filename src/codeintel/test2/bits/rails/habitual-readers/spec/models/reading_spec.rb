require File.dirname(__FILE__) + '/../spec_helper'

context "The reading model" do
  fixtures :readings

  specify "should count two Readings" do
    Reading.count.should_be 2
  end

  specify "should have more specifications" do
    violated "not enough specs"
  end
end


require 'delegate'
class Tempfile < DelegateClass(File)
end

# Test mixin requirement

class Child < Parent
  include Mixin
  def initialize
  end
  def hoohah
  end
end

t = Tempfile.new


class Foo
  def self.cmethod(a, b, c)
    return 42
  end
  
  def imethod(d1, e2, *f3)
    return "Hello"
  end
  
  def extend_me()
    class << self
      def imethod_2(x)
        return 2 * x
      end
    end
  end
end
f3 = Foo.new()
puts f3.imethod(1,2,3)
begin
  puts f3.imethod_2(4)
rescue =>  ex
  puts ex
end
f3.extend_me()
puts f3.imethod_2(5)

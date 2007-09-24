require 'outer'
include Outer

module M1
  require 'mod1'
  include Mod1

  class C1
    require 'thing/mod2'
    include Mod2a

    def foo(a,b)
      include Mod2b
    end
  end
end

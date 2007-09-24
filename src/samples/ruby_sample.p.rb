#!/usr/bin/ruby
# Copyright (c) 2000-2006 ActiveState Software Inc.

# Use this sample script to explore some of Komodo's Ruby features.

#---- Auto-Indent
#     - Note that most Ruby programmers, and programs, use 2-space
#       indentation, so you should probably make sure Komodo is set
#       to 2-spaces while writing Ruby code.
#     - Indentation incremented in definitions, control blocks, and
#       do...end and brace blocks.
#     - Dedenters, like 'end' or 'else' are automatically dedented
#       if a character is typed at the end of that line.

#---- Code Folding:
#    - Click the "+" and "-" symbols in the left margin.
#    - Use View|Fold to collapse or expand all blocks.

#---- Syntax Coloring:
#    - Language elements are colored according to the Fonts and Colors
#      preference.


$global_1 = 12

class FruitSalad
  @@times_called = 0
  def initialize(fruits)
    @@times_called += 1
    @ingredients = {}
    @num_served = 0
    add(fruits)
  end

  def add(fruits)
    fruits.each do | name, count |
      @ingredients[name] = 0 unless @ingredients.has_key?(name)
      @ingredients[name] += count
    end
  end
  
  def accumulate(sum, item)
    sum + item[1]
  end

  def servings()
    # Step into a block
    total_fruits = @ingredients.inject(0) {|sum, item| accumulate(sum, item)}
    total_fruits - @num_served
  end

  def serve(n=1)
    s = servings
    raise "Not enough fruit -- requested #{n}, have #{s}" if n > s
    @num_served += n
  end
end # end class

fs = FruitSalad.new({'apples' => 4, 'bananas' => 3, 'grapes' => 2})
puts "We have #{fs.servings} servings"
fs.serve(4)
puts "We now have #{fs.servings} servings"
fs.serve(fs.servings)
begin
  fs.serve(4)
rescue => msg
  puts "Caught exception: #{msg}"
  fs.add({'cherries' => 5, 'apples' => 2})
  fs.serve(4)
end
puts "Finish with #{fs.servings} servings for leftovers"


#---- Background Syntax Checking:
#     - Syntax errors are underlined in red.
#     - Syntax warnings are underlined in green.
#     - Configure Ruby preferences to customize errors and warnings.
#     - Position the cursor over the underline to view the error
#       or warning message.

"hello there";




# At the top-level, "self" is an Object instance.
puts "top-level: self=#{self}"   # -> main
puts "top-level: self.class=#{self.class}" # -> Object

module MyModule
    # In a class, "self" is a class object.
    puts "module: self=#{self}"
    puts "module: self.class=#{self.class}"
    def mymoduleinstancemethod
        # In an instance method "self" is an instance of the class.
        puts "module instance method: self=#{self}"
        puts "module instance method: self.class=#{self.class}"
    end
    def MyModule.mymoduleclassmethod
        # In an instance method "self" is an instance of the class.
        puts "module class method: self=#{self}"
        puts "module class method: self.class=#{self.class}"
    end
end

MyModule::mymoduleclassmethod

class MyClass
    include MyModule
    # In a class, "self" is a class object.
    puts "class: self=#{self}"
    puts "class: self.class=#{self.class}"
    def myinstancemethod
        # In an instance method "self" is an instance of the class.
        puts "class instance method: self=#{self}"
        puts "class instance method: self.class=#{self.class}"
    end
    def MyClass.myclassmethod
        # In an instance method "self" is an instance of the class.
        puts "class method: self=#{self}"
        puts "class method: self.class=#{self.class}"
    end
end

MyClass.myclassmethod
c = MyClass.new
c.myinstancemethod
c.mymoduleinstancemethod




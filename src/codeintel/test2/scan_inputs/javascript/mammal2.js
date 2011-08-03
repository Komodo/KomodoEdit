Cat.prototype.constructor=Cat;
Cat.prototype.meow=function() { dump("meow"); }
function Cat(name){
    this.name=name;
}
Cat.prototype.purr=function() { dump("purr"); }


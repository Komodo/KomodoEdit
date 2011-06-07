function ClassName() {}
ClassName.prototype = { constructor: ClassName };

var alias = ClassName;
var instance = new ClassName();
alias.prototype.method = function() {}
instance.method();

var loop = loop; /* make sure it doesn't inifinite loop */
loop.foo = loop; /* this should fail and loop becomes a normal variable */

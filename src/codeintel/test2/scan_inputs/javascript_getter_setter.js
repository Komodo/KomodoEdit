// Testing getter and setter names
//
// Test 1
// Should define a class jsclass with variables "num" and "_num".
//
function jsclass() {
    this._num = 0;
}
jsclass.prototype.__defineGetter__("num", function() { return this._num });
jsclass.prototype.__defineSetter__("num", function(new_num) {
    this._num = new_num;
});

//
// Test 2
// Should define a class "myclass" with variables "_rows" and "rowCount".
//
function myclass(initial_rows) {
    this._rows = initial_rows;
}
myclass.prototype = {
    get rowCount() { return this._rows.length; }
}

//
// Test 3
// Should define a class "myclass" with variables "_name" and "name".
//
function thirdclass() {
    this._name = "name";
}
thirdclass.prototype = {
    set name(newname) { if (newname) this._name = newname; }
}

//
// Test 4
// New style "Object.defineProperty" - JavaScript 1.8.5
//
var foo = {};
Object.defineProperty(foo, "prop", {
  get: function() this._v + 5,
  set: function(v) { this._v = v + 10; return this.prop; },
  configurable: true,
  enumerable: true
});

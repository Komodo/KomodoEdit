/* Copyright (c) 2006 YourNameHere
   See the file LICENSE.txt for licensing information. */

TestCode = function(a1) {
    this.a1 = a1;
}
TestCode.prototype = {
    c1: "c1",
    test: function() {},
    enabled: true
}
var x;
var t = x = new TestCode("a1");
t.c1 = "new c1";
x.test();

var item1 = 7, item2 = 'cat', item3 = [];
item2.toString();
item3.toString();

var low = -1, high = gFastIndex;

/*
  Ensure a variable named "this[0]" is not created.
  http://bugs.activestate.com/show_bug.cgi?id=77854
*/
x = this[0] = 1;

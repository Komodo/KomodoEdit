try {
dump("Loading test_test.js...\n");

// example of setting up a class based test case
function MyTestCase(name) {
  Casper.UnitTest.TestCase.apply(this, [name]);
}
MyTestCase.prototype = new Casper.UnitTest.TestCase();
MyTestCase.prototype.constructor = MyTestCase;
MyTestCase.prototype.test_simple = function() {
  this.assert(true);
}
MyTestCase.prototype.test_fail = function() {
  this.assertFalse(false);
}
MyTestCase.prototype._internal_test = function() {
  this.assert(true);
}
MyTestCase.prototype.test_class_func = function() {
  this._internal_test();
}

// we do not pass an instance of MyTestCase, they are created in MakeSuite
Casper.UnitTest.testRunner.add(Casper.UnitTest.MakeSuite("A class based test case", MyTestCase));


function test_1a(){
  this.assert(true);
  var trueVar = true;
  this.assert(trueVar);
  this.assertTrue(true);
  this.assertTrue(trueVar);
  this.assertFalse(false);
  var falseVar = false;
  this.assertFalse(falseVar);
  this.assertNull(null);
  var nullVar = null;
  this.assertNull(nullVar);
  this.assertNotNull("something");
  var notNullVar = "something";
  this.assertNotNull(notNullVar);
  this.assertNaN("text");
  var NaNVar = "text";
  this.assertNaN(NaNVar);
  this.assertNotNaN(5);
  var number = 13;
  this.assertNotNaN(number);
  this.assertNotUndefined("defined");
  var defined = "something";
  this.assertNotUndefined(defined);
  var notDefined;
  this.assertUndefined(notDefined);
}

function test_2a(){
  this.assertEquals(5, 5);
  var number = 5;
  this.assertEquals(5, number);
  this.assertNotEquals(5, 13);
  this.assertNotEquals(13, number);
  
  this.assertEquals("something", "something");
  var text = "something";
  this.assertEquals("something", text);
  this.assertNotEquals("other", "something");
  this.assertNotEquals("other", text);
  
  var object = new Object();
  object.attribute = "value";
  var object2 = new Object();
  object2.attribute = "abcd";
  this.assertEquals(object, object);
  this.assertNotEquals(object, object2);
}

function test_3a(){
  var string = "casper";
  this.assertRegExp("asp", string);
  this.assertNotRegExp("mozilla", string);
}

function test_4a(){
	var string = "string2";
	var number = 1;
	var b_oolean = true;
	var f_unction = test_3a;
	var object = new Object();
  this.assertTypeOf("string", string);
  this.assertTypeOf("number", number);
  this.assertTypeOf("boolean", b_oolean);
  this.assertTypeOf("function", f_unction);
  this.assertTypeOf("object", object);
  this.assertNotTypeOf("string", number);
  this.assertNotTypeOf("number", string);
  this.assertNotTypeOf("boolean", f_unction);
  this.assertNotTypeOf("function", object);
  this.assertNotTypeOf("object", b_oolean);
}

// example of setting up a function based test suite
var myTestSuite1 = new Casper.UnitTest.TestSuite("Casper Passing TestSuite");
myTestSuite1.add(new Casper.UnitTest.TestCase("TestCase Assert Functions", test_1a));
myTestSuite1.add(new Casper.UnitTest.TestCase("TestCase AssertEquals Functions", test_2a));
myTestSuite1.add(new Casper.UnitTest.TestCase("TestCase AssertRegExp Functions", test_3a));
myTestSuite1.add(new Casper.UnitTest.TestCase("TestCase AssertTypeOf Functions", test_4a));
Casper.UnitTest.testRunner.add(myTestSuite1);


function test_1b(){
  var extype = Casper.UnitTest.AssertException;
  this.failUnlessRaises(extype, this.failUnlessRaises, [extype, this.assert, [true]], "Test Failure of failUnlessRaises");
  this.failUnlessRaises(extype, this.assert, [false], "Test Failure of assert(false)");
  var trueVar = false;
  this.failUnlessRaises(extype, this.assert, [trueVar], "Test Failure of assert(true)");
  this.failUnlessRaises(extype, this.assertTrue, [false], "Test Failure of assertTrue(false)");
  this.failUnlessRaises(extype, this.assertTrue, [trueVar], "Test Failure of assertTrue(true)");
  this.failUnlessRaises(extype, this.assertFalse, [true], "Test Failure of assertFalse(true)");
  var falseVar = true;
  this.failUnlessRaises(extype, this.assertFalse, [falseVar], "Test Failure of assertFalse(false)");
  this.failUnlessRaises(extype, this.assertNull, ["not null"], "Test Failure of assertNull(not null)");
  var nullVar = "not null";
  this.failUnlessRaises(extype, this.assertNull, [nullVar], "Test Failure of assertNull(null)");
  this.failUnlessRaises(extype, this.assertNotNull, [null], "Test Failure of assertNotNull(null)");
  var notNullVar = null;
  this.failUnlessRaises(extype, this.assertNotNull, [notNullVar], "Test Failure of assertNotNull(not null)");
  this.failUnlessRaises(extype, this.assertNaN, [5], "Test Failure of assertNaN(5)");
  var NaNVar = 5;
  this.failUnlessRaises(extype, this.assertNaN, [NaNVar], "Test Failure of assertNaN(5)");
  this.failUnlessRaises(extype, this.assertNotNaN, ["NaN"], "Test Failure of assertNotNaN(NaN)");
  var number = "NaN";
  this.failUnlessRaises(extype, this.assertNotNaN, [number], "Test Failure of assertNotNaN('NaN')");
  var defined;
  this.failUnlessRaises(extype, this.assertNotUndefined, [defined], "Test Failure of assertNotUndefined(undefined)");
  var notDefined = "something";
  this.failUnlessRaises(extype, this.assertUndefined, [notDefined], "Test Failure of assertUndefined(defined)");
}

function test_2b(){
  var extype = Casper.UnitTest.AssertException;
  this.failUnlessRaises(extype, this.assertEquals, [13, 5]);
  var number = 5;
  this.failUnlessRaises(extype, this.assertEquals, [13, number]);
  this.failUnlessRaises(extype, this.assertNotEquals, [5, 5]);
  this.failUnlessRaises(extype, this.assertNotEquals, [5, number]);
  
  this.failUnlessRaises(extype, this.assertEquals, ["other", "something"]);
  var text = "something";
  this.failUnlessRaises(extype, this.assertEquals, ["other", text]);
  this.failUnlessRaises(extype, this.assertNotEquals, ["something", "something"]);
  this.failUnlessRaises(extype, this.assertNotEquals, ["something", text]);
  
  var object = new Object();
  object.attribute = "value";
  var object2 = new Object();
  object2.attribute = "value";
  this.failUnlessRaises(extype, this.assertNotEquals, [object2, object]);
  this.failUnlessRaises(extype, this.assertNotEquals, [object, object]);
}


var myTestSuite2 = new Casper.UnitTest.TestSuite("Casper Failing TestSuite");
myTestSuite2.add(new Casper.UnitTest.TestCase("TestCase Falling Assert Functions", test_1b));
myTestSuite2.add(new Casper.UnitTest.TestCase("TestCase Falling AssertEquals Functions", test_2b));
Casper.UnitTest.testRunner.add(myTestSuite2);


function test_1d(){
  // this will try to call an undefined function, which raises a TypeError
  this.failUnlessRaises(TypeError);
}
var myTestSuite4 = new Casper.UnitTest.TestSuite("Casper Breaking TestSuite");
myTestSuite4.add(new Casper.UnitTest.TestCase("Test Case 1d", test_1d));
Casper.UnitTest.testRunner.add(myTestSuite4);

function test_1e_setup() {
  this.assert(true);
}
function test_1e() {
  this.assert(true);
}
function test_1e_teardown() {
  this.assert(true);
}
var myTestSuite5 = new Casper.UnitTest.TestSuite("Casper Setup/Teardown TestSuite");
myTestSuite5.add(new Casper.UnitTest.TestCase("Test Case 1e assert true", test_1e, test_1e_setup, test_1e_teardown));
Casper.UnitTest.testRunner.add(myTestSuite5);

} catch(e) {
    var CasperLog = Casper.Logging.getLogger("Casper::global");
    CasperLog.exception(e);
}

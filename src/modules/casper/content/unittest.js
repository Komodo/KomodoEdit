/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 * 
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 * 
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 * 
 * The Original Code is Komodo code.
 * 
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
 * ActiveState Software Inc. All Rights Reserved.
 * 
 * Contributor(s):
 *   ActiveState Software Inc
 * 
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 * 
 * ***** END LICENSE BLOCK ***** */

/**
 * Casper is a UI unit testing module to be used with Mozilla technologies.
 * Tests can be run through either a XUL UI widget or through the command
 * line using a "-casper path/to/test/files".
 */

try {
include('chrome://jslib/content/io/dir.js');
include('chrome://jslib/content/io/fileUtils.js');

if (typeof(Casper) == 'undefined') {
    var Casper = {};
}

Casper.UnitTest = {
    log: Casper.Logging.getLogger('Casper::UnitTest'),
  
    testRunner: null,
    testDir: "chrome://casper/content/test/",
    
    PASS: 1,
    FAIL: 2,
    BREAK: 3,
    UNKNOWN: 4,
    ASSERT: 5,
    ASSERTTRUE: 6,
    ASSERTFALSE: 7,
    ASSERTEQUALS: 8,
    ASSERTNOTEQUALS: 9,
    ASSERTNULL: 10,
    ASSERTNOTNULL: 11,
    ASSERTUNDEFINED: 12,
    ASSERTNOTUNDEFINED: 13,
    ASSERTNAN: 14,
    ASSERTNOTNAN: 15,
    ASSERTREGEXP: 16,
    ASSERTNOTREGEXP: 17,
    ASSERTTYPEOF: 18,
    ASSERTNOTTYPEOF: 19,
    TESTSUITE: 20,
    TESTCASE: 21
}

Casper.UnitTest.AssertException = function(type, msg) {
    this.type = type;
    this.name = this.getTypeText(type);
    this.message = msg;
    this.stack = this.getExceptionStack();
    //this.stack = new String(this.stack); // have to do this to save the stack
    //Casper.UnitTest.log.setLevel(Casper.Logging.DEBUG);
    //Casper.UnitTest.log.exception(this);
}
Casper.UnitTest.AssertException.prototype = {
  getTypeText: function(type)
    {
        switch (type)
        {
        case Casper.UnitTest.ASSERT:
            return("Assert");
        case Casper.UnitTest.ASSERTTRUE:
            return("Assert True");
        case Casper.UnitTest.ASSERTFALSE:
            return("Assert False");
        case Casper.UnitTest.ASSERTEQUALS:
            return("Assert Equals");
        case Casper.UnitTest.ASSERTNOTEQUALS:
            return("Assert Not Equals");
        case Casper.UnitTest.ASSERTNULL:
            return("Assert Null");
        case Casper.UnitTest.ASSERTNOTNULL:
            return("Assert Not Null");
        case Casper.UnitTest.ASSERTUNDEFINED:
            return("Assert Undefined");
        case Casper.UnitTest.ASSERTNOTUNDEFINED:
            return("Assert Not Undefined");
        case Casper.UnitTest.ASSERTNAN:
            return("Assert NaN");
        case Casper.UnitTest.ASSERTNOTNAN:
            return("Assert Not NaN");
        case Casper.UnitTest.ASSERTREGEXP:
            return("Assert RegExp");
        case Casper.UnitTest.ASSERTNOTREGEXP:
            return("Assert Not RegExp");
        case Casper.UnitTest.ASSERTTYPEOF:
            return("Assert TypeOf");
        case Casper.UnitTest.ASSERTNOTTYPEOF:
            return("Assert Not TypeOf");
        case Casper.UnitTest.TESTSUITE:
            return("Test Suite");
        case Casper.UnitTest.TESTCASE:
            return("Test Case");
        }
        return("UNKNOWN TEST TYPE");
    },
    getExceptionStack: function()
    {
    
        if (!((typeof Components == "object") &&
              (typeof Components.classes == "object")))
            return "No stack trace available.";

        var frame = Components.stack.caller.caller;
        var str = "<top>";
    
        while (frame)
        {
            var name = frame.name ? frame.name : "[anonymous]";
            str += "\n" + name + "@" + frame.filename +':' + frame.lineNumber;
            frame = frame.caller;
        }
    
        return str+"\n";
    
    }
}

Casper.UnitTest.TestSuite = function(name, tests) {
    this._log = null;
    this.url = null;  // Url that the test suite was loaded from
    this.type = Casper.UnitTest.TESTSUITE;
    this.name = name;
    this._result = null;
    this.index = 0;
    if (typeof(tests) == 'array') {
      // this better be an array of TestCase classes
      this.testCase = tests;
    } else {
      this.testCase = new Array();
    }
}

Casper.UnitTest.TestSuite.prototype = {
    get log() {
        if (!this._log) {
            this._log = Casper.Logging.getLogger('Casper::UnitTest::TestSuite');
            //this._log.setLevel(Casper.Logging.DEBUG);
        }
        return this._log;
    },

    get result() {
        if (!this._result) {
            this._result = new Casper.UnitTest.TestResult();
        }
        this._result.passes();
        var testcase;
        for (var i=0; i<this.testCase.length; i++) {
            testcase = this.testCase[i];
            if (testcase.wasRun) {
                if (testcase._result.failed()) {
                    this._result.fails("Test Suite Failed");
                    break;
                }
                if (testcase._result.broke()) {
                    this._result.fails("Test Suite Exception");
                    break;
                }
            }
        }
        return this._result;
    },

    get testChild() {
        return this.testCase;
    },
    
    add: function(testCase)
    {
        this.testCase.push(testCase);
    },
      
    setup: function() {
        // subclasses can safely override setup
    },
      
    run: function()
    {
        this.log.debug("run()");
        this.setup();
        this.index = 0;
        window.setTimeout(function (me) { me.execute(); }, 0, this);
    },
    
    execute: function()
    {
        this.log.debug("execute()");
        var self = this;
        var test = this.testCase[this.index++];
        test.reset();
        this.log.debug("Suite:: executing testcase '" + test.name + "'");
        if (Casper.UnitTest.testRunner.shouldRunTestcase(test.name)) {
            test.complete = function() {
                self.next();
            }
            test.run();
        } else {
            self.next();
        }
    },
    
    next: function()
    {
        if (this.index >= this.testCase.length) {
            this.tearDown();
            this.close();
            return;
        }
        window.setTimeout(function (me) { me.execute(); }, 0, this);
    },
    tearDown: function() {
        // subclasses can safely override teardown
    },
    close: function() {
        // subclasses cannot override close, this is changed by test runners
    }
}

Casper.UnitTest.TestCase = function(name, testFunction, setupFn, tearDownFn) {
    this._log = null;
    this.type = Casper.UnitTest.TESTCASE;
    this.name = name;
    this.testFunction = null;
    this._result = null;
    this.complete = null;
    this._tearDown = null;
    this._setup = null;
    this._testChild = [];

    if (typeof(testFunction) != "undefined") {
        this.testFunction = testFunction;
        if (typeof(testFunction) == 'string') {
          this.testFunction = this[fn];
        } else
        if (typeof(testFunction) == 'function') {
          this.testFunction = testFunction;
        }
    } else {
        if (name in this) {
          this.testFunction = this[name];
        }
    }
    if (typeof(setupFn) != "undefined") {
      this._setup = setupFn;
    }
    if (typeof(tearDownFn) != "undefined") {
      this._tearDown = tearDownFn;
    }

    // Synonyms for assertion methods
    this.assertEqual = this.assertEquals = this.failUnlessEqual;
    this.assertNotEqual = this.assertNotEquals = this.failIfEqual;
    this.assertAlmostEqual = this.assertAlmostEquals = this.failUnlessAlmostEqual;
    this.assertNotAlmostEqual = this.assertNotAlmostEquals = this.failIfAlmostEqual;
    this.assertRaises = this.failUnlessRaises;
    this.assert = this.failUnless;
    this.assertTrue = this.failUnless;
    this.assertFalse = this.failIf;
    
    //this.log.setLevel(Casper.Logging.DEBUG);
}
Casper.UnitTest.TestCase.prototype = {
    get log() {
        if (!this._log) {
            this._log = Casper.Logging.getLogger('Casper::UnitTest::TestCase');
            //this._log.setLevel(Casper.Logging.DEBUG);
        }
        return this._log;
    },
    get wasRun() {
        return this._result != null;
    },
    get result() {
        if (!this._result)
            this._result = new Casper.UnitTest.TestResult();
        return this._result;
    },
    get testChild() {
        return this._testChild;
    },
    reset: function()
    {
        this._result = null;
    },
    
    setup: function()
    {
        if (this._setup)
            this._setup();
    },
    tearDown: function()
    {
        if (this._tearDown)
            this._tearDown();
    },
    run: function()
    {
        try {
            try {
                this.setup();
                this.testFunction();
                this.tearDown();
                this.result.passes();
            } catch(ex if ex instanceof Casper.UnitTest.AssertException) {
                this.result.fails(ex.message, ex);
            } catch(ex) {
                this.result.breaks(ex);
            }
        } finally {
            if (this.complete) this.complete();
        }
    },

    fail: function(msg)
    {
        //Fail immediately, with the given message.
        if (typeof(msg) == 'undefined') msg = "Unknown Failure";
        throw new Casper.UnitTest.AssertException(Casper.UnitTest.ASSERT, msg);
    },
    failIf: function(expr, msg)
    {
        //Fail the test if the expression is true.
        if (expr) {
            if (typeof(msg) == 'undefined') msg = "failIf: "+expr+" != true";
            throw new Casper.UnitTest.AssertException(Casper.UnitTest.ASSERTFALSE, msg);
        }
    },
    failUnless: function(expr, msg)
    {
        //Fail the test unless the expression is true.
        if (!expr) {
            if (typeof(msg) == 'undefined') msg = "failUnless: "+expr+" != false";
            throw new Casper.UnitTest.AssertException(Casper.UnitTest.ASSERTTRUE, msg);
        }
    },
    failUnlessRaises: function(excClass, callableObj, args, msg)
    {
        /*
           Fail unless an exception of class excClass is thrown
           by callableObj when invoked with arguments args and keyword
           arguments kwargs. If a different type of exception is
           thrown, it will not be caught, and the test case will be
           deemed to have suffered an error, exactly as for an
           unexpected exception.
        */
        try {
            callableObj.apply(this, args);
        } catch(e if e instanceof excClass) {
            // test passed
            //this.log.debug(msg+": OK\n");
            return;
        }
        if (typeof(msg) == 'undefined') msg = "Exception was not raised";
        throw new Casper.UnitTest.AssertException(Casper.UnitTest.ASSERT, msg);
    },
    failUnlessEqual: function(first, second, msg)
    {
        /*
           Fail if the two objects are unequal as determined by the '=='
           operator.
        */
        if (!this._isValueEqual(first, second)) {
            if (typeof(msg) == 'undefined') msg = "failUnlessEqual: "+ first +" != "+ second;
            throw new Casper.UnitTest.AssertException(Casper.UnitTest.ASSERTEQUALS, msg);
        }
    },
    failIfEqual: function(first, second, msg)
    {
        /*
           Fail if the two objects are equal as determined by the '=='
           operator.
        */
        if (this._isValueEqual(first, second)) {
            if (typeof(msg) == 'undefined') msg = "failIfEqual: "+ first +" == "+ second;
            throw new Casper.UnitTest.AssertException(Casper.UnitTest.ASSERTNOTEQUALS, msg);
        }
    },
    
    _isValueEqual: function(v1, v2) {
        if (typeof(v1) != typeof(v2))
            return false;
        if (v1 != v2 && typeof(v1) == 'object')
            return this._isObjectEqual(v1, v2);
        return v1 == v2;
    },
    
    _isObjectEqual: function(ar1, ar2) {
        if (ar1.length != ar2.length) return false;
        for (var i in ar1) {
            if (!this._isValueEqual(ar1[i], ar2[i])) return false;
        }
        return true;
    },

    
    _round: function(value, digits)
    {
        if (digits < 1)
            return Math.round(value);
        
        var p = Math.pow(10, digits);
        return Math.round(value*p)/p;
    },
    failUnlessAlmostEqual: function(first, second, places, msg)
    {
        /*
           Fail if the two objects are unequal as determined by their
           difference rounded to the given number of decimal places
           (default 7) and comparing to zero.

           Note that decimal places (from zero) are usually not the same
           as significant digits (measured from the most signficant digit).
        */
        if (typeof(places) == 'undefined') places = 7;
        if (this._round(second-first, places) != 0) {
            if (typeof(msg) == 'undefined') msg = this._round(second-first, places) +" != 0";
            throw new Casper.UnitTest.AssertException(Casper.UnitTest.ASSERT, msg );
        }
    },
    failIfAlmostEqual: function(first, second, places, msg)
    {
        /*
           Fail if the two objects are equal as determined by their
           difference rounded to the given number of decimal places
           (default 7) and comparing to zero.

           Note that decimal places (from zero) are usually not the same
           as significant digits (measured from the most signficant digit).
        */
        if (typeof(places) == 'undefined') places = 7;
        if (this._round(second-first, places) == 0) {
            if (typeof(msg) == 'undefined') msg = this._round(second-first, places) +" == 0";
            throw new Casper.UnitTest.AssertException(Casper.UnitTest.ASSERT, msg);
        }
    },

    assertNull: function(value, msg)
    {
        if (value != null) {
            if (typeof(msg) == 'undefined') msg = "assertNull: "+ value +" != null";
            throw new Casper.UnitTest.AssertException(Casper.UnitTest.ASSERTNULL, msg);
        }
    },
    
    assertNotNull: function(value, msg)
    {
        if (value == null) {
            if (typeof(msg) == 'undefined') msg = "assertNull: "+ value +" == null";
            throw new Casper.UnitTest.AssertException(Casper.UnitTest.ASSERTNOTNULL, msg);
        }
    },
    
    assertUndefined: function(value, msg)
    {
        if (typeof(value) != 'undefined') {
            if (typeof(msg) == 'undefined') msg = "Value is not Undefined";
            throw new Casper.UnitTest.AssertException(Casper.UnitTest.ASSERTUNDEFINED, msg);
        }
    },
    
    assertNotUndefined: function(value, msg)
    {
        if (typeof(value) == 'undefined') {
            if (typeof(msg) == 'undefined') msg = "Value is Undefined";
            throw new Casper.UnitTest.AssertException(Casper.UnitTest.ASSERTNOTUNDEFINED, msg);
        }
    },
    
    
    assertNaN: function(value, msg)
    {
        if (!isNaN(value)) {
            if (typeof(msg) == 'undefined') msg = "Value is not NaN";
            throw new Casper.UnitTest.AssertException(Casper.UnitTest.ASSERTNAN, msg);
        }
    },
    
    assertNotNaN: function(value, msg)
    {
        if (isNaN(value)) {
            if (typeof(msg) == 'undefined') msg = "Value is NaN";
            throw new Casper.UnitTest.AssertException(Casper.UnitTest.ASSERTNOTNAN, msg);
        }
    },

    assertRegExp: function(regExp, value, msg)
    {
        if (!value.match(regExp)) {
            if (typeof(msg) == 'undefined') msg = "Value does not match "+regExp;
            throw new Casper.UnitTest.AssertException(Casper.UnitTest.ASSERTREGEXP, msg);
        }
    },
    
    assertNotRegExp: function(regExp, value, msg)
    {
        if (value.match(regExp)) {
            if (typeof(msg) == 'undefined') msg = "Value matches "+regExp;
            throw new Casper.UnitTest.AssertException(Casper.UnitTest.ASSERTNOTREGEXP, msg);
        }
    },

    assertTypeOf: function(type, value, msg)
    {
        if (typeof(value) != type) {
            if (typeof(msg) == 'undefined') msg = typeof(value) +" != "+type;
            throw new Casper.UnitTest.AssertException(Casper.UnitTest.ASSERTTYPEOF, msg);
        }
    },
    
    assertNotTypeOf: function(type, value, msg)
    {
        if (typeof(value) == type) {
            if (typeof(msg) == 'undefined') msg = typeof(value) +" == "+type;
            throw new Casper.UnitTest.AssertException(Casper.UnitTest.ASSERTNOTTYPEOF, msg);
        }
    }
}



/**
 * TestCaseAsync
 * if you need to handle async events then subclass this
 */
Casper.UnitTest.TestCaseAsync = function(name, testFunction, setupFn, tearDownFn) {
    Casper.UnitTest.TestCase.apply(this, [name, testFunction, setupFn, tearDownFn]);
}
Casper.UnitTest.TestCaseAsync.prototype = new Casper.UnitTest.TestCase();
Casper.UnitTest.TestCaseAsync.constructor = Casper.UnitTest.TestCaseAsync;
Casper.UnitTest.TestCaseAsync.prototype.run = function()
{
      try {
          this.setup();
          this.testFunction();
          // testFunction does callback to set success
      } catch(ex if ex instanceof Casper.UnitTest.AssertException) {
          this.result.fails(ex.message, ex);
          this.testComplete();
          return;
      } catch(ex) {
          this.result.breaks(ex);
          this.testComplete();
          return;
      }
}
Casper.UnitTest.TestCaseAsync.prototype.testComplete = function()
{
    try {
        try {
            this.tearDown();
        } catch(ex if ex instanceof Casper.UnitTest.AssertException) {
            this.result.fails(ex.message, ex);
        } catch(ex) {
            this.result.breaks(ex);
        }
    } finally {
        if (this.complete) this.complete();
    }
}

/**
 * TestCaseSerialClass
 * if you want a test case class that has a setup/teardown that happens only
 * once, subclass this.
 */
Casper.UnitTest.TestCaseSerialClass = function(name, testFunction, setupFn, tearDownFn) {
    Casper.UnitTest.TestCase.apply(this, [name, testFunction, setupFn, tearDownFn]);

    // make test objects for each test function
    for (var i in this) {
        if (i.match(/^test_/)) {
            var theTest = new Object();
            theTest.result = new Casper.UnitTest.TestResult();
            theTest.name = i;
            theTest.testChild = [];
            theTest.wasRun = false;
            this._testChild.push(theTest);
        }
    }
}
Casper.UnitTest.TestCaseSerialClass.prototype = new Casper.UnitTest.TestCase();
Casper.UnitTest.TestCaseSerialClass.constructor = Casper.UnitTest.TestCaseSerialClass;

Casper.UnitTest.TestCaseSerialClass.prototype.run = function()
{
    try {
        try {
            this.result.passes(); // pass by default
            this.setup();
            try {
                for (var t in this._testChild) {
                    this.runOne(this._testChild[t]);
                }
            } finally {
                this.tearDown();
            }
        } catch(ex if ex instanceof Casper.UnitTest.AssertException) {
            this.result.fails(ex.message, ex);
        } catch(ex) {
            this.result.breaks(ex);
            //this.log.exception(ex);
        }
    } finally {
        if (this.complete) this.complete();
    }
}

Casper.UnitTest.TestCaseSerialClass.prototype.runOne = function(theTest)
{
    try {
        this[theTest.name]();
        theTest.result.passes();
    } catch(ex if ex instanceof Casper.UnitTest.AssertException) {
        theTest.result.fails(ex.message, ex);
        this.result.fails(ex.message, ex);
    } catch(ex) {
        theTest.result.breaks(ex);
        this.result.breaks(ex);
    } finally {
        theTest.wasRun = true;
    }
}

Casper.UnitTest.TestCaseSerialClassAsync = function(name, testFunction, setupFn, tearDownFn) {
    Casper.UnitTest.TestCaseAsync.apply(this, [name, testFunction, setupFn, tearDownFn]);
    this.currentTest = null;
    // make test objects for each test function
    var theTest;
    for (var i in this) {
        if (i.match(/^test_/)) {
            theTest = new Object();
            theTest.asyncComplete = false;
        } else if (i.match(/^testAsync_/)) {
            theTest = new Object();
            theTest.asyncComplete = true;
        } else {
            continue;  // Not a test
        }
        theTest.name = i;
        theTest.wasRun = false;
        theTest.result = new Casper.UnitTest.TestResult();
        theTest.testChild = [];
        this._testChild.push(theTest);
    }
}
Casper.UnitTest.TestCaseSerialClassAsync.prototype = new Casper.UnitTest.TestCaseAsync();
Casper.UnitTest.TestCaseSerialClassAsync.constructor = Casper.UnitTest.TestCaseSerialClassAsync;

Casper.UnitTest.TestCaseSerialClassAsync.prototype.run = function()
{
    try {
        this.result.passes(); // pass by default
        this._testIndex = 0;
        this.setup();
        this.runNext();
    } catch(ex if ex instanceof Casper.UnitTest.AssertException) {
        this.result.fails(ex.message, ex);
        this.testComplete();
    } catch(ex) {
        this.result.breaks(ex);
        this.testComplete();
    }
}

Casper.UnitTest.TestCaseSerialClassAsync.prototype.runOne = function()
{
    this.currentTest = this._testChild[this._testIndex++];
    if (Casper.UnitTest.testRunner.shouldRunTestchild(this.name, this.currentTest.name)) {
        try {
            // Pass the test by default, this allows the called function to be
            // able to set the test results itself.
            this.currentTest.result.passes();
            this[this.currentTest.name]();
        } catch(ex if ex instanceof Casper.UnitTest.AssertException) {
            this.currentTest.result.fails(ex.message, ex);
            this.result.fails(ex.message, ex);
        } catch(ex) {
            this.currentTest.result.breaks(ex);
            this.result.breaks(ex.message, ex);
            //this.log.exception(ex);
        } finally {
            this.currentTest.wasRun = true;
        }
    }
    if (!this.currentTest.asyncComplete ||
        (this.currentTest.result.type != Casper.UnitTest.PASS)) {
        this.runNext();
    }
}

Casper.UnitTest.TestCaseSerialClassAsync.prototype.runNext = function()
{
    try {
        if (this._testIndex >= this._testChild.length) {
            this.testComplete();
            return;
        }
        window.setTimeout(function(me) { me.runOne(); }, 0, this);
    } catch(ex) {
        this.result.breaks(ex);
        //this.log.exception(ex);
        this.testComplete();
    }
}

Casper.UnitTest.TestResult = function(name)
{
    this.type = Casper.UnitTest.UNKNOWN;
    this.name = "UNKNOWN";
    this.message = "";
    this.detail = null;
    this.fileName = null;
    this.lineNumber = null;
}
Casper.UnitTest.TestResult.prototype = {
    passed: function() {
      return this.type == Casper.UnitTest.PASS;
    },
    failed: function() {
      return this.type == Casper.UnitTest.FAIL;
    },
    broke: function() {
      return this.type == Casper.UnitTest.BREAK;
    },
    passes: function()
    {
        this.type = Casper.UnitTest.PASS;
        this.name = "PASS";
        this.message = "ok";
    },
      
    fails: function(message, ex)
    {
        this.type = Casper.UnitTest.FAIL;
        this.name = "FAILURE";
        this.message = message;
        if (typeof(ex) == 'undefined') return;
        this.fileName = ex.fileName;
        this.lineNumber = ex.lineNumber;
        //dump(ex.stack);
        this.detail = ex.stack.split(/\(.*?\)@/).join('\n');
        //dump(this.detail);
    },
      
    breaks: function(ex)
    {
        this.type = Casper.UnitTest.BREAK;
        this.name = "BREAK";
        this.message = new String(ex);
        if (typeof(ex) == 'undefined') return;
        this.fileName = ex.fileName;
        this.lineNumber = ex.lineNumber;
        //dump(ex.stack);
        //this.detail = ex.stack.split(/\(.*?\)@/).join('\n');
        //dump(this.detail);
        this.detail = ex.stack;
    },
    
    statusName: function()
    {
        switch (this.type)
        {
        case Casper.UnitTest.PASS:
            return "testPasses";
        case Casper.UnitTest.FAIL:
            return "testFails";
        case Casper.UnitTest.BREAK:
            return "testBreaks";
        }
        return "testUnknown";
    }
}


 
Casper.UnitTest.getTestCasesFromClass = function(suite, testCaseClass)
{
    for (var i in testCaseClass.prototype) {
        if (i.match(/^test_/)) {
            suite.add(new testCaseClass(i));
        }
    }
}

Casper.UnitTest.MakeSuite = function(name, testCaseClass)
{
    var suite = new Casper.UnitTest.TestSuite(name);
    Casper.UnitTest.getTestCasesFromClass(suite, testCaseClass);
    return suite;
}

Casper.UnitTest.TextTestRunner = function (params, logfile)
{
    this.log = Casper.Logging.getLogger('Casper::UnitTest::TextTestRunner');
    //this.log.setLevel(Casper.Logging.DEBUG);
    this.log.debug("Initializing TextTestRunner for: " + params);
    this.reset();
    this.params = params;
    this.logfile = logfile;
    this._test_settings = null; // Settings for how and what to run
    this.execOnComplete = null;
}
    
Casper.UnitTest.TextTestRunner.prototype.reset = function(testSuite)
{
    this.testSuite = [];
    this._testObject = [];
    this.clearResults();
    this.suiteIndex = 0;
    this.currentSuite = null;
    this.currentUrl = null;
}

Casper.UnitTest.TextTestRunner.prototype.add = function(testSuite)
{
    testSuite.url = this.currentUrl;
    this.testSuite.push(testSuite);
    this.log.info("Suite '" + testSuite.name + "' added.");
}

Casper.UnitTest.TextTestRunner.prototype.clearResults = function()
{
    this.totalTestSuites = 0;
    this.totalTestCases = 0;
    this.totalTests = 0;
    this.suiteIndex = 0;
    this.totalSuccess = 0;
    this.totalFail = 0;
    this.totalBreak = 0;
}
    
Casper.UnitTest.TextTestRunner.prototype.launch = function()
{
    Casper.UnitTest.testRunner = this;
    this.run();
}

Casper.UnitTest.TextTestRunner.prototype.loadTests = function() {
    var argument;
    try {
        // Parse the parameters passed in
        this._test_settings = new Casper.UnitTest.TestSuiteSettings();
        for (var i=0; i < this.params.length; i++) {
            argument = this.params[i];
            this.log.debug("loadTests:: argument: " + argument);
            // We can expect different formats for the given test location
            // - A directory              "/test/components/"
            // - A javascript filename    "/test/components/test_acomponent.js"
            // - A javascript filename and a test case       "/test.js#mytestcase"
            // - A javascript filename, test case and child  "/test.js#mytestcase.test1"
            Casper.UnitTest.updateFilesAndSettings(this._test_settings, argument);
        }
        this.log.info("loadTests::   url settings");
        for (url in this._test_settings.testcase_names_for_url) {
            this.log.info("loadTests::   url[" + url + "]: " + this._test_settings.testcase_names_for_url[url]);
        }

        // Load the necessary urls
        var count = 0;
        var url;
        for (var i = 0; i < this._test_settings.testfile_urls.length; i++) {
            url = this._test_settings.testfile_urls[i];
            this.log.info("loadTests:: loading... "+url+"\n");
            try {
                this.currentUrl = url;
                include(url);
                ++count;
            } catch(e) {
              // either cannot load, or already loaded
            }
        }
    } catch (ex) {
        this.log.exception(ex);
    }

    if (count == 0)
        log.warn("loadTests:: did not load any tests!");
}

/**
 * Used to check if the given test case should be run.
 * @param {string} testcase_name  Name of the test case
 */
Casper.UnitTest.TextTestRunner.prototype.shouldRunTestcase = function(testcase_name) {
    return this._test_settings.shouldRunTestcase(this.currentSuite.url, testcase_name);
}

/**
 * Used to check if the given test child should be run.
 * @param {string} testcase_name  Name of the test case
 * @param {string} testchild_name  Name of the test child inside the testcase
 */
Casper.UnitTest.TextTestRunner.prototype.shouldRunTestchild = function(testcase_name, testchild_name) {
    return this._test_settings.shouldRunTestchild(this.currentSuite.url, testcase_name, testchild_name);
}

Casper.UnitTest.TextTestRunner.prototype.run = function()
{
    this.log.debug("run()");
    this.reset();
    this.loadTests();
    this.next();
}

Casper.UnitTest.TextTestRunner.prototype.runOneSuite = function()
{
    try {
        if (this.suiteIndex < this.testSuite.length) {
            var self = this;
            var suite = this.testSuite[this.suiteIndex++];
            this.currentSuite = suite;
            this.log.debug("runOneSuite:: running " + suite.name);
            suite.close = function() {
                self.showSuiteResults(suite);
                self.next();
            }
            suite.run();
        } else {
          // we're done
            this.finishResults();
        }
      //this.showResults();
    } catch(e) {
        this.log.exception(e);
    }
}

Casper.UnitTest.TextTestRunner.prototype.next = function()
{
    this.log.debug("next()");
    window.setTimeout(function(me) { me.runOneSuite(); }, 0, this);
}

Casper.UnitTest.TextTestRunner.prototype.showSuiteResults = function(suite)
{
    try {
    this.totalTestSuites += 1;
    if (! this.logfile) {
        dump("Suite: "+suite.name+" Result: "+suite.result.message+"\n");
    }
    var testCases = suite.testChild;
    this.totalTestCases += testCases.length;

    for (var j=0; j < testCases.length; j++) {
        var testCase = testCases[j];
        if (!testCase.wasRun) {
            // Not the testcase we ran
            continue;
        }
        if (! this.logfile) {
            dump("Case: "+testCase.name+": "+testCase.result.message+"\n");
        }
        if (testCase.testChild.length > 0) {
            var tests = testCase.testChild;
            var testChild;
            for (var k=0; k < tests.length; k++) {
                testChild = tests[k];
                if (!testChild.wasRun) {
                    // Not the test child we ran
                    continue;
                }
                this.totalTests += 1;
                if (! this.logfile) {
                    dump("Test: "+testChild.name+": "+testChild.result.message+"\n");
                    if (!testChild.result.passed()) {
                       dump(testCase.result.detail+"\n");
                    }
                }
                this.totalSuccess += testChild.result.passed() ? 1:0;
                this.totalFail += testChild.result.failed() ? 1:0;
                this.totalBreak += testChild.result.broke() ? 1:0;
            }
        } else {
            if (!this.logfile && !testCase.result.passed()) {
                dump(testCase.result.detail+"\n");
            }
            this.totalTests += 1;
            this.totalSuccess += testCase.result.passed() ? 1:0;
            this.totalFail += testCase.result.failed() ? 1:0;
            this.totalBreak += testCase.result.broke() ? 1:0;
        }
    }
    if (! this.logfile) {
        dump("==============================================================\n");
    }
    } catch(e) {
        this.log.exception(e);
    }
}

Casper.UnitTest.TextTestRunner.prototype.escapeForJSON = function(data)
{
    data = data.replace('\\', '\\\\', "g");
    data = data.replace("\n", "\\n", "g");
    data = data.replace('"', '\\"', "g");
    return data;
}
/**
 * Save the test suite runtime information to a log file as JSON.
 * 
 * @param suite {Casper.UnitTest.TestSuite}  The test suite
 * @param {File} file  A file object that implements a write() method.
 * @param {boolean} isFirst Indicates if this is the first suite being
 *      logged.
 * @returns {int} The number of tests written.
 */
Casper.UnitTest.TextTestRunner.prototype.logSuiteResults = function(suite, file, isFirst)
{
    var num_tests_written = 0;
    try {
    var _log_test_case = function(file, suite, testcase_name, testfunc_name,
                            passed, result, message, detail, isFirstTest,
                            escapeFn) {
        if (!isFirstTest) {
            file.write(',');
        }
        file.write('\n {\n');
        file.write('  "url": "'+escapeFn(suite.url)+'",\n');
        file.write('  "testcase": "'+escapeFn(testcase_name)+'",\n');
        if (testfunc_name != null) {
            file.write('  "testfunc": "'+escapeFn(testfunc_name)+'",\n');
        } else {
            file.write('  "testfunc": '+testfunc_name+',\n');
        }
        file.write('  "passed": '+passed+',\n');
        file.write('  "result": "'+escapeFn(result)+'",\n');
        if (message != null) {
            file.write('  "message": "'+escapeFn(message)+'",\n');
        } else {
            file.write('  "message": '+message+',\n');
        }
        if (detail != null) {
            file.write('  "detail": "'+escapeFn(detail)+'"\n');
        } else {
            file.write('  "detail": '+detail+'\n');
        }
        file.write(' }');
        num_tests_written += 1;
    }

    var testCases = suite.testChild;
    for (var j=0; j < testCases.length; j++) {
        var testCase = testCases[j];
        if (!testCase.wasRun) {
            // Not the testcase we ran
            continue;
        }
        if (testCase.testChild.length > 0) {
            var tests = testCase.testChild;
            var testChild;
            for (var k=0; k < tests.length; k++) {
                testChild = tests[k];
                if (!testChild.wasRun) {
                    // Not the test child we ran
                    continue;
                }
                _log_test_case(file, suite,
                               testCase.name,
                               testChild.name,
                               testChild.result.passed(),
                               testChild.result.name,
                               testChild.result.message,
                               testChild.result.detail,
                               isFirst,
                               this.escapeForJSON);
                isFirst = false;
            }
        } else {
            //XXX When does this happen?! Shouldn't be able to "run" a
            //    TestCase class instance without an actual test function
            //    (aka "testChild" here). --TM
            _log_test_case(file, suite,
                           testCase.name,
                           null,
                           testCase.result.passed(),
                           testCase.result.name,
                           testCase.result.message,
                           testCase.result.detail,
                           isFirst,
                           this.escapeForJSON);
            isFirst = false;
        }
    }
    } catch(e) {
        this.log.exception(e);
    }
    return num_tests_written;
}

Casper.UnitTest.TextTestRunner.prototype.finishResults = function()
{
    if (! this.logfile) {
        dump("Total Suites: "+this.totalTestSuites+"\n");
        dump("Total Cases: "+this.totalTestCases+"\n");
        dump("Total Tests: "+this.totalTests+"\n");
        dump("Total OK: "+this.totalSuccess+"\n");
        dump("Total FAIL: "+this.totalFail+"\n");
        dump("Total BREAK: "+this.totalBreak+"\n");
    }

    if (this.logfile) {
        /* Save results to a file */
        try {
            var file = new File(this.logfile);
            file.open("w");
            file.write("[");
            var isFirstTest = true;
            var wroteTests = false;
            for (var i=0; i<this.testSuite.length; i++) {
                wroteTests = this.logSuiteResults(this.testSuite[i], file, isFirstTest);
                if (isFirstTest && wroteTests) {
                    isFirstTest = false;
                }
            }
            file.write("\n]\n");
            file.close();
        } catch (ex) {
            this.log.exception(ex);
        }
    }

    if (this.execOnComplete)
        this.execOnComplete();
}
    
Casper.UnitTest.TextTestRunner.prototype.showResults = function()
{
    this.totalTestSuites = 0;
    this.totalTestCases = 0;

    for (var i=0; i<this.testSuite.length; i++)
    {
        this.showSuiteResults(this.testSuite[i]);
    }
  
    this.finishResults();
}
  
Casper.UnitTest.TextTestRunner.prototype.showDetails = function() {}

/**
 * Debugging function used to log all available test information.
 */
Casper.UnitTest.TextTestRunner.prototype.logAllTests = function() {
    var suite;
    var testCases;
    var testCase;
    var tests;
    var testChild;
    for (var i=0; i < this.testSuite.length; i++) {
        suite = this.testSuite[i];
        this.log.debug("suite: " + suite.name + "\n");
        testCases = suite.testChild;
        for (var j=0; j < testCases.length; j++) {
            testCase = testCases[j];
            this.log.debug("  testCase: " + testCase.name + "\n");
            tests = testCase.testChild;
            for (var k=0; k < tests.length; k++) {
                testChild = tests[k];
                this.log.debug("    testChild: " + testChild.name + "\n");
            }
        }
    }
}

/**
 * Debugging function used to output the specified tests that should be run.
 * This information comes from the arguments initially supplied to the runner.
 */
Casper.UnitTest.TextTestRunner.prototype.logTestsToRun = function() {
    var url;
    var testcase_names;
    var testcase_name;
    var testchild_names;
    var testchild_name;
    for (var i=0; i < this._test_settings.testfile_urls.length; i++) {
        url = this._test_settings.testfile_urls[i];
        this.log.debug(":: url[" + i + "]: " + url);
        if (url in this._test_settings.testcase_names_for_url) {
            testcase_names = this._test_settings.testcase_names_for_url[url];
            for (var j=0; j < testcase_names.length; j++) {
                testcase_name = testcase_names[j];
                this.log.debug("loadTests::   testcase: " + testcase_name);
                url += "#" + testcase_name;
                if (url in this._test_settings.testchild_names_for_testcaseurl) {
                    testchild_names = this._test_settings.testchild_names_for_testcaseurl[url];
                    for (var k=0; k < testchild_names.length; k++) {
                        testchild_name = testchild_names[k];
                        this.log.debug("loadTests::     testchild: " + testchild_name);
                    }
                }
            }
        }
    }
}

  
Casper.UnitTest.XULTestRunner = function(testDir)
{
    Casper.UnitTest.TextTestRunner.apply(this, [testDir]);
    this.log = Casper.Logging.getLogger('Casper::UnitTest::XULTestRunner');
    this._window = null;
}
Casper.UnitTest.XULTestRunner.prototype = new Casper.UnitTest.TextTestRunner();
Casper.UnitTest.XULTestRunner.constructor = Casper.UnitTest.XULTestRunner;

Casper.UnitTest.XULTestRunner.prototype.launch = function()
{
    //Creates a new window ready to launch tests
    Casper.UnitTest.testRunner = this; //Set the global variable to remember which TR to execute at the new window
    this._window = window.open("chrome://casper/content/testrunner.xul", "testRunnerWindow", "chrome, centerscreen, resizable, width=600, height=400");
}
    
Casper.UnitTest.XULTestRunner.prototype.clearResults = function()
{
    try {
        this.totalTestSuites = 0;
        this.totalTestCases = 0;
        this.totalTests = 0;
        this.totalSuccess = 0;
        this.totalFail = 0;
        this.totalSuccess = 0;
        this.totalBreak = 0;
        if (this._window) {
          this._window.document.getElementById("totalSuites").value = 0;
          this._window.document.getElementById("totalCases").value = 0;
          this._window.document.getElementById("totalTests").value = 0;
          this._window.document.getElementById("totalOK").value = 0;
          this._window.document.getElementById("totalFAIL").value = 0;
          this._window.document.getElementById("totalBREAK").value = 0;

          //Deletion of Results
          var treeResults = this._window.document.getElementById("treeResults");
          treeResults.currentIndex = -1;
          var treechildrenResults = this._window.document.getElementById("treechildrenResults");
          while(treechildrenResults.hasChildNodes())
            treechildrenResults.removeChild(treechildrenResults.firstChild);

        }
    } catch(e) {
        this.log.exception(e);
    }
}
    
Casper.UnitTest.XULTestRunner.prototype.showSuiteResults = function(suite)
{
    this.totalTestSuites += 1;
    var testCases = suite.testChild;
    this.totalTestCases += testCases.length;
    for (var j=0; j < testCases.length; j++) {
        var testCase = testCases[j];
        if (testCase.testChild.length > 0) {
            var tests = testCase.testChild;
            this.totalTests += tests.length;
            for (var k=0; k < tests.length; k++) {
                this.totalSuccess += tests[k].result.passed() ? 1:0;
                this.totalFail += tests[k].result.failed() ? 1:0;
                this.totalBreak += tests[k].result.broke() ? 1:0;
            }
        } else {
            this.totalTests += 1;
            this.totalSuccess += testCase.result.passed() ? 1:0;
            this.totalFail += testCase.result.failed() ? 1:0;
            this.totalBreak += testCase.result.broke() ? 1:0;
        }
    }
    
    this._window.document.getElementById("totalSuites").value = this.totalTestSuites;
    this._window.document.getElementById("totalCases").value = this.totalTestCases;
    this._window.document.getElementById("totalTests").value = this.totalTests;
    this._window.document.getElementById("totalOK").value = this.totalSuccess;
    this._window.document.getElementById("totalFAIL").value = this.totalFail;
    this._window.document.getElementById("totalBREAK").value = this.totalBreak;

    var treechildrenResults = this._window.document.getElementById("treechildrenResults");
    treechildrenResults.appendChild(this._getTreeitem(suite));
}
    
Casper.UnitTest.XULTestRunner.prototype.showResults = function()
{
    this.clearResults();
    for (var i=0; i<this.testSuite.length; i++)
    {
        this.showSuiteResults(this.testSuite[i]);
    }
}
    
Casper.UnitTest.XULTestRunner.prototype.finishResults = function() {
    if (this.execOnComplete)
        this.execOnComplete();
}
    
Casper.UnitTest.XULTestRunner.prototype._getTreeitem = function(testObject)
{
    //Returns a treeitem for the testObject
    var resultTreeitem = document.createElement("treeitem");
    try {
    resultTreeitem.setAttribute("testObjectId", this._testObject.length);
    this._testObject[this._testObject.length] = testObject;

    var resultTreerow = document.createElement("treerow");
    resultTreeitem.appendChild(resultTreerow);
    
    var resultNameTreecell = document.createElement("treecell");
    resultNameTreecell.setAttribute("label", testObject.name);
    resultTreerow.appendChild(resultNameTreecell);
    
    var resultResultTreecell = document.createElement("treecell");
    resultResultTreecell.setAttribute("label", testObject.result.name);
    
    //Set the style for the Result
    resultResultTreecell.setAttribute("properties", testObject.result.statusName());
    resultTreerow.appendChild(resultResultTreecell);
	
    //Create a treechildren if testObject has Childs
    if (testObject.testChild.length > 0)
    {
        resultTreeitem.setAttribute("container","true");
        resultTreeitem.setAttribute("open", false);
        
        var newTreechildren = document.createElement("treechildren");
        resultTreeitem.appendChild(newTreechildren);
        for(var i=0; i<testObject.testChild.length; i++)
	    newTreechildren.appendChild(this._getTreeitem(testObject.testChild[i]));
    }
    } catch(e) {
        this.log.exception(e);
    }
    
    return resultTreeitem;
}
      
Casper.UnitTest.XULTestRunner.prototype._setDescription = function(el, text) {
    while (el.hasChildNodes())
        el.removeChild(el.firstChild);

    if (text)  {
        var node = document.createTextNode(text);
        el.appendChild(node);
    }
}

Casper.UnitTest.XULTestRunner.prototype.showDetails = function()
{
    try {
    //Shows details for a testObject (this means testSuite, testCase or test)
    var treeResults = this._window.document.getElementById("treeResults");
    if (treeResults.currentIndex < 0) return;
    var testObject = this._testObject[treeResults.view.getItemAtIndex(treeResults.currentIndex).getAttribute("testObjectId")];
    
    var el = this._window.document.getElementById("labelDetailType");
    this._setDescription(el, testObject.result.name);

    el = this._window.document.getElementById("labelDetailNameComment");
    this._setDescription(el, testObject.name);

    el = this._window.document.getElementById("textboxDetailResult");
    el.value = testObject.result.message;
    
    el = this._window.document.getElementById("labelDetailBreakMessage");
    el.value = testObject.result.detail;
//    this._setDescription(el, testObject.result.detail);
    } catch(e) {
        this.log.exception(e);
    }
}



/**
 * Parse up given command line test names into a class object
 */
Casper.UnitTest.TestSuiteSettings = function() {
    this.isValid = true;
    this.path = null;
    this.fileInfo = null;
    this.testfile_urls = []; // Used for including
    this.testcase_names_for_url = {};  // Name of the specific testcases in the suite
    this.testchild_names_for_testcaseurl = {}; // Name of the specific tests in the testcase
}
/**
 * Parse up a command line argument
 * @param {FileUtils} fu  A jslib FileUtis object
 * @param {string} arg  Argument from the command line
 */
Casper.UnitTest.TestSuiteSettings.prototype.parseArgument = function(fu, arg) {
    var index = arg.lastIndexOf("#");
    if (index >= 0) {
        this.path = arg.substr(0, index);
        var url = fu.pathToURL(this.path);
        arg = arg.substr(index +1);
        index = arg.indexOf(".");
        if (index >= 0) {
            var testcase_name = arg.substr(0, index);
            var testchild_name = arg.substr(index + 1);
            var testcaseurl = url + "#" + testcase_name;
            if (testcaseurl in this.testchild_names_for_testcaseurl) {
                var testchild_names = this.testchild_names_for_testcaseurl[testcaseurl];
                if (testchild_names.indexOf(testchild_name) == -1) {
                    testchild_names.push(testchild_name);
                    //dump("Appending test child name: " + testchild_name + " for url: " + testcaseurl + "\n");
                }
            } else {
                this.testchild_names_for_testcaseurl[testcaseurl] = [testchild_name];
                //dump("Adding test child name: " + testchild_name + " for url: " + testcaseurl + "\n");
            }
        } else {
            testcase_name = arg;
        }
        if (url in this.testcase_names_for_url) {
            var testcase_names = this.testcase_names_for_url[url];
            if (testcase_names.indexOf(testcase_name) == -1) {
                testcase_names.push(testcase_name);
            }
        } else {
            this.testcase_names_for_url[url] = [testcase_name];
        }
    } else {
        this.path = arg;
    }
    this.fileInfo = new File(this.path);
    if (this.fileInfo.exists()) {
        this.isValid = true;
    }
}
Casper.UnitTest.TestSuiteSettings.prototype.addTestfileUrl = function(url) {
    if (this.testfile_urls.indexOf(url) == -1) {
        this.testfile_urls.push(url);
    }
}
Casper.UnitTest.TestSuiteSettings.prototype.shouldRunTestcase = function(url, testcase_name) {
    if (url in this.testcase_names_for_url) {
        var testcase_names = this.testcase_names_for_url[url];
        if (testcase_names.indexOf(testcase_name) >= 0) {
            // This testcase was set to be run
            return true;
        }
        // Not a testcase specified for this url
        return false;
    }
    // Nothing specified for this url, let it run
    return true;
}
Casper.UnitTest.TestSuiteSettings.prototype.shouldRunTestchild = function(url, testcase_name, testchild_name) {
    var testcaseurl = url + "#" + testcase_name;
    if (testcaseurl in this.testchild_names_for_testcaseurl) {
        var testchild_names = this.testchild_names_for_testcaseurl[testcaseurl];
        if (testchild_names.indexOf(testchild_name) >= 0) {
            // This testcase was set to be run
            return true;
        }
        // Not a testcase specified for this testcaseurl
        return false;
    }
    return this.shouldRunTestcase(url, testcase_name);
}

/**
 * Update the settings object with the specific test information provided.
 * @param settings {Casper.UnitTest.TestSuiteSettings}  Settings object to update
 * @param {string} uri  Test uri to parse
 */
Casper.UnitTest.updateFilesAndSettings = function(settings, uri) {
    //dump("getFilesAndSettings:: uri: " + uri + "\n");
    var fu = new FileUtils();

    var loadFilesForSettings = function(settings, fileInfo) {
        if (fileInfo.isDir()) {
            var dir = new Dir(settings.path);
            var list = dir.readDir();
            var file;
            for (var i=0; i < list.length; i++) {
                file = list[i];
                if (file.isDir()) {
                    loadFilesForSettings(settings, file);
                } else if (file.leaf.match(/^test_.*\.js$/i)) {
                    settings.addTestfileUrl(fu.pathToURL(file.path));
                }
            }
        } else if (fileInfo.isFile()) {
            settings.addTestfileUrl(fu.pathToURL(fileInfo.path));
        }
    }

    var path = uri;
    if (path.match(/^file:\/\//i)) {
        path = fu.urlToPath(uri);
    } else if (path.match(/^chrome:\/\//i)) {
        path = fu.chromeToPath(uri);
    }

    settings.parseArgument(fu, path);
    if (!settings.isValid) {
        log.error("testLoader path is invalid: ["+this.path+"]\n");
        return null;
    }

    loadFilesForSettings(settings, settings.fileInfo);
    return settings;
}

Casper.UnitTest.getFilesInDir = function(uri) {
    var fu = new FileUtils;
    var LoadFilesInDir = function(dir) {
        var count = 0;
        var list = dir.readDir();
        var files = [];
        for (var i = 0; i < list.length; i++) {
            var file = list[i];
            if(file.isDir())
                files = files.concat(LoadFilesInDir(file));
            else if(file.leaf.match(/^test_.*\.js$/i)) {
                files.push(fu.pathToURL(file.path));
            }
        }
        return files;
    }

    var path = uri;
    if (path.match(/^file:\/\//i)) {
        path = fu.urlToPath(uri);
    } else
    if (path.match(/^chrome:\/\//i)) {
        path = fu.chromeToPath(uri);
    }
    var dir = new Dir(path);
    if (!dir.isDir()) {
        log.error("testLoader has no valid path ["+path+"]\n");
        return 0;
    }
    return LoadFilesInDir(dir);
}

Casper.UnitTest.ForceQuit = function() {
  var appStartup = Components.classes["@mozilla.org/toolkit/app-startup;1"]
                             .getService(Components.interfaces.nsIAppStartup);
  appStartup.quit(appStartup.eForceQuit);
}

Casper.UnitTest.runTestsText = function(params, logfile, quitOnComplete)
{
    try {
        if (!params)
            params = [Casper.UnitTest.testDir];
        if (!logfile)
            logfile = null;
        Casper.UnitTest.testRunner = new Casper.UnitTest.TextTestRunner(params, logfile);
        if (quitOnComplete) {
            Casper.UnitTest.testRunner.execOnComplete = Casper.UnitTest.ForceQuit;
        }
        Casper.UnitTest.testRunner.launch();
    } catch(e) {
        this.log.exception(e);
    }
}
  
Casper.UnitTest.runTestsXUL = function(testDir)
{
    try {
        if (typeof(testDir) == 'undefined')
            testDir = Casper.UnitTest.testDir;
        if (testDir instanceof String) {
            testDir = new Array(testDir);
        }
        Casper.UnitTest.testRunner = new Casper.UnitTest.XULTestRunner(testDir);
        Casper.UnitTest.testRunner.launch();
    } catch(e) {
        this.log.exception(e);
    }
}
Casper.UnitTest.openRecorder = function()
{
    window.open('chrome://casper/content/recorder.xul', 'testRecorderWindow', 'chrome, centerscreen, resizable, width=600, height=400');
}

} catch(e) {
    var CasperLog = Casper.Logging.getLogger("Casper::global");
    CasperLog.exception(e);
}

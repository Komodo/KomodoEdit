try {

function test_%EVENT_TEST_CLASSNAME%(name) {
    Casper.UnitTest.TestCaseAsync.apply(this, [name]);

    this.eventList = %EVENT_LIST%;
}
test_%EVENT_TEST_CLASSNAME%.prototype = new Casper.UnitTest.TestCaseAsync();
test_%EVENT_TEST_CLASSNAME%.prototype.constructor = test_%EVENT_TEST_CLASSNAME%;
test_%EVENT_TEST_CLASSNAME%.prototype.setup = function() {
}
test_%EVENT_TEST_CLASSNAME%.prototype.tearDown = function() {
}
test_%EVENT_TEST_CLASSNAME%.prototype.test_events = function() {
    var self = this;
    var test = new Casper.Events.test(window);
    test.complete = function(e) {
        self.complete_async(e);
    };
    test.eventList = this.eventList;
    test.replay();
}
test_%EVENT_TEST_CLASSNAME%.prototype.complete_async = function(ex) {
    // assert the state of something
    try {
      if (ex) {
          this.result.fails(ex.message, ex);
      } else {
          // Add final assertions here
          this.result.passes();
      }
    } catch(ex if ex instanceof Casper.UnitTest.AssertException) {
        this.result.fails(ex.message, ex);
    } catch(ex) {
        this.result.breaks(ex);
    } finally {
      this.testComplete();
    }
}
// we *do not pass an instance* of the test class, they are created in MakeSuite
Casper.UnitTest.testRunner.add(Casper.UnitTest.MakeSuite("%EVENT_TEST_CLASSNAME%", test_%EVENT_TEST_CLASSNAME%));

} catch(e) {
    var CasperLog = Casper.Logging.getLogger("Casper::global");
    CasperLog.exception(e);
}


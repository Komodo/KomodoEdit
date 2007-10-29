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


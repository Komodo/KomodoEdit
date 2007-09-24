
// Created 2 classes named "test_keybindings_bindings", see:
//   http://bugs.activestate.com/show_bug.cgi?id=70324
function test_keybindings_bindings() {
    Casper.UnitTest.TestCaseSerialClass.apply(this, ["kkf bindings"]);
}
test_keybindings_bindings.prototype = new Casper.UnitTest.TestCaseSerialClass();
test_keybindings_bindings.prototype.constructor = test_keybindings_bindings;
test_keybindings_bindings.prototype.setup = function() {
    this._evalCommand = gKeybindingMgr.evalCommand;
    var self = this;
}

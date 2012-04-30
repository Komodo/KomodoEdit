var ns = {};
ns.keybindings = {};
var gKeyDownHandler = function () {
    ns.keybindings.manager.keyDownLabels = 1;
}
ns.keybindings.manager = new Manager();

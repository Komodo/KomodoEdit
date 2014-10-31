/*
 * This module only handles "cause and effect", it should not contain any
 * overly specific logic
 */

(function() {

    var commando,
        elem;

    this.init = function(_commando)
    {
        if ( ! _commando)
            _commando = require("./commando");

        commando = commando;
        elem = commando.elem;
    }

    this.onSearch = function()
    {
        _onKitt();
    }

    var _onKitt = function()
    {
        // You didn't see this, you were never here
        if (_onKitt.kitt)
        {
            elem("panel").removeClass("kitt");
            delete _onKitt.kitt
        }
        if (["kitt", "michael"].indexOf(elem('search').value()) !== -1)
        {
            var sound = Cc["@mozilla.org/sound;1"].createInstance(Ci.nsISound);
            sound.play(ioService.newURI('chrome://commando/content/loading.wav', null, null));
            elem("panel").addClass("kitt");
            _onKitt.kitt = true;
        }
    }

}).apply(module.exports);

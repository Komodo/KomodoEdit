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

}).apply(module.exports);

// Komodo's JavaScipt ciler would hang on this file - bug 85481.

( function Protagonist() {

    var SELECTOR = ".protagonist",
    WALK_SPEED = 8,

    instances = {},

    Protagonist = function( player ) {

        var sprite = $(SELECTOR),
        running = false,

        offset = function( x, y ) {
            var position = sprite.position();
            position.top += y;
            position.left += x;
            sprite.css( {
                top: position.top + "px",
                left: position.left + "px"
            } );
        };

        this.moveLeft = function() {
            offset( -1 * ( running ? WALK_SPEED * 2 : WALK_SPEED ) );
        };

        this.moveRight = function() {
            offset( running ? WALK_SPEED * 2 : WALK_SPEED );
        };

        this.isRunning = function( value ) {
            if( arguments.length > 0 ) {
                running = value;
            }
            return running;
        };

        this.jump = function() {};

    };

    this.Protagonist = {
        get: function( player ) {
            var protagonist = instances[player];
            if( !protagonist ) {
                instances[player] = new Protagonist( player );
            }
            return instances[player] || ( instances[player] = new Protagonist( player ) );
        }
    };

} )();


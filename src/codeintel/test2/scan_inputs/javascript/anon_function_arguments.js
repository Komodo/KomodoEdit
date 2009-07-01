YUI({
        modules: {
            ea_forms4: {
                path: "../js/ea_forms4.js",
                type: "js"
            }
        },
        filter: 'raw',
        base: "/yui3/"
    }
).use("base", "node", "io-form", "dump", "json-parse", "plugin",
    function(Y) {
        Y.use('ea_forms4',
            function(Y) {
                //initialize the page
                var init = function() {
                    //do things
                }
                var myMethod = function() {
                    //do things
                }
        
            });
    }
);

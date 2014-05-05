(function() {

    this.onSearch = function(query, subscope, done)
    {
        var results = [
            {
                id: "foo",
                name: "Foobar",

                description: "this is <b>foobar</b>!",
                icon: "moz-icon://tmp/",

                isScope: true
            },
            {
                id: "foo2",
                name: "Foobar2",

                description: "this is <b>foobar2</b>!",
                icon: "moz-icon://tmp/file.txt",
            },
            {
                id: "foo3",
                name: "Foobar3",

                description: "this is <b>foobar3</b>!",
                icon: "moz-icon://tmp/",
            }
        ];
        done(results);
    }

}).apply(module.exports);

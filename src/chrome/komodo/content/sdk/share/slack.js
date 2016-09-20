(function()
{
    const share = require("ko/share");
    const client_id="3108485669.77788960934";
    const scope="files:write:user";
    const w = require("ko/windows").getMain();
    var ajax = require("ko/ajax");
    var redirect_uri;
    var state = require('sdk/util/uuid').uuid().number.replace(/[[{?]|[}?]]*/g,"");
    var realm = "Slack Integration User Key";
    var team;
    
    this.load = function()
    {
        commands.register("slack", this.share.bind(this, undefined), {
            label: "Slack: Share Code on your slack"
        });

        share.register("slack", "Share Code on Slack");
        
        require("notify/notify").categories.register("slack",
        {
            label: "Slack Integration"
        });
    };
    
    this.authorize = function()
    {
        var authUrl = "https://slack.com/oauth/authorize?";
        var params = require("sdk/querystring").stringify(
        {
            client_id: client_id,
            scope: scope,
            state: state,
        });
        var reqStr = authUrl+params;
        ajax.get(reqStr,(code, respText) =>
        {
            // Notify instead of console.log
            console.log("code: "+code+"\nResponse: "+respText);
        });
    };

    function savekey(APIkey)
    {
        // delete any saved keys
        (function(){
            require("sdk/passwords").search({
                username: "slack",
                url: "http://www.example.com",
                onComplete: function (credentials) {
                    credentials.forEach(require("sdk/passwords").remove);
                }   
            });
        })();
        // Save the new key
        require("sdk/passwords").store({
            url: "http://www.example.com",
            username: "slack",
            password: APIkey,
            realm: realm
          });
    }
    
    /**
     * Get the saved Slack API key
     *
     * @argument {function} callback    What to do with the retrieved key
     *
     * The function that retrieves keys from storage is async so we can't just
     * return it
     */
    this.getKey = function(callback)
    {
        w.alert("not implemented" + callback);
    };
    
    this.share = function()
    {
        var view = require("ko/views").current().get();
        w.alert(view);
    };
   
}).apply(module.exports);
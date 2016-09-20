var ajax = require("ko/ajax");
var $ = require("ko/dom");
var scope="files:write:user"; //// identify,read,post',
var redirect_uri = "http://localhost:8001/slack/auth";
var client_id = "3108485669.77788960934";
var uuidGenerator = Components.classes["@mozilla.org/uuid-generator;1"]
                                .getService(Ci.nsIUUIDGenerator);

var state = uuidGenerator.generateUUID(); // geenerate 
var team;

function OnLoad()
{
    // populate json data
    var params = require("sdk/querystring").stringify(
    {
        client_id: client_id,
        scope: scope, 
        state: state,
        redirect_uri: redirect_uri,
    });
    console.log(params.split("&").join("\n"));
    var baseUrl = "https://slack.com/oauth/authorize?";
    var reqStr = baseUrl+params;
    console.log(reqStr);
    var browser = $("#slackauth_browser");
    browser.element().loadURI(reqStr);
    //ajax.get(reqStr,(code, respText) =>
    //{
    //    // Notify instead of console.log
    //    //console.log("code: "+code+"\nResponse: "+respText);
    //    browser.innerHT
    //});
}


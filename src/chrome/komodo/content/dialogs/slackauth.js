
var slackApp = {};

(function()
{
    const {classes: Cc, interfaces: Ci, utils: Cu} = Components;
    var $ = require("ko/dom");
    var $gBrowser = $("#slackauth_browser");
    var gBrowserWindows = $gBrowser.element().contentWindows;
    var slack = require("ko/share/slack");
    // Set load event for when each webpage loads so we can get key from komodo
    // auth server
    this.init = function()
    {
        //Add event listner to content load to get page and process it
        if($gBrowser) $gBrowser.element().addEventListener("DOMContentLoaded", this.onPageLoad, false);
        this.loadSlackAuthPage();
        window.sizeToContent();
    }
    this.getBrowserContent = function()
    {
        return gBrowserWindows;
    }
    this.getSlackAuthURI = function()
    {
        return "https://slack.com/oauth/authorize?";
    }
    this.getScope = function()
    {
        return "files:write:user,channels:read"; //// identify,read,post',
    }
    this.getRedirectUri = function()
    {
        return "http://komodo.activestate.com/slack/auth";
    }
    this.getClientId = function()
    {
        return "3108485669.77788960934";
    }
    /**
     * Used to authenticate requests came from Komodo
     */
    this.getState = function()
    {
        return require('sdk/util/uuid').uuid().number.replace(/[{}]/g,"");
    }
    // Process page and look for auth key returned from Komodo/slack/auth
    this.onPageLoad = function()
    {
        var keyDiv = document.getElementById("slackauth_browser").contentDocument.getElementById("key");
        var doneDiv = document.getElementById("slackauth_browser").contentDocument.getElementById("done");
        if(keyDiv)
        {
            console.log("key: " + keyDiv.innerHTML.trim());
            require("ko/share/slack").saveKey(keyDiv.innerHTML.trim());
        }
        doneDiv.addEventListener("animationend",function(){window.close();});
    }
    // Load slack auth page
    this.loadSlackAuthPage = function()
    {
        // populate json data
        var params = require("sdk/querystring").stringify(
        {
            client_id: this.getClientId(),
            scope: this.getScope(), 
            state: this.getState(),
            redirect_uri: this.getRedirectUri(),
        });
        var baseUrl = this.getSlackAuthURI();
        var reqStr = baseUrl + params;
        $gBrowser.element().loadURI(reqStr);
    }
}).apply(slackApp);

window.addEventListener("load", function load(event){
    window.removeEventListener("load", load, false); //remove listener, no longer needed
    slackApp.init();  
},false);

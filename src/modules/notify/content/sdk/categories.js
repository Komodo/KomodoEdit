var logging   = require("ko/logging");
var log       = logging.getLogger("notify-categories");

var categories = {

    register: function(key, opts)
    {
        opts.id = key;
        this._registered[key] = opts;
    },

    unregister: function(key)
    {
        delete this._registered[key];
    },

    get: function(key)
    {
        if ( ! key) return this._registered;
        return this._registered[key] || false;
    },

    _registered: {}

};

categories.register("autoComplete",
{
    label: "Auto Completions",
    opts:
    {
        duration: 3000,
        from: "editor"
    }
});

categories.register("autoUpdate",
{
    label: "Auto Update",
    opts:
    {
        icon: "koicon://ko-svg/chrome/icomoon/skin/notification2.svg",
        duration: 10000 // 10 seconds
    }
});

categories.register("linter", { label: "Linter Messages" });

categories.register("browser", { label: "Browser" });

categories.register("bookmark", { label: "Bookmarks" });

categories.register("editor", { label: "Editor" });

categories.register("workspace", { label: "Workspace" });

categories.register("commands", { label: "Commands" });

categories.register("remote", { label: "Remote (Servers)" });

categories.register("codeintel", { label: "CodeIntel" });

categories.register("codeintel-verbose", { label: "CodeIntel (Verbose)" });

categories.register("codeintel-event", { label: "CodeIntel (Event)" });

categories.register("toolbox", { label: "Toolbox" });

categories.register("tools", { label: "Tools" });

categories.register("formatting", { label: "Formatting" });

categories.register("keybindings", { label: "Keybindings" });

categories.register("viEmulation", { label: "Vi Emulation" });

categories.register("scc", { label: "Source Code Control" });

categories.register("projects", { label: "Projects" });

categories.register("history", { label: "History" });

categories.register("macros", { label: "Macro's" });

categories.register("customization", { label: "Customization" });

categories.register("mark", { label: "Transient Marks (emacs)" });

categories.register("debugger", { label: "Debugger" });

categories.register("searchReplace", { label: "Search / Replace" });

categories.register("unittest", { label: "Unit Testing" });

categories.register("lint", { label: "Linter", opts: {
    priority: "info",
    classlist: "lint",
    duration: 6000,
    icon: "koicon://ko-svg/chrome/icomoon/skin/cancel-circle2.svg"
} });

categories.register("refactoring", { label: "Refactoring" });

categories.register("publishing", { label: "Publishing" });

categories.register("places", { label: "Places" });

categories.register("fs", { label: "Filesystem" });

categories.register("dev", { label: "Development" });

categories.register("packages", { label: "Packages", opts: { duration: 5000, alwaysShow: true } });

categories.register("find", { label: "Find/Replace" });

categories.register("status-message", { label: "Status Message" });

categories.register("progress-message", { label: "Progress Message", opts: { duration: 10000 } });

module.exports = categories;

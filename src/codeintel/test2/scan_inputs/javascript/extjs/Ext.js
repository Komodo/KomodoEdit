Ext = {
    version : '3.0'
};

(function(){
    var isWindows = check(/windows|win32/);

    Ext.apply(Ext, {
        isWindows: isWindows
    });

})();

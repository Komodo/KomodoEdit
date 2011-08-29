function foo() {
    var infoSvc = Components.classes["@activestate.com/koInfoService;1"].
          getService(Components.interfaces.koIInfoService);
    // Ensure this doesn't create a global daysLeft variable.
    var daysLeft = infoSvc.daysUntilExpiration;
    if (daysLeft < 0) daysLeft = -daysLeft;
}

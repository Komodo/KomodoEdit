var obj = null; // window input/output

function SetWindowLocation()
{
   var gLocation = document.getElementById("location");
   if (gLocation)
   {
     window.screenX = Math.max(0, Math.min(window.opener.screenX + Number(gLocation.getAttribute("offsetX")),
                                           screen.availWidth - window.outerWidth));
     window.screenY = Math.max(0, Math.min(window.opener.screenY + Number(gLocation.getAttribute("offsetY")),
                                           screen.availHeight - window.outerHeight));
  }
}

function SaveWindowLocation()
{
   var gLocation = document.getElementById("location");
   if (gLocation)
   {
     var newOffsetX = window.screenX - window.opener.screenX;
     var newOffsetY = window.screenY - window.opener.screenY;
     gLocation.setAttribute("offsetX", window.screenX - window.opener.screenX);
     gLocation.setAttribute("offsetY", window.screenY - window.opener.screenY);
   }
}

/* General startup routine for preferences dialog.
 *  Place all necessary modifications to pref tree here.
 */
function Startup()
{
    var name = document.getElementById("VarName");
    var value = document.getElementById("VarValue");
    document.getElementById("VarPaths").init();
    // The following selects the default selection (see preftree.xul for the
    // ids of the treeitems to choose from) if an argument is passed in,
    // otherwise loads it from a preference.

    if (window.arguments && window.arguments[0] != null) {
        obj = window.arguments[0];
        name.setAttribute("value", obj.name);
        value.setAttribute("value", obj.value);
        if (obj.name == "") {
            name.select();
        } else {
            value.select();
        }
    }
    obj.res = "cancel";  // default response

    SetWindowLocation();
}

function doUnLoad()
{
    SaveWindowLocation();
}

function doOk()
{
    try {
        window.arguments[0].name = document.getElementById("VarName").value;
        var deck = document.getElementById("VarDeck");
        if (deck.selectedIndex == 0) {
            window.arguments[0].value = document.getElementById("VarValue").value;
        } else {
            window.arguments[0].value = document.getElementById("VarPaths").getData();
        }
        if (obj.name == "") {
            ko.dialogs.alert("You must specify a variable name.");
            document.getElementById("VarName").focus();
            return false;
        }
        window.arguments[0].res = "ok";
        return true;
    } catch (e) {
        dump(e);
        //log.exception(e);
    }
    return true;
}

function doCancel()
{
    obj.res = "cancel";
    //window.arguments[0] = obj;
    return true;
}

function doPathVar()
{
    var textField = document.getElementById("VarValue");
    var deck = document.getElementById("VarDeck");
    var list = document.getElementById("VarPaths");
    var pathButton = document.getElementById("pathButton");
    if (deck.selectedIndex == 0) {
        list.setAttribute('collapsed','false');
        list.setData(textField.value);
        deck.selectedIndex = 1;
        pathButton.setAttribute("class", "less-icon button-toolbar-a");
    } else {
        var data = list.getData();
        textField.setAttribute('value', data);
        textField.value = data;
        deck.selectedIndex = 0;
        list.setAttribute('collapsed','true');
        pathButton.setAttribute("class", "more-icon button-toolbar-a");
    }
    window.sizeToContent();
}



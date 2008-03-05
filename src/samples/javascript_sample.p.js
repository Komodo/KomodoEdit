/* Copyright (c) 2000-2008 ActiveState Software Inc.

/* Use this sample to explore editing JavaScript with Komodo. */

function validateForm(form) {
    var i;
    var pass = true;
    for (i = 0; i < form.length; i++) {
        var element = form.elements[i];
        if (element.name.substring(0,8) == "required") {
            if (((element.type=="text" || element.type=="textarea") &&
                  element.value=='') && element.selectedIndex==0) {
                pass = false;
                break;
            }
        }
    }
    if (!pass) {
        var shortName = element.name.substring(8,30).toUpperCase();
        alert("Please complete the " + shortName + " field correctly.");
        return false;
    }
    else {
        return true;
    }
}

// Abbreviations:
//    - Snippets from the Abbreviations folder in projects and toolboxes
//      can be inserted by typing the snippet name followed by
//      'Ctrl'+'T' ('Cmd'+'T' on OS X). The Samples folder in the
//      Toolbox contains some default abbreviation snippets to get you
//      started.
//     
//  Try this below with the 'func' JavaScript snippet. An empty function
//  is created with "Tabstop" placeholders for the function name and
//  argument.


// Incremental search:
//   - Use 'Ctrl'+'I' ('Cmd'+'I' on OS X) to start an incremental search.
//   - Begin typing the characters you want to find. 
//   - As you type, the cursor moves to the first match after the current
//    cursor position. Press 'Esc' to cancel.

// Code Folding:
//   - Click the "-" and "+" symbols in the left margin.
//   - Use View/Fold to collapse or expand all blocks.

// Syntax Coloring:
//   - Language elements are colored according to the Fonts and Colors
//     preference.

// Background Syntax Checking:
//   - Syntax errors are underlined in red.
//   - Syntax warnings are underlined in green.
//   - Position the cursor over the underline to view the error or warning
//     message.

// Code Browsing:
//   1. If necesssary, enable Komodo's code intelligence (Edit|Preferences|Code Intelligence).
//   2. Select View|Tabs|Code Browser.
//   3. On the Code tab, click the plus sign next to "javascript_sample.js".
//   4. If necessary, display the Code Description pane by clicking the
//      "Show/Hide Description" button at the bottom of the Code Browser.
//   5. Select "validateForm". The Code Description pane indicates that the file
//      contains one function, validateForm(form).

// More:
//   - Press 'F1' to view the Komodo User Guide.


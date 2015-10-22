// Copyright (c) 2000-2011 ActiveState Software Inc.
// See the file LICENSE.txt for licensing information.

/* Do stuff when the user chooses to create one of these projects.
 *
 * Based on rails createRailsProject.js
 */

if (typeof(ko) == 'undefined') {
    var ko = {};
}
if (!('koextgen' in ko)) {
    ko.koextgen = {};
}

(function() {

this.enableCodeIntelForLanguage = function koextgen_komodolang(projectDir, data) {
    var cmd = 'startcodeintel ' +
              data.lang +
              ' -d ' + '"' + projectDir + '"';
    var callback = function() {
        // Update the keywords and comment styles.
        var osPath = Components.classes["@activestate.com/koOsPath;1"].
                        getService(Components.interfaces.koIOsPath);
        // Read in the UDL and komodo-lang file.
        var pylib_dir = osPath.join(projectDir, "pylib");
        var codeintel_filepath = osPath.join(pylib_dir, "codeintel_" + data.lang.toLowerCase() + ".py");
        var content = ko.koextgen.extensionLib.readFile(codeintel_filepath);
        if (content) {
            // Update the udl keywords.
            if (data.keywords.length > 0) {
                content = content.replace('# Keywords',
                            '# Keywords\n        "' + data.keywords.join('",\n        "') + '"\n');
            }
            if (data.is_html_based) {
                content = content.replace('#m_lang = "HTML"', 'm_lang = "HTML"');
                content = content.replace('#css_lang = ', 'css_lang  = ');
                content = content.replace('#csl_lang = ', 'csl_lang = ');
                content = content.replace('#tpl_lang = ', 'tpl_lang = ');
            } else if (data.is_xml_based) {
                content = content.replace('#m_lang = "XML"', 'm_lang = "XML"');
            } else {
                content = content.replace('#ssl_lang = ', 'ssl_lang = ');
            }

            ko.koextgen.extensionLib.writeFile(codeintel_filepath, content);
        }

        require("notify/notify").send('Enabled codeintel for ' + data.lang, "projects");
    };
    ko.koextgen.extensionLib.command(cmd, callback);
}

this.generateKomodoLanguage = function koextgen_komodolang(projectDir, data) {
    var cmd = 'startlang "' +
              data.lang +
              '" --ext ' + data.ext +
              ' -d ' + '"' + projectDir + '"';
    if (data.is_html_based) {
        cmd += ' --is-html-based';
    } else if (data.is_xml_based) {
        cmd += ' --is-xml-based';
    }
    var callback = function() {
        // Update the keywords and comment styles.
        var osPath = Components.classes["@activestate.com/koOsPath;1"].
                        getService(Components.interfaces.koIOsPath);
        // Read in the UDL and komodo-lang file.
        var udl_dir = osPath.join(projectDir, "udl");
        var udl_filepath = osPath.join(udl_dir, data.lang.toLowerCase() + "-mainlex.udl");
        var udl_content = ko.koextgen.extensionLib.readFile(udl_filepath);
        var kolang_dir = osPath.join(projectDir, "components");
        var kolang_filepath = osPath.join(kolang_dir, "ko" + data.lang + "_UDL_Language.py");
        var kolang_content = ko.koextgen.extensionLib.readFile(kolang_filepath);

        // Update the udl keywords.
        if (data.keywords.length > 0) {
            udl_content = udl_content.replace('# Keywords',
                                              '# Keywords\n        "' + data.keywords.join('",\n        "') + '"\n');
        }

        // Update the comment styles.
        function enable_comment_style(comment_str, comment_str2) {
            // This will uncomment the code - by removing the starting "#"
            udl_content = udl_content.replace(comment_str, comment_str.substr(1));
            kolang_content = kolang_content.replace(comment_str, comment_str.substr(1));
            if (comment_str2) {
                udl_content = udl_content.replace(comment_str2, comment_str2.substr(1));
                kolang_content = kolang_content.replace(comment_str2, comment_str2.substr(1));
            }
        }
        if (data.line_comment_slashslash)
            enable_comment_style("#'//'");
        if (data.line_comment_hash)
            enable_comment_style("#'#'");
        if (data.line_comment_dashdash)
            enable_comment_style("#'--'");
        if (data.line_comment_semicolan)
            enable_comment_style("#';'");
        if (data.line_comment_percent)
            enable_comment_style("#'%'");
        if (data.block_comment_c)
            enable_comment_style("#'/*'", "#('/*'");
        if (data.block_comment_pascal)
            enable_comment_style("#'(*'", "#('(*'");

        ko.koextgen.extensionLib.writeFile(udl_filepath, udl_content);
        ko.koextgen.extensionLib.writeFile(kolang_filepath, kolang_content);

        require("notify/notify").send('Added language ' + data.lang, "projects");

        if (data.enable_codeintel) {
            ko.koextgen.enableCodeIntelForLanguage(projectDir, data);
        }
    };
    ko.koextgen.extensionLib.command(cmd, callback);
}

this.createExtGenProject = function(targetName) {
    try {
        var project = ko.projects.manager.createNewProject();
        var projectURI = project.url;
        if (!project) {
            return;
        }
        var projectFileEx = project.getFile();
        // Get the project's location, then from one point higher populate it.
        var projectPath = projectFileEx.path;
        var projectDirPath = projectFileEx.dirName;
        var toolbox = ko.toolbox2.getProjectToolbox(projectURI);

        var prefset = project.prefset;
        prefset.setStringPref("koextgen.target", targetName);
        var baseName = projectFileEx.baseName;
        var ext = projectFileEx.ext;
        baseName = baseName.substr(0, baseName.length - ext.length);
        var baseNameCapitalized = baseName[0].toUpperCase() + baseName.substr(1);

        // Callback function to create the project structure.
        var createFn = function(data) {
            if (!data.valid) {
                return;
            }

            if (!ko.koextgen.extensionLib.updateProject(projectDirPath, targetName, data.vars)) {
                alert('Error encountered: '+ko.koextgen.extensionLib.error+"\nConfiguration aborted.");
                return;
            }

            if (targetName == "komodolang") {
                // Add the language details.
                ko.koextgen.generateKomodoLanguage(projectDirPath, data);
            }

            prefset.setBooleanPref('configured', true);

            //TODO: Finish building the configure macro
            var msg = 'Extension Project ' + data.vars.name + ' configured!';
            require("notify/notify").send(msg, "projects");
            ko.projects.manager.saveProject(project);

            var fromFile = 1, fromString = 2; // Enums
            var macroInfo = [
                [fromFile, "build.js", "Build", "chrome://fugue/skin/icons/building--plus.png"],
                [fromFile, "reconfigure.js", "Reconfigure", "chrome://fugue/skin/icons/wrench.png"],
            ];
            if (targetName.substr(0, 6) == "komodo") {

                macroInfo.push([fromFile, "buildandinstall.js", "Build and Install", "chrome://fugue/skin/icons/building--arrow.png"]);
                macroInfo.push([fromString, "ko.help.open('komodo_extensions');", "Docs - Extensions", "chrome://fugue/skin/icons/information-white.png"]);
            }
            if (targetName == "komodolang") {
                macroInfo.push([fromString, "ko.help.open('user-defined_languages');", "Docs - UDL", "chrome://fugue/skin/icons/information-white.png"]);
                macroInfo.push([fromFile, "udl_visualize.py", "UDL Visualization", "chrome://fugue/skin/icons/magnifier-zoom-actual-equal.png"]);
            }
            macroInfo.forEach(function(parts) {
                var readFrom = parts[0];
                var fname = parts[1];
                var macroName = parts[2];
                var iconURI = parts[3];
                var buildMacroContents = fname;
                if (readFrom === fromFile) {
                    buildMacroContents = ko.koextgen.extensionLib.getTemplateContents(fname);
                }
                var buildMacro = ko.toolbox2.createPartFromType("macro");
                buildMacro.name = macroName;
                buildMacro.value = buildMacroContents;
                buildMacro.iconurl = iconURI;
                ko.toolbox2.addItem(buildMacro, toolbox, /*selectItem=*/true);
                buildMacro.setBooleanAttribute('trigger_enabled', false);

                buildMacro.setLongAttribute('rank', 100);
                if (fname.substr(-3) == ".py") {
                    buildMacro.setStringAttribute('language', "Python");
                } else {
                    buildMacro.setStringAttribute('language', "JavaScript");
                    buildMacro.setBooleanAttribute('async', true);
                }
                buildMacro.save();
            });
        }

        //XXX: Reinstate ability to modify settings.
        var data = {
            'extensiontype': targetName,
            'callback': createFn,
            'valid': false,
            'configured': false,
            'vars': {
                'id': '',
                'name': baseNameCapitalized + (targetName == 'komodolang' ? ' Language' : ' Extension'),
                'creator': 'Me',
                'version': '0.1',
                'description': '',
                'homepageURL': '',
                'ext_name': baseName
            },
        };
        var setup_xul_uri = "chrome://koextgen/content/resources/setup.xul";
        window.openDialog(
            setup_xul_uri,
            "_blank",
            "centerscreen,chrome,resizable,scrollbars,dialog=no,close,modal=no",
        data);
    } catch(ex) {
        dump("\n\n*** Error in createExtProject: " + ex + "\n");
    }
};
}).apply(ko.koextgen);


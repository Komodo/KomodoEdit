/* -*- Mode: Javascript; tab-width: 2; c-basic-offset: 2; -*-
 * 
 * The contents of this file are subject to the Netscape Public
 * License Version 1.1 (the "License"); you may not use this file
 * except in compliance with the License. You may obtain a copy of
 * the License at http://www.mozilla.org/NPL/
 *
 * Software distributed under the License is distributed on an "AS
 * IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
 * implied. See the License for the specific language governing
 * rights and limitations under the License.
 *
 * The Original Code is mozilla.org code.
 *
 * The Initial Developer of the Original Code is Netscape
 * Communications Corporation.  Portions created by Netscape are
 * Copyright (C) 1998 Netscape Communications Corporation. All
 * Rights Reserved.
 *
 * Contributor(s): 
 *
 *  Doug Turner   <dougt@acm.org> 
 *  Pete Collins  <petejc@mozdev.org> 
 */

const G_DISPLAY_NAME    = "jsLib";
const G_NAME            = "jslib";
const G_VER             = "0.1.356";
const G_CHROME          = "Chrome";
const G_USER            = "Current User";
const G_CONTENT         = "";

const G_JAR_FILE        = "jslib.jar";
const G_CHROME_DIR      = getFolder(G_CHROME, "");
const G_USER_CHROME_DIR = getFolder(G_USER, "chrome");

const COMNT_1           = "INSTALL FOR JSLIB AS A JAR . . . \n\nInstall: ";
const COMNT_2           = "JSLIB Jar";
const KILO_BYTES        = 200; // 200K

const CONFIRM_MSG       =   "jslib has failed to install globally on your system. " 
                          + "This is most likely due to you not having the required " 
                          + "system permissions to do so.\n\n" 
                          + "Would you like to install jslib in your " 
                          + "Mozilla user directory instead?\n\n"
                          + "This means that only the current profile "
                          + "will be able to use jsib.\n\n"
                          + "If you wish to have a global install of jslib, you can cancel "
                          + "the install here and login as system administrator and retry "
                          + "the install from there. ";

const UP_TO_DATE        = "jsLib v,"+G_VER+" [UP TO DATE] - no installation needed"

var rv = initInstall(G_DISPLAY_NAME, G_NAME, G_VER);

logComment(COMNT_1 + rv);

if (verifyDiskSpace(getFolder("Program"), KILO_BYTES)) 
{
  var globalJar = getFolder(G_CHROME_DIR, G_JAR_FILE);
  var userJar = getFolder(G_USER_CHROME_DIR, G_JAR_FILE);
  
  // XXX Add command line "-jslib" handler --pete
  rv = addDirectory("Commandline Handler", "components", getFolder("Components"), "" );

  if (rv == ACCESS_DENIED) {
    alert("Unable to write to components directory "+getFolder("Components")+".\n You will need to restart the browser with administrator/root privileges to preperly install jsLib. After installing as root (or administrator), you will need to restart the browser one more time, to register jsLib.\n After the second restart, you can go back to running the browser without privileges!");

    cancelInstall(ACCESS_DENIED);

  } else if (rv != SUCCESS) {
    cancelInstall(rv);
  } else {
    if (File.exists(globalJar))
      upgradeGlobal();
    else if (File.exists(userJar))
      upgradeUser();
    else if (addGlobal() != SUCCESS)
      addUser();

    rv = getLastError();
    logComment(rv);

    if (rv == SUCCESS) {
      rv = performInstall();
      if (rv == REBOOT_NEEDED)
        cancelInstall(SUCCESS);
    } else {
      cancelInstall(rv);
    }
  }
} else {
  cancelInstall(INSUFFICIENT_DISK_SPACE);
}

// this function verifies disk space in kilobytes
function verifyDiskSpace(aDirPath, aSpaceRequired)
{
  var spaceAvailable;
  var rv = true;

  // Get the available disk space on the given path
  spaceAvailable = fileGetDiskSpaceAvailable(aDirPath);
                                                                                                    
  // Convert the available disk space into kilobytes
  spaceAvailable = parseInt(spaceAvailable / 1024);
                                                                                                    
  // do the verification
  if (spaceAvailable < aSpaceRequired) {
    logComment("Insufficient disk space: " + aDirPath);
    logComment("  required : " + spaceRequired + " K");
    logComment("  available: " + spaceAvailable + " K");
    rv = false;
  }
                                                                                                    
  return rv;
}

// InstallTrigger.getVersion is busted on Firefox 1.0.3
function checkVersion ()
{
  return true;

  /***************************
  var ver = new String(InstallTrigger.getVersion("jslib"));

  // strip off build info 
  ver = ver.substring(0, ver.lastIndexOf("."));

  return (G_VER >= ver);
  ***************************/
}

function upgradeGlobal ()
{
  if (checkVersion())
    addGlobal();
  else
    logComment(UP_TO_DATE);
}

function upgradeUser ()
{
  if (checkVersion())
    addUser();
  else
    logComment(UP_TO_DATE);
}

function addGlobal ()
{
  var rv = addDirectory(COMNT_2, "chrome",  G_CHROME_DIR, "");
  if (rv == 0) {
    // register chrome in global chrome
    rv = registerChrome(PACKAGE|CONTENT|DELAYED_CHROME, 
                      getFolder(G_CHROME_DIR, G_JAR_FILE), G_CONTENT);
    rv = registerChrome(CONTENT|DELAYED_CHROME,
                      getFolder(G_CHROME_DIR, "jsliblive"), "");
    cleanUser();
  }

  return rv;
}

function addUser ()
{
  // cancel previous install attempt
  cancelInstall(ACCESS_DENIED);
  alert("this build of jsLib only supports a global install");
  return false;

  var rv;
  if (confirm(CONFIRM_MSG)) {
    // reinitialize the install
    rv = initInstall(G_DISPLAY_NAME, G_NAME, G_VER);
    addDirectory(COMNT_2, "chrome",  G_USER_CHROME_DIR, "");
    if (rv == 0) {
      // register chrome in user home 
      rv = registerChrome(PACKAGE|CONTENT|PROFILE_CHROME, 
                          getFolder(G_USER_CHROME_DIR, G_JAR_FILE),  G_CONTENT);
      rv = registerChrome(CONTENT|DELAYED_CHROME, 
                            G_USER_CHROME_RUN, G_CONTENT);
      rv = registerChrome(CONTENT|DELAYED_CHROME, targetChrome, G_CONTENT);
    }
  }

  return rv; 
}

function log (aMsg, aRes)
{
  var rv = aRes;
  if (rv == 0)
    rv = "[SUCCESS]";

  logComment(aMsg+": "+rv);
}

function cleanUser ()
{
  cleanUserCompReg();
  // cleanUserChrome();
  cleanXULmfl();
}

function cleanUserCompReg ()
{
  var userCompReg = getFolder(G_USER, "compreg.dat");
  if (File.exists(userCompReg)) {
    var rv = File.remove(userCompReg);
    log("Removed user comreg.dat file", rv)
  }
}

function cleanUserChrome ()
{
  var userChrome = getFolder(G_USER_CHROME_DIR, "chrome.rdf");
  if (File.exists(userChrome)) {
    var rv = File.remove(userChrome);
    log("Removed user chrome.rdf file", rv)
  }
}

function cleanXULmfl ()
{
  var userChrome = getFolder(G_USER_CHROME_DIR, "XUL.mfl");
  if (File.exists(userChrome)) {
    var rv = File.remove(userChrome);
    log("Removed user XUL.mfl file", rv)
  }
}

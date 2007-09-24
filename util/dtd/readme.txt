instructions for using DTD validator

1. get xmlproc and install it.  scripts must be accessable somewhere, I just dropped them in komodo-devel/dtd
  <URL: http://www.garshol.priv.no/download/software/xmlproc/ >

2. import the dtdvalidator project

3. xul files need:

<!DOCTYPE window PUBLIC "-//MOZILLA//DTD XUL V1.0//EN" "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul">


If the xul uses a dtd for entity references, do this:

<!DOCTYPE window PUBLIC "-//MOZILLA//DTD XUL V1.0//EN" "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul" [
    <!ENTITY % viewprefsDTD SYSTEM "chrome://komodo/locale/editor/currentViewPrefs.dtd">
        %viewprefsDTD;
    <!ENTITY % prefIndentDTD SYSTEM "chrome://komodo/locale/pref/pref-indentation.dtd">
        %prefIndentDTD;
    <!ENTITY % prefEditsmartDTD SYSTEM "chrome://komodo/locale/pref/pref-editsmart.dtd">
        %prefEditsmartDTD;    
]>

Note, xmlproc doesn't handle chrome url's, so will error on any entity references.

4. xbl files need:

<!DOCTYPE bindings PUBLIC "-//MOZILLA//DTD XBL V1.0//EN" "http://www.mozilla.org/xbl">



aswixui -- ActiveState WiX UI library
=====================================

'aswixui' is a branch of the WiX project's UI library for defining an MSI
installer user interface. The original WiX sources are kept in:

    //depot/main/contrib/wix/...

with the "wixui" bits found in ".../src/ui/wixui". That tree is branched
here:

    p4 integrate //depot/main/contrib/wix/src/ui/wixui/... \
        //depot/main/support/aswixui/...

and some modifications are maintained to somewhat customize the UI for use
for MSI installers for some ActiveState products.

Currently there are not that many changes; and I don't expect there to be.


WiX Introduction
================

WiX is an XML schema and a set of tools for defining an MSI project and
building it. To effectively use WiX you have to know quite a lot about MSI
itself. Teaching that is out of scope here.  More details:

    http://sourceforge.net/projects/wix/

This is currently the best tutorial I know for learning how to use WiX:

    http://www.tramontana.co.hu/wix/index.html


Building 'aswixui'
==================

At the time of this writing there are three flavours of the WiX UI that
define a slightly different UI for an MSI. Currently only the "Feature Tree"
flavour is being used (currently only by Komodo), so this is the only WiX UI
library that is built.

To build the ActiveState WiX UI library (aswixui_featuretree.wixlib):

1. Install the latest WiX toolset:

    http://sourceforge.net/project/showfiles.php?group_id=105970&package_id=114109

   (Typically I install it to "C:\Program Files\Wix".)

2. Put it on your PATH. You should be able to run "candle" at the command
   line.

3. Get "nmake" on your PATH from somewhere. Visual Studio (any version)
   and Platform SDK both supply an "nmake.exe".

4. Build it:

    nmake


Using 'aswixui_featuretree.wixlib'
==================================

The way you use your WiX UI library is as follows:

1. Refer to the exported UI id in your normal WiX project source file (.wxs):

        <?xml version="1.0" encoding="utf-8"?>
        <Wix xmlns="http://schemas.microsoft.com/wix/2003/01/wi">
          <Product ...>
          ...
            <UIRef Id="WixUI" />
          ...
          </Product>
 
2. Link in the library when you build your files:

        candle *.wxs
        light -out foo.msi *.wixobj ...\aswixui_featuretree.wixlib




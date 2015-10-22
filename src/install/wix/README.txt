README for Komodo's WiX usage
=============================

This directory holds the WiX project files for building the Komodo Windows
installer. WiX is an open source tool (see sf.net) for building .msi files
from an XML definition. This is MSI so this is complicated.


What to do when I add/remove a file to/from Komodo
--------------------------------------------------

These WiX project files need to know the exact Komodo file manifest. I.e. if
a file is added or removed from the Komodo install tree then something in
here needs to be updated. If not the Windows build will fail.

When the build does fail a tool (bin/wax.py) is run against the current
project files and the Komodo install image to determine what changes need to
hand-integrated into the project files. That helps, but that takes time (a
Window build currently takes 45 min) so this is a 1.5 hour cycle at least. In
some circumstances you can help out by making the WiX changes ahead of time
(ideally with the same change that you add/remove files from Komodo). Here is
how.

*Note*: You don't have to be on Windows to do the following.

1. Are you adding or removing a *directory*? If so, then give up. This is hard
   enough that we should just allow the build to fail and generate that diff
   file with wax.py.

2. Resist the temptation to manually do the update without running
   'bin/newstuff.py' in step (4). There are a few subtleties involved in
   getting all the Wix attributes just right.

3. Is the file part of the "docs" or "core" feature? This tells you if you
   are editing "feature-docs.wxs.in" or "feature-core.wxs.in".

4. Removing a file: Find the <File> node for your file (just search for the
   basename and make sure the "src" attribute is the right one). Delete
   that line (i.e. the whole <File/> tag).

   Adding a file: Find the appropriate <Directory> node in the .wxs file
   (i.e. look for the <File> nodes for other files in the same directory).
   Duplicate one of the <File> lines from the same directory and edit it
   to look like this:

        <File Id="NEWFILE" src="feature-core\INSTALLDIR\path\to\your\new\file"/>

5. Run the "newstuff.py" script to update things -- it knows how to massage
   your new <File> node to the right thing:

        python bin\newstuff.py feature-core.wxs.in

   (Make that "feature-docs.wxs.in" if that is the one you were updating.)

6. Check it in.


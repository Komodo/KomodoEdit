<?xml version="1.0"?> 
<!-- ***** BEGIN LICENSE BLOCK *****
 Version: MPL 1.1/GPL 2.0/LGPL 2.1
 
 The contents of this file are subject to the Mozilla Public License
 Version 1.1 (the "License"); you may not use this file except in
 compliance with the License. You may obtain a copy of the License at
 http://www.mozilla.org/MPL/
 
 Software distributed under the License is distributed on an "AS IS"
 basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 License for the specific language governing rights and limitations
 under the License.
 
 The Original Code is Komodo code.
 
 The Initial Developer of the Original Code is ActiveState Software Inc.
 Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
 ActiveState Software Inc. All Rights Reserved.
 
 Contributor(s):
   ActiveState Software Inc
 
 Alternatively, the contents of this file may be used under the terms of
 either the GNU General Public License Version 2 or later (the "GPL"), or
 the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 in which case the provisions of the GPL or the LGPL are applicable instead
 of those above. If you wish to allow use of your version of this file only
 under the terms of either the GPL or the LGPL, and not to allow others to
 use your version of this file under the terms of the MPL, indicate your
 decision by deleting the provisions above and replace them with the notice
 and other provisions required by the GPL or the LGPL. If you do not delete
 the provisions above, a recipient may use your version of this file under
 the terms of any one of the MPL, the GPL or the LGPL.
 
 ***** END LICENSE BLOCK ***** -->

<!--      This sample XSL script shows you some of the features in Komodo
     to help you work with your XSL Transforms.  You can use this
     script to transform "birds.xml" (also in this project). -->
     
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:output method="xml" indent="yes"/>

<!-- Syntax Coloring:
    Komodo detects keywords and applies syntax coloring.  In the code
    below, note how "template" is a different color from "match",
    which is a different color from ""Class"". -->

<xsl:template match="Class">
    <html>
            <xsl:apply-templates select="Order"/>
    </html>
</xsl:template>

<!-- Background Syntax Checking:
    Komodo periodically checks for syntax errors in your XML code. Red
    and green "squiggles" underline syntax errors. For example, delete
    the closing ">" of this comment. The green squiggle indicates the
    syntax error.  Put your cursor on the squiggle to see the actual
    warning message in the status bar. -->
    
<xsl:template match="Order">
    <h1>Order is:  <xsl:value-of select="@Name"/></h1>
        <xsl:apply-templates select="Family"/><xsl:text>
</xsl:text>
</xsl:template>

<!-- Code Folding:-->
<!--    You can collapse and expand blocks of code. Click the -->
<!--    "-" and "+" signs in the light grey bar on the left. -->

<xsl:template match="Family">
    <h2>Family is:  <xsl:value-of select="@Name"/></h2>
	<xsl:apply-templates select="Species | SubFamily | text()"/>
</xsl:template>

<xsl:template match="SubFamily">
    <h3>SubFamily is <xsl:value-of select="@Name"/></h3>
        <xsl:apply-templates select="Species | text()"/>
</xsl:template>

<!-- AutoCompletion and CallTips

     Komodo helps you code faster by presenting you with available
     tags and attributes in the XSL namespace.

     For example, on a blank line below this comment block, slowly
     re-enter the following line of code:
       <xsl:template match="SubFamily"></xsl:template>
       
     When you type the colon ":", Komodo lists the valid XSLT
     tags. You can move through the list with your up and down arrow
     keys. To complete the tag name, press "Tab". This is called
     AutoCompletion.
     
     When you type the first few characters of "match", Komodo
     presents a list of valid attributes for the xsl:template tag. You
     can move through the list with your up and down arrow keys. To
     complete the attribute name, press "Tab". This is called
     CallTips.
     
     When you type the closing ">" character, Komodo adds the closing
     "</xsl:template>" tag for you. -->
     
<xsl:template match="Species">
	<p>
            <xsl:variable name="parent" select=".."/>
            <xsl:variable name="parentname" select="name($parent)"/>
            <xsl:variable name="name" select="@Scientific_Name"/>
            <xsl:choose>
                <xsl:when test="$parentname='SubFamily'">
                    <xsl:text>	</xsl:text><xsl:value-of select="."/><xsl:text> </xsl:text><xsl:value-of select="$name"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:value-of select="."/><xsl:text> </xsl:text><xsl:value-of select="$name"/>
                </xsl:otherwise>
            </xsl:choose>
	</p>
</xsl:template>

<!-- Debugging XSLT
    You can use Komodo to debug your XSLT programs. For example try
    the following steps:

    1. Set a breakpoint on the "<xsl:template match="Species">" line:
       click in the dark grey vertical bar on the left.

    2. Open the input file pane. At the bottom of the Editor pane,
       below your XSLT file, click "Choose File" and browse to the
       birds.xml sample file, or enter the full path to
       /samples/birds.xml.  Note - You can set breakpoints in this
       input XML file.  Note - You can have more than one XML file
       open for a given XSL file.  Note - You can use an XML file on a
       web server as your input XML file.  In the Input File field,
       enter the full URL to your XML file. For example,
       "http://www.yourdomain.com/yourfile.xml".

    3. Start debugging: from the Debug menu, select Start.

    4. In the XSLT Debugger Launch Options dialog, Komodo suggests the
       name of the XML document you currently have open as the XML
       file to transform. If this field is blank, click "Browse" and
       browse to the birds.xml sample file, or enter the full path to
       /samples/birds.xml.
    5. Go to your breakpoint: on the Debug toolbar, click "Go".  (To
       view and hide the toolbars, click the "grippies" on the left of
       each toolbar.)

    6. Step through the "Species" template: click any of the "Step"
       buttons.  You can watch the program output on the Output pane
       below and watch the variables in the Variables tab of the
       Output pane.

    7. Select a variable with your mouse and drag it to the Watched
       Variables pane to watch it. -->
      
</xsl:stylesheet>

<!--
See Komodo's online help for much more information on:
    - managing projects
    - keyboard shortcuts
    - remote debugging; and more
Just press < F1 >, or select Help from the Help menu.
-->

<?xml version="1.0"?> 

<!-- Use this sample script to explore some of Komodo's XSLT features. -->

<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:output method="html" indent="yes"/>

<!-- Syntax Coloring:
     - Language elements are colored according to the Fonts and Colors
       preference.-->

<xsl:template match="Class">
    <html>
            <xsl:apply-templates select="Order"/>
    </html>
</xsl:template>

<!--  Background Syntax Checking:
      - Syntax errors are underlined in red.
      - Syntax warnings are underlined in green.
      - Place the cursor over the underline to view the error or warning
        message. -->
    
<xsl:template match="Order">
    <h1>Order is:  <xsl:value-of select="@Name"/></h1>
        <xsl:apply-templates select="Family"/><xsl:text>
</xsl:text>
</xsl:template>

<!-- Incremental search:
     - Use 'Ctrl'+'I' ('Cmd'+'I' on OS X) to start an incremental search.
     - Begin typing the characters you want to find. 
     - As you type, the cursor moves to the first match after the current
       cursor position. Press 'Esc' to cancel. -->

<!-- Code Folding:
     - Click the "+" and "-" symbols in the left margin.
     - Use View|Fold to collapse or expand all blocks. -->

<xsl:template match="Family">
    <h2>Family is:  <xsl:value-of select="@Name"/></h2>
        <xsl:apply-templates select="Species | SubFamily | text()"/>
</xsl:template>

<xsl:template match="SubFamily">
    <h3>SubFamily is <xsl:value-of select="@Name"/></h3>
        <xsl:apply-templates select="Species | text()"/>
</xsl:template>

<!-- AutoComplete:
     - On a blank line below, enter an opening angle bracket ("<").
     - Komodo lists the valid XSLT tags.
     - Press 'Tab' to complete the tag name.-->

<!-- CallTips:
     - On a blank line below, enter "<xsl:template", and press the space bar.
     - Komodo displays a list of valid attributes.
     - To complete the selected attribute name, press 'Tab'. -->

<xsl:template match="Species">
    <p>
        <xsl:variable name="parent" select=".."/>
        <xsl:variable name="parentname" select="name($parent)"/>
        <xsl:variable name="name" select="@Scientific_Name"/>
        <xsl:choose>
            <xsl:when test="$parentname='SubFamily'">
                <xsl:text> </xsl:text><xsl:value-of select="."/><xsl:text> </xsl:text><xsl:value-of select="$name"/>
            </xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="."/><xsl:text> </xsl:text><xsl:value-of select="$name"/>
            </xsl:otherwise>
        </xsl:choose>
    </p>
</xsl:template>


</xsl:stylesheet>

<!-- More:
     - Press 'F1' to view the Komodo User Guide.
     - Select Help|Tutorial|XSLT Tutorial for more about Komodo and XSLT. -->


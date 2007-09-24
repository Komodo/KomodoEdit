<?xml version='1.0' encoding='ISO-8859-1'?>

<!-- =============================================================== -->
<!--                                                                 -->
<!-- This stylesheet renders documents conformant to XML-Spec DTD    -->
<!-- into XSL formatting objects. It performs no systematic          -->
<!-- treatment of element roles, limiting itself to basic            -->
<!-- functionality. The result is expected to be further converted   -->
<!-- to a page-oriented format (PDF, PostScript, PCL...).            -->
<!--                                                                 -->
<!-- Versions taken into account:                                    -->
<!--                                                                 -->
<!--    XML-Spec DTD: http://www.w3.org/XML/1998/06/xmlspec-v20.dtd  -->
<!--          XSL FO: http://www.w3.org/TR/2000/WD-xsl-20001018/     -->
<!--                                                                 -->
<!--     Author: Anton Dovgyallo                                     -->
<!--    Revised: Nikolai Grigoriev                                   -->
<!--                                                                 -->
<!-- © RenderX, 1999-2000                                            -->
<!--                                                                 -->
<!-- =============================================================== -->

<!DOCTYPE xsl:stylesheet [
  <!-- Character entities -->
  <!ENTITY  copyright "&#xA9;">
  <!ENTITY  trademark "&#x2122;">
  <!ENTITY  registered "&#xAE;">
  <!ENTITY  section "&#xA7;">
  <!ENTITY  endash "&#x2013;">
  <!ENTITY  emdash "&#x2014;">
  <!ENTITY  quotedblleft "&#x201C;">
  <!ENTITY  quotedblright "&#x201D;">
]>

<xsl:stylesheet version="1.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:fo="http://www.w3.org/1999/XSL/Format"
                xmlns:e="http://www.w3.org/1999/XSL/Spec/ElementSyntax">

<xsl:output method="xml"
            version="1.0"
            indent="no"
            encoding="utf-8"/>

<xsl:key name="generic-id" match="*[@id]" use="@id"/>
<xsl:key name="prod-id" match="prod" use="@id"/>
<xsl:key name="vcnote-id" match="vcnote" use="@id"/>
<xsl:key name="wfcnote-id" match="wfcnote" use="@id"/>
<xsl:key name="constraintnote-id" match="constraintnote" use="@id"/>
<xsl:key name="bibl-id" match="blist/bibl" use="@id"/>
<xsl:key name="termdef-id" match="termdef" use="@id"/>
<xsl:key name="proto-name" match="proto" use="@name"/>



<!-- =============================================================== -->
<!-- Parameters and attribute sets                                   -->
<!-- =============================================================== -->

<xsl:param name="column-count" select="1"/>
<xsl:param name="title-color">#003080</xsl:param>
<xsl:param name="href-color">#0050A0</xsl:param>

<xsl:param name="lhs-width">1.5in</xsl:param>
<xsl:param name="rhs-width">4in</xsl:param>

<xsl:attribute-set name="title-attrs">
  <xsl:attribute name="color"><xsl:value-of select="$title-color"/></xsl:attribute>
  <xsl:attribute name="font-weight">bold</xsl:attribute>
  <xsl:attribute name="keep-together.within-column">always</xsl:attribute>
  <xsl:attribute name="keep-with-next.within-column">always</xsl:attribute>
  <xsl:attribute name="text-align">start</xsl:attribute>
  <xsl:attribute name="space-after.optimum">6pt</xsl:attribute>
  <xsl:attribute name="hyphenate">false</xsl:attribute>
</xsl:attribute-set>

<xsl:attribute-set name="href-attrs">
  <xsl:attribute name="color"><xsl:value-of select="$href-color"/></xsl:attribute>
  <xsl:attribute name="text-decoration">underline</xsl:attribute>
</xsl:attribute-set>


<!-- =============================================================== -->
<!-- Suppresing deleted parts                                        -->
<!-- =============================================================== -->

<xsl:template match="*[@diff='del']" priority="10"/>
<xsl:template match="*[@diff='del']" mode="ref-mode" priority="10"/>
<xsl:template match="*[@diff='del']" mode="toc-mode" priority="10"/>
<xsl:template match="*[@diff='del']" mode="separator-mode" priority="10"/>
<xsl:template match="*[@diff='del']" mode="specref-mode" priority="10"/>
<xsl:template match="*[@diff='del']" mode="table-mode" priority="10"/>
<xsl:template match="*[@diff='del']" mode="property-list-mode" priority="10"/>
<xsl:template match="*[@diff='del']" mode="short-glist-mode" priority="10"/>


<!-- *************************************************************** -->
<!--                                                                 -->
<!-- Top-level template: page layout, headers/footers                -->
<!--                                                                 -->
<!-- *************************************************************** -->

<!-- =============================================================== -->
<!-- Common headers/footers                                          -->
<!-- =============================================================== -->

<xsl:template name="standard-static-contents">
  <xsl:param name="page-number"/>

  <fo:static-content flow-name="odd-header">
    <fo:list-block font="10pt Times"
                   provisional-distance-between-starts="4.5in"
                   provisional-label-separation="0in">
      <fo:list-item>
        <fo:list-item-label end-indent="label-end()">
          <fo:block text-align="start" font-weight="bold">
            <fo:retrieve-marker retrieve-class-name="div2"
                                retrieve-boundary="page"/> 
          </fo:block>
        </fo:list-item-label>
        <fo:list-item-body start-indent="body-start()">
          <fo:block text-align="end">
            <xsl:copy-of select="$page-number"/>
           </fo:block>
        </fo:list-item-body>
      </fo:list-item>        
    </fo:list-block>
  </fo:static-content>

  <fo:static-content flow-name="even-header">
    <fo:list-block font="10pt Times"
                   provisional-distance-between-starts="1.5in"
                   provisional-label-separation="0in">
      <fo:list-item>
        <fo:list-item-label end-indent="label-end()">
          <fo:block text-align="start">
            <xsl:copy-of select="$page-number"/>
          </fo:block>
        </fo:list-item-label>
        <fo:list-item-body start-indent="body-start()">
          <fo:block text-align="end" font-weight="bold">
            <fo:retrieve-marker retrieve-class-name="div1"
                                retrieve-boundary="page"/> 
          </fo:block>
        </fo:list-item-body>
      </fo:list-item>
    </fo:list-block>
  </fo:static-content>

  <fo:static-content flow-name="odd-footer">
    <fo:block font="bold italic 9pt Times" text-align="end">
      <xsl:value-of select="header/title"/>
    </fo:block>
  </fo:static-content>

  <fo:static-content flow-name="even-footer">
    <fo:block font="bold italic 9pt Times" text-align="start">
      <xsl:value-of select="header/title"/>
    </fo:block>
  </fo:static-content>

  <fo:static-content flow-name="blank-body">
    <fo:block font="italic 10pt Times" text-align="center">
      This page is intentionally left blank.
    </fo:block>
  </fo:static-content>

  <fo:static-content flow-name="last-blank-header">
    <fo:block font="bold 10pt Times" text-align="end">
      <xsl:value-of select="header/title"/>
      (<xsl:value-of select="header/w3c-designation"/>)
    </fo:block>
  </fo:static-content>

</xsl:template>


<!-- =============================================================== -->
<!-- Topmost template                                                -->
<!-- =============================================================== -->

<xsl:template match="spec">
  <fo:root hyphenate="true"
           hyphenation-push-character-count="3"
           hyphenation-remain-character-count="3">
    <fo:layout-master-set>
      <fo:simple-page-master master-name="first-page">
        <fo:region-body  margin="0.9in 0.6in 0.9in 1in"  
                         column-count="{$column-count}"
                         padding="6pt 0pt"/> 
      </fo:simple-page-master>

      <fo:simple-page-master master-name="odd-page">
        <fo:region-body  margin="0.9in 0.6in 0.9in 1in" 
                         column-count="{$column-count}"
                         padding="6pt 0pt"
                         border-top="thin solid silver"
                         border-bottom="thin solid silver"/> 
        <fo:region-before region-name="odd-header"
                         extent="0.9in"
                         padding="0pt 0.6in 6pt 1in"
                         display-align="after"
                         precedence="false"/>
        <fo:region-after region-name="odd-footer"
                         extent="0.9in"
                         padding="6pt 0.6in 0pt 1in"
                         precedence="false"/>
      </fo:simple-page-master>

      <fo:simple-page-master master-name="even-page">
        <fo:region-body  margin="0.9in 1in 0.9in 0.6in" 
                         column-count="{$column-count}"
                         padding="6pt 0pt"
                         border-top="thin solid silver"
                         border-bottom="thin solid silver"/> 
        <fo:region-before region-name="even-header"
                         extent="0.9in"
                         padding="0pt 1in 6pt 0.6in"
                         display-align="after"
                         precedence="false"/>
        <fo:region-after  region-name="even-footer"
                         extent="0.9in"
                         padding="6pt 1in 0pt 0.6in"
                         precedence="false"/>
      </fo:simple-page-master>

      <fo:simple-page-master master-name="blank-page">
        <fo:region-body  region-name="blank-body"
                         margin="0.9in 1in 0.9in 0.6in" 
                         display-align="center"
                         padding="6pt 0pt"
                         border-top="thin solid silver"
                         border-bottom="thin solid silver"/> 
        <fo:region-before region-name="even-header"
                         extent="0.9in"
                         padding="0pt 1in 6pt 0.6in"
                         display-align="after"
                         precedence="false"/>
        <fo:region-after region-name="even-footer"
                         extent="0.9in"
                         padding="6pt 1in 0pt 0.6in"
                         precedence="false"/>

      </fo:simple-page-master>

      <fo:simple-page-master master-name="last-blank-page">
        <fo:region-body  region-name="blank-body"
                         margin="0.9in 1in 0.9in 0.6in" 
                         display-align="center"
                         padding="6pt 0pt"
                         border-top="thin solid silver"
                         border-bottom="thin solid silver"/> 
        <fo:region-before region-name="last-blank-header"
                         extent="0.9in"
                         padding="0pt 1in 6pt 0.6in"
                         display-align="after"
                         precedence="false"/>
        <fo:region-after region-name="even-footer"
                         extent="0.9in"
                         padding="6pt 1in 0pt 0.6in"
                         precedence="false"/>

      </fo:simple-page-master>

      <fo:page-sequence-master master-name="header">
        <fo:single-page-master-reference master-name="first-page"/>
        <fo:repeatable-page-master-alternatives>
          <fo:conditional-page-master-reference
                    odd-or-even="odd" master-name="odd-page"/>
          <fo:conditional-page-master-reference
                    odd-or-even="even" master-name="even-page"/>
        </fo:repeatable-page-master-alternatives>
      </fo:page-sequence-master>

      <fo:page-sequence-master master-name="TOC">
        <fo:repeatable-page-master-alternatives>
          <fo:conditional-page-master-reference
                    blank-or-not-blank="blank" master-name="blank-page"/>
          <fo:conditional-page-master-reference
                    odd-or-even="odd" master-name="odd-page"/>
          <fo:conditional-page-master-reference
                    odd-or-even="even" master-name="even-page"/>
        </fo:repeatable-page-master-alternatives>
      </fo:page-sequence-master>

      <fo:page-sequence-master master-name="body">
        <fo:repeatable-page-master-alternatives>
          <fo:conditional-page-master-reference
                    blank-or-not-blank="blank" master-name="last-blank-page"/>
          <fo:conditional-page-master-reference
                    odd-or-even="odd" master-name="odd-page"/>
          <fo:conditional-page-master-reference
                    odd-or-even="even" master-name="even-page"/>
        </fo:repeatable-page-master-alternatives>
      </fo:page-sequence-master>

    </fo:layout-master-set>

    <!-- Front header -->

    <fo:page-sequence master-name="header" format="i">
                      
      <xsl:call-template name="standard-static-contents">
        <xsl:with-param name="page-number"><fo:page-number/></xsl:with-param>
      </xsl:call-template>

      <fo:flow flow-name="xsl-region-body" font="11pt Times">
        <xsl:apply-templates select="header"/>
      </fo:flow>
    </fo:page-sequence>

    <!-- TOC -->
    <fo:page-sequence master-name="TOC" format="i" 
                      force-page-count="end-on-even">

      <xsl:call-template name="standard-static-contents">
        <xsl:with-param name="page-number">
          <fo:page-number/> 
        </xsl:with-param>
      </xsl:call-template>

      <fo:flow flow-name="xsl-region-body" font="11pt Times">
        <xsl:call-template name="toc"/>
      </fo:flow>
    </fo:page-sequence>

    <!-- Body -->
    <fo:page-sequence format="1" initial-page-number="1"
                      force-page-count="end-on-even"
                      master-name="body">

      <xsl:call-template name="standard-static-contents">
        <xsl:with-param name="page-number">
          Page <fo:page-number/> 
          of <fo:page-number-citation ref-id="terminator"/>
        </xsl:with-param>
      </xsl:call-template>

      <fo:flow flow-name="xsl-region-body" font="11pt Times">
        <fo:block>
          <xsl:apply-templates select="front"/>
          <xsl:apply-templates select="body"/>
          <xsl:apply-templates select="back"/>
        </fo:block>
        <fo:block id="terminator"/>
      </fo:flow>
    </fo:page-sequence>
  </fo:root>

</xsl:template>


<!-- *************************************************************** -->
<!--                                                                 -->
<!-- Spec Header and Its Descendants. Most of the the styling is     -->
<!-- merged into a single template, for easier layout control;       -->
<!-- <pubstmt>, <sourcedesc>, <langusage>, <revisiondesc> omitted.   --> 
<!--                                                                 -->
<!-- *************************************************************** -->


<xsl:template match="header">

  <!-- Logo -->
  <fo:block>
    <fo:basic-link external-destination="url('http://www.w3.org/')">  
      <fo:external-graphic src="url('w3c.gif')"/>
    </fo:basic-link>
  </fo:block>  

  <!-- Titles/version/date/etc -->
  <fo:block xsl:use-attribute-sets="title-attrs">
    <fo:block font-size="30pt" space-before.optimum="1in">
      <xsl:apply-templates select="title"/>
    </fo:block>
    <fo:block font-size="24pt" space-before.optimum="6pt">
      <xsl:apply-templates select="subtitle"/>
    </fo:block>
    <fo:block font-size="24pt" space-before.optimum="12pt">
      <xsl:apply-templates select="version"/>
    </fo:block>
    <fo:block font-size="18pt" space-before.optimum="18pt">
      <xsl:apply-templates select="w3c-doctype"/> 
      <xsl:text> </xsl:text>
      <xsl:apply-templates select="pubdate/day"/> 
      <xsl:text> </xsl:text>
      <xsl:apply-templates select="pubdate/month"/> 
      <xsl:text> </xsl:text>
      <xsl:apply-templates select="pubdate/year"/>
    </fo:block>
  </fo:block>

  <fo:wrapper text-align="justify">

    <!-- References to document locations -->
    <xsl:apply-templates select="publoc"/>
    <xsl:apply-templates select="latestloc"/>
    <xsl:apply-templates select="prevlocs"/>


    <!-- Authors/Editors -->
    <xsl:apply-templates select="authlist"/>

    <!-- Copyright -->
    <fo:block space-before.optimum="18pt" font-size="10pt">

      <xsl:choose>
        <xsl:when test="copyright">
          <xsl:apply-templates select="copyright"/>
        </xsl:when>
        <xsl:otherwise> 
          <!-- Provide default W3C copyright notice -->
          Copyright &copyright;
          <xsl:value-of select="pubdate/year"/>
          W3C (MIT, INRIA, Keio), 
          All Rights Reserved. W3C liability, trademark, 
          document use and software licensing rules apply.
        </xsl:otherwise>
      </xsl:choose>
    </fo:block>
     
    <!-- Abstract and status -->
    <xsl:apply-templates select="abstract"/>
    <xsl:apply-templates select="status"/>

    <!-- Notice. If there are more than one notice, they are numbered. -->
    <xsl:if test="notice">
      <fo:block space-before.optimum="12pt" 
                xsl:use-attribute-sets="title-attrs">
         Notice to the reader
      </fo:block>

      <xsl:choose>
        <xsl:when test="count(notice) &gt; 1">
          <fo:list-block provisional-label-separation="3pt"
                         provisional-distance-between-starts="18pt">
            <xsl:for-each select="notice">
              <fo:list-item space-after.optimum="6pt">
                <fo:list-item-label end-indent="label-end()">
                  <fo:block><xsl:number format="1."/></fo:block>
                </fo:list-item-label>
                <fo:list-item-body start-indent="body-start()">
                  <fo:block><xsl:apply-templates/></fo:block>
                </fo:list-item-body>
              </fo:list-item>        
            </xsl:for-each>
          </fo:list-block>
        </xsl:when>
        <xsl:otherwise>
          <fo:block>
            <xsl:apply-templates select="notice"/>
          </fo:block>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:if>
  </fo:wrapper>
</xsl:template>

<!-- =============================================================== -->
<!-- Templates for single zones in the header                        -->
<!-- =============================================================== -->

<!-- Location. Support for role="available-format" added -->

<xsl:template match="header/publoc">
  <fo:block keep-together.within-column="always">
    <fo:block space-before.optimum="12pt" 
              space-after.optimum="6pt">
      This version:
    </fo:block>
    <xsl:for-each select="loc[not (@role='available-format')]">
      <fo:block start-indent="0.5in">
        <xsl:apply-templates select="."/>
      </fo:block>
    </xsl:for-each>

    <!-- Extension found in XSLT Spec -->
    <xsl:if test="loc[@role='available-format']"> 

      <fo:block start-indent="0.5in">
        Available formats:
        <xsl:for-each select="loc[@role='available-format']">
          <xsl:choose>
            <xsl:when test="position() = 1">
              <xsl:text> </xsl:text>
            </xsl:when>
            <xsl:otherwise>
              <xsl:text>, </xsl:text>
            </xsl:otherwise>
          </xsl:choose>

          <xsl:apply-templates select="."/>
        </xsl:for-each>
      </fo:block>
    </xsl:if>

    <!-- Extension found in XSL WD Spec -->
    <xsl:apply-templates select="otherversions"/>

  </fo:block>
</xsl:template>

<!-- =============================================================== -->
<!-- Location - other versions                                       -->
<xsl:template match="publoc/otherversions">
  <fo:block start-indent="0.5in">
    <xsl:text>(</xsl:text>
    <xsl:for-each select="loc">
      <xsl:apply-templates select="."/>
      <xsl:if test="following-sibling::loc">
        <xsl:text>, </xsl:text>
      </xsl:if>      
    </xsl:for-each>
    <xsl:text>)</xsl:text>
  </fo:block>
</xsl:template>

<!-- =============================================================== -->

<xsl:template match="header/latestloc">
  <fo:block keep-together.within-column="always">
    <fo:block space-before.optimum="12pt" 
              space-after.optimum="6pt">
      Latest version:
    </fo:block>
    <xsl:for-each select="loc">
      <fo:block start-indent="0.5in">
        <xsl:apply-templates select="."/>
      </fo:block>
    </xsl:for-each>
  </fo:block>
</xsl:template>

<!-- =============================================================== -->

<xsl:template match="header/prevlocs">
  <fo:block keep-together.within-column="always">
    <fo:block space-before.optimum="12pt" 
              space-after.optimum="6pt">
      <xsl:choose>
        <xsl:when test="count(loc) &gt; 1">
          Previous versions:
        </xsl:when>
        <xsl:otherwise>
          Previous version:
        </xsl:otherwise>
      </xsl:choose>
    </fo:block>
    <xsl:for-each select="loc">
      <fo:block start-indent="0.5in">
        <xsl:apply-templates select="."/>
      </fo:block>
    </xsl:for-each>
  </fo:block>
</xsl:template>

<!-- =============================================================== -->

<xsl:template match="header/authlist">
  <fo:block keep-together.within-column="always">
    <fo:block space-before.optimum="12pt" 
              space-after.optimum="6pt">
      <xsl:choose>
        <xsl:when test="count(author) &gt; 1">
          Authors and Contributors:
        </xsl:when>
        <xsl:otherwise>
          Author:
        </xsl:otherwise>
      </xsl:choose>
    </fo:block>
    <fo:block start-indent="0.5in">
      <xsl:apply-templates select="author"/>
    </fo:block>
  </fo:block>
</xsl:template>

<!-- =============================================================== -->

<xsl:template match="authlist/author">
  <fo:block>
    <xsl:apply-templates select="name"/> 
    <xsl:text> </xsl:text>
    <xsl:apply-templates select="affiliation"/>
    <xsl:apply-templates select="email"/>
  </fo:block>
</xsl:template>

<!-- =============================================================== -->

<xsl:template match="author/affiliation">
  (<xsl:apply-templates/>)     
  <xsl:text> </xsl:text>
</xsl:template>

<!-- =============================================================== -->

<xsl:template match="header/abstract">
  <fo:block keep-together.within-column="always">
    <fo:block space-before.optimum="12pt" 
              xsl:use-attribute-sets="title-attrs">
       Abstract
    </fo:block>

    <fo:block>
      <xsl:apply-templates/>
    </fo:block>
  </fo:block>

</xsl:template>

<!-- =============================================================== -->

<xsl:template match="header/status">
  <fo:block space-before.optimum="12pt" 
            xsl:use-attribute-sets="title-attrs">
     Status of this document
  </fo:block>

  <fo:block>
    <xsl:apply-templates/>
  </fo:block>

</xsl:template>


<!-- *************************************************************** -->
<!--                                                                 -->
<!-- Standalone elements                                             -->
<!--                                                                 -->
<!-- *************************************************************** -->

<!-- Paragraph. If a paragraph is shorter that 80 symbols and ends   -->
<!-- with a colon, it is kept with the next one                      -->

<xsl:template match="p">
  <xsl:param name="prefix"/> <!-- note/issue prefix -->

  <fo:block>
    <xsl:if test="not(ancestor::table) and not(parent::prnote)">
      <xsl:attribute name="space-after.optimum">6pt</xsl:attribute>
    </xsl:if>

    <xsl:if test="@id">
      <xsl:attribute name="id">
        <xsl:value-of select="generate-id()"/>
      </xsl:attribute>
    </xsl:if>

    <xsl:variable name="txt" select="normalize-space(.)"/>
    <xsl:variable name="txtlen" select="string-length($txt)"/>
    <xsl:if test="($txtlen &lt; 80 and substring($txt, $txtlen)=':')
                 or (parent::css-cited and not(preceding-sibling::p))">    
      <xsl:attribute name="keep-with-next.within-column">always</xsl:attribute>
    </xsl:if>

    <xsl:if test="not(preceding-sibling::p) and $prefix != '' ">
       <fo:wrapper font-weight="bold">
          <xsl:value-of select="$prefix"/>
       </fo:wrapper>
    </xsl:if>

    <xsl:apply-templates/>

  </fo:block>
</xsl:template>

<!-- =============================================================== -->
<!-- Lists: ordered and unordered                                    -->
<!-- =============================================================== -->

<!-- Common list-block template: generic. All subtle processing      -->
<!-- is done in item templates.                                      -->

<xsl:template match="slist|ulist|olist">
  <xsl:variable name="list-type" 
                select="name()"/>
  <xsl:variable name="list-level" 
                select="count(ancestor-or-self::*[name()=$list-type])"/>

  <fo:list-block provisional-label-separation="3pt"
                 space-before.optimum="6pt">
    <xsl:choose>
      <xsl:when test="self::slist">
        <xsl:attribute name="provisional-distance-between-starts">12pt</xsl:attribute>
        <xsl:attribute name="padding-left">12pt</xsl:attribute>
        <xsl:attribute name="space-after.optimum">6pt</xsl:attribute>
      </xsl:when>                 
      <xsl:otherwise>
        <xsl:attribute name="provisional-distance-between-starts">18pt</xsl:attribute>
      </xsl:otherwise>
    </xsl:choose>
                   

    <xsl:apply-templates>
      <xsl:with-param name="list-level" select="$list-level"/>
    </xsl:apply-templates>
  </fo:list-block>
</xsl:template>


<!-- =============================================================== -->
<!-- Item for an unordered list                                      -->

<xsl:template match="ulist/item">
  <xsl:param name="list-level"/>

  <fo:list-item>

    <fo:list-item-label end-indent="label-end()">
      <fo:block text-align="start">

        <xsl:choose>
          <xsl:when test="($list-level mod 2) = 1">&#x2022;</xsl:when> <!-- disk bullet -->
          <xsl:otherwise>-</xsl:otherwise>
        </xsl:choose>  
      </fo:block>
    </fo:list-item-label>

    <fo:list-item-body start-indent="body-start()">
      <fo:block><xsl:apply-templates/></fo:block>
    </fo:list-item-body>
  </fo:list-item>

</xsl:template>


<!-- =============================================================== -->
<!-- Item for a simple list                                          -->
<!-- Despite the prescriptions of the XMLSpec, I have made it        -->
<!-- a bulleted list, because of its usage in XSLT/XPath             -->

<xsl:template match="slist/sitem">
  <xsl:param name="list-level"/>

  <fo:list-item>

    <fo:list-item-label end-indent="label-end()">
      <fo:block text-align="start">-</fo:block>
    </fo:list-item-label>

    <fo:list-item-body start-indent="body-start()">
      <fo:block>
        <xsl:apply-templates/>
      </fo:block>
    </fo:list-item-body>
  </fo:list-item>

</xsl:template>



<!-- =============================================================== -->
<!-- Ordered list item -->

<xsl:template match="olist/item">
  <xsl:param name="list-level"/>

  <fo:list-item id="{generate-id()}">

    <fo:list-item-label end-indent="label-end()">
      <fo:block text-align="start">
        <xsl:call-template name="olist-item-number">
          <xsl:with-param name="list-level" select="$list-level"/>
        </xsl:call-template>
      </fo:block>
    </fo:list-item-label>

    <fo:list-item-body start-indent="body-start()">
      <fo:block>
        <xsl:apply-templates/>
      </fo:block>
    </fo:list-item-body>
  </fo:list-item>

</xsl:template>

<!-- Ordered list item, spec reference mode -->
<!-- It generates just a number as a text   -->
<!-- Note that this template has no $list-level -->
<!-- parameter; it should be calculated in-place -->

<xsl:template match="olist/item" mode="specref-mode">
  <fo:basic-link internal-destination="{generate-id()}"
                  color="{$href-color}">
    <xsl:call-template name="olist-item-number">
      <xsl:with-param name="list-level">
        <xsl:value-of select="count(ancestor-or-self::olist)"/>
      </xsl:with-param>
    </xsl:call-template>
  </fo:basic-link>
</xsl:template>


<xsl:template name="olist-item-number">
  <xsl:param name="list-level"/>
  <xsl:choose>
    <xsl:when test="$list-level=1"> <!-- arabic -->
      <xsl:number format="1."/>
    </xsl:when>

    <xsl:when test="$list-level=2"> <!-- capital letter -->
      <xsl:number format="A."/>
    </xsl:when>

    <xsl:when test="$list-level=3"> <!-- small roman -->
      <xsl:number format="i."/>
    </xsl:when>

    <xsl:when test="$list-level=4"> <!-- small letter -->
      <xsl:number format="a)"/>
    </xsl:when>

    <xsl:otherwise>  <!-- arabic by default -->
      <xsl:number format="1)"/>
    </xsl:otherwise>

  </xsl:choose> 
</xsl:template>

<!-- =============================================================== -->
<!-- Special lists - simple, glossary, and bibliography              -->
<!-- =============================================================== -->

<xsl:template match="glist|blist">
  <fo:block space-before.optimum="6pt"
            space-after.optimum="6pt">
    <xsl:apply-templates/>
  </fo:block>
</xsl:template>

<xsl:template match="glist[not(gitem/label[string-length() &gt; 3])]"
              priority="2">
  <fo:list-block space-before.optimum="6pt"
                 space-after.optimum="6pt"
                 provisional-distance-between-starts="36pt"
                 provisional-label-separation="3pt">
    <xsl:apply-templates mode="short-glist-mode"/>
  </fo:list-block>
</xsl:template>

<!-- =============================================================== -->
<!-- Item for a glossary list - regular                              -->

<xsl:template match="glist/gitem">
  <fo:block keep-together.within-column="always"
            keep-with-next.within-column="always"
            space-before.optimum="6pt"
            font-style="italic"
            font-weight="bold">
    <xsl:apply-templates select="label"/>
  </fo:block>

  <fo:block keep-with-previous.within-column="always"
            space-before.optimum="3pt"
            start-indent="0.5in">
    <xsl:apply-templates select="def"/>
  </fo:block>

</xsl:template>

<!-- =============================================================== -->
<!-- Item for a glossary list - short                               -->

<xsl:template match="glist/gitem" mode="short-glist-mode">
  <fo:list-item space-before.optimum="6pt">
    <fo:list-item-label end-indent="label-end()">
      <fo:block font-style="italic"
                font-weight="bold">
        <xsl:apply-templates select="label"/>
      </fo:block>
    </fo:list-item-label>
    <fo:list-item-body start-indent="body-start()">
      <fo:block>
        <xsl:apply-templates select="def"/>
      </fo:block>
    </fo:list-item-body>
  </fo:list-item>
</xsl:template>


<!-- =============================================================== -->
<!-- Bibliographical entry. In reference mode, only @key is used.    -->

<xsl:template match="blist/bibl">

  <fo:block id="{generate-id()}" 
            space-after.optimum="9pt"
            keep-together.within-column="always">
    <xsl:if test="@key">
      <fo:block keep-with-next.within-column="always"
                space-after.optimum="3pt"
                font-style="italic">
       <xsl:value-of select="@key"/>
      </fo:block>
    </xsl:if>

    <fo:block start-indent="0.5in" text-align="start">
      <xsl:choose>
        <xsl:when test="@href">
          <fo:basic-link external-destination="url('{@href}')"
                          xsl:use-attribute-sets="href-attrs">
              <xsl:apply-templates/>
          </fo:basic-link>
        </xsl:when>
        <xsl:otherwise>
          <xsl:apply-templates/>
        </xsl:otherwise>
      </xsl:choose>
    </fo:block>
  </fo:block>

</xsl:template>


<xsl:template match="blist/bibl" mode="ref-mode">

  <xsl:text>[</xsl:text>
  <fo:basic-link internal-destination="{generate-id()}"
                  color="{$href-color}">
    <xsl:value-of select="@key"/>
  </fo:basic-link>
  <xsl:text>]</xsl:text>

</xsl:template>


<!-- =============================================================== -->
<!-- Organization list (i.e. WG members list)                        -->

<xsl:template match="orglist">

  <fo:block space-before.optimum="6pt"
            text-align="justify">
    <xsl:apply-templates select="member"/>
  </fo:block>

</xsl:template>


<xsl:template match="orglist/member">
  <xsl:apply-templates select="name"/>
  <xsl:apply-templates select="affiliation"/>
  <xsl:apply-templates select="role"/>    
  <xsl:if test="not(position()=last())">
    <xsl:text>; </xsl:text> 
  </xsl:if>  
</xsl:template>

<xsl:template match="orglist/member/affiliation">
  <xsl:text>, </xsl:text>
  <xsl:apply-templates/>
</xsl:template>

<xsl:template match="orglist/member/role">
  <xsl:text> (</xsl:text>
  <xsl:apply-templates/>
  <xsl:text>)</xsl:text>
</xsl:template>


<!-- =============================================================== -->
<!-- Notes of various kinds                                          -->
<!-- =============================================================== -->

<xsl:template name="generic-note">
  <xsl:param name="note-type">NOTE: </xsl:param>
  <fo:block padding-left="0.35in" 
            font-size="9.5pt"
            space-before.optimum="12pt" 
            space-after.optimum="6pt"
            id="{generate-id()}">

    <!-- If there are no paragraph children, put prefix separately -->
    <xsl:if test="not(p)">  
      <fo:block space-after.optimum="3pt" 
                font-weight="bold"
                keep-with-next.within-column="always">
         <xsl:value-of select="$note-type"/>
      </fo:block>
    </xsl:if>

    <xsl:apply-templates> 
      <xsl:with-param name="prefix" select="$note-type"/>
    </xsl:apply-templates>

  </fo:block>
</xsl:template>

<xsl:template match="note">
  <xsl:call-template name="generic-note"/>
</xsl:template>

<xsl:template match="issue">
  <xsl:call-template name="generic-note">
    <xsl:with-param name="note-type">
      <xsl:text>Issue </xsl:text>
      <xsl:number count="//issue" format="1"/>
      <xsl:text>: </xsl:text>
    </xsl:with-param>
  </xsl:call-template>
</xsl:template>

<xsl:template match="issue" mode="specref-mode">
  <fo:basic-link internal-destination="{generate-id()}"
                  color="{$href-color}">
    <xsl:text>Issue </xsl:text>
    <xsl:number count="//issue" format="1"/>
    <xsl:text>: </xsl:text>
  </fo:basic-link>
</xsl:template>

<!-- =============================================================== -->
<!-- Constraint notes - Normal mode                                  -->
<!-- =============================================================== -->

<xsl:template name="constraint-note">
  <xsl:param name="note-type"/>
  <fo:block padding="6pt"
            padding-bottom="3pt" 
            border="1pt solid gray" 
            border-after-width.conditionality="discard" 
            border-before-width.conditionality="discard" 
            padding-after.conditionality="discard" 
            padding-before.conditionality="discard" 
            space-after.optimum="4pt"
            space-after.precedence="force" 
            id="{generate-id()}">

    <fo:block keep-with-next.within-column="always"
              keep-together.within-column="always"
              space-after.optimum="3pt"
              font-weight="bold">
      <xsl:value-of select="$note-type"/>
      <xsl:text>: </xsl:text>
      <xsl:apply-templates select="head"/> 
    </fo:block>
    
    <xsl:apply-templates select="*[not(self::head)]"/>

  </fo:block>
</xsl:template>


<xsl:template match="wfcnote">
  <xsl:call-template name="constraint-note">
    <xsl:with-param name="note-type">Well-Formedness Constraint</xsl:with-param>
  </xsl:call-template>
</xsl:template>

<xsl:template match="vcnote">
  <xsl:call-template name="constraint-note">
    <xsl:with-param name="note-type">Validity Constraint</xsl:with-param>
  </xsl:call-template>
</xsl:template>


<xsl:template match="constraintnote">
  <xsl:call-template name="constraint-note">
    <xsl:with-param name="note-type" select="@type"/>
  </xsl:call-template>
</xsl:template>

<!-- Constraint note reference in specref mode -->
<xsl:template match="wfcnote | vcnote | costraintnote | nscnote" 
              mode="specref-mode">
  <fo:basic-link internal-destination="{generate-id()}"
                  color="{$href-color}">
    <xsl:text>&quot;</xsl:text>
    <xsl:apply-templates select="head"/> 
    <xsl:text>&quot;</xsl:text>
  </fo:basic-link>
</xsl:template>

<!-- =============================================================== -->
<!-- Constraint notes - Reference mode                               -->
<!-- =============================================================== -->

<xsl:template name="constraint-note-reference">
  <xsl:param name="note-type"/>
  <fo:basic-link internal-destination="{generate-id()}"
                  color="{$href-color}">
    <xsl:value-of select="note-type"/>
    <xsl:text>: </xsl:text>
    <xsl:apply-templates select="head"/> 
  </fo:basic-link>
</xsl:template>

<xsl:template match="wfcnote" mode="ref-mode">
  [<xsl:call-template name="constraint-note-reference">
    <xsl:with-param name="note-type">WFC</xsl:with-param>
  </xsl:call-template>]
</xsl:template>

<xsl:template match="vcnote" mode="ref-mode">
  [<xsl:call-template name="constraint-note-reference">
    <xsl:with-param name="note-type">VC</xsl:with-param>
  </xsl:call-template>]
</xsl:template>

<xsl:template match="constraintnote" mode="ref-mode">
  [<xsl:call-template name="constraint-note-reference">
    <xsl:with-param name="note-type" select="@type"/>
  </xsl:call-template>]
</xsl:template>


<!-- =============================================================== -->
<!-- Illustrations                                                   -->
<!-- =============================================================== -->

<!-- Example - rendered in monospace font -->

<xsl:template match="eg">
  <fo:block font-family="Courier" 
            font-size-adjust="0.36"
            space-before.optimum="6pt" 
            space-after.optimum="6pt" 
            space-treatment="preserve"
            linefeed-treatment="preserve"
            white-space-collapse="false"
            hyphenate="false"
            line-height="1.3"
            text-align="start"
            wrap-option="wrap">
    <xsl:if test="@role='error'">
      <xsl:attribute name="color">#C00000</xsl:attribute>
    </xsl:if>             
    <xsl:apply-templates/>
  </fo:block>
</xsl:template>

<!-- =============================================================== -->
<!-- Graphic - a block-level image.                                  -->

<xsl:template match="figure/graphic" priority="1">
   <xsl:call-template name="draw-graphic"/>
</xsl:template>

<xsl:template match="graphic">
<!--  <fo:float float="before"> -->
    <xsl:call-template name="draw-graphic"/>
<!--  </fo:float> -->
</xsl:template>

   
   
   
<xsl:template name="draw-graphic">
  <fo:block text-align="center">
    <fo:external-graphic src="url('{@source}')"
                         space-before.optimum="9pt"
                         space-after.optimum="6pt"/>
  </fo:block>
</xsl:template>



<!-- =============================================================== -->
<!-- Code Scrap.                                                     -->
<!--                                                                 -->
<!-- Coulmn width attributes (pcw1-pcw5) are ignored. Instead, the   -->
<!-- column widths are controlled by the $lhs-width/$rhs-width       -->
<!-- global parameters (see globals section in the beginning).       -->
<!-- Column widths for production number and BNF separator (::==)    -->
<!-- are fixed (since they depend mostly on the font size), and the  -->
<!-- last column (comments/constraints) absorbs the rest of the page -->
<!-- width.                                                          -->

<!-- In this version, there's no way to tweak these widths for every -->
<!-- scrap section; in our opinion, this enforce stylishness and     -->
<!-- thus can be tolerated ;-)                                       -->


<xsl:template match="scrap">
  <fo:block space-before.optimum="12pt">
    <xsl:if test="@headstyle!='suppress'">
      <fo:block xsl:use-attribute-sets="title-attrs"
                space-after.optimum="6pt">
        <xsl:apply-templates select="head"/>
      </fo:block>  
    </xsl:if>
    <fo:table border-collapse="separate"
              border-spacing="6pt 0pt"
              font-size="90%">
      <fo:table-column column-width="18pt"/>
      <fo:table-column column-width="{$lhs-width}"/>
      <fo:table-column column-width="18pt"/>
      <fo:table-column column-width="{$rhs-width}"/>

      <fo:table-body>
        <xsl:apply-templates select="prodgroup|prodrecap|prod|bnf"/>
      </fo:table-body>

    </fo:table>
  </fo:block>  
</xsl:template>


<!-- =============================================================== -->
<!-- Since we ignore pcw* attributes, there's no special processing  -->
<!-- of production groups; we pass immediately to single productions -->

<xsl:template match="scrap/prodgroup">
  <xsl:apply-templates select="prod"/>
</xsl:template>

<!-- =============================================================== -->
<!-- Prodrecap finds the production and redraws it without number    -->

<xsl:template match="prodrecap">
  <xsl:apply-templates select="key('prod-id', @ref)">
    <xsl:with-param name="recap">true</xsl:with-param>
  </xsl:apply-templates> 
</xsl:template>

<!-- =============================================================== -->
<!-- BNF produces just a block of preformatted text                  -->

<xsl:template match="bnf">
  <fo:table-row>
    <fo:table-cell number-columns-spanned="5">
      <fo:block font-size="smaller"
                font-family="monospace"
                text-align="start"
                space-before.optimum="6pt" 
                space-after.optimum="6pt" 
                space-treatment="preserve"
                linefeed-treatment="preserve"
                white-space-collapse="false"
                wrap-option="wrap">
        <xsl:apply-templates/>
      </fo:block>
    </fo:table-cell>
  </fo:table-row>
</xsl:template>

<!-- =============================================================== -->
<!-- Real fun starts here.                                           -->

<xsl:template match="prod">
  <xsl:param name="recap">false</xsl:param>

  <fo:table-row>
    <xsl:if test="$recap='false'">
      <xsl:attribute name="id">
        <xsl:value-of select="generate-id()"/>
      </xsl:attribute>
    </xsl:if>
  
    <fo:table-cell number-rows-spanned="{count(rhs)}">
      <!-- Put a number in brackets unless it's a prodrecap -->
      <fo:block text-align="start">
        <xsl:if test="$recap='false'">
          <xsl:call-template name="production-counter"/>
        </xsl:if>
      </fo:block>
    </fo:table-cell>

    <fo:table-cell number-rows-spanned="{count(rhs)}">
      <!-- Second column: left-hand side. Width = $lhs-width -->
      <fo:block text-align="end">
        <xsl:apply-templates select="lhs"/>
      </fo:block>
    </fo:table-cell>

    <fo:table-cell number-rows-spanned="{count(rhs)}">
      <!-- Third column: BNF neck. Width = 24pt -->
      <fo:block text-align="center" color="#A00000">
        <xsl:text>::=</xsl:text>
      </fo:block>
    </fo:table-cell>

    <!-- The first 'rhs' template completes the row -->
    <xsl:apply-templates select="rhs[1]"/>
  </fo:table-row>

  <!-- More 'rhs' elements each form a row of their own -->
  <xsl:for-each select="rhs[position()>1]">
    <fo:table-row>
      <xsl:apply-templates select="."/>
    </fo:table-row>
  </xsl:for-each>

  <!-- Spacer row -->
  <fo:table-row height="6pt">
    <fo:table-cell number-columns-spanned="5">
      <fo:block/>
    </fo:table-cell>
  </fo:table-row>

</xsl:template>


<xsl:template match="prod" mode="specref-mode">
  <fo:basic-link internal-destination="{generate-id()}"
                  color="{$href-color}">
    <xsl:call-template name="production-counter"/>
  </fo:basic-link>
</xsl:template>

<xsl:template name="production-counter">
  <xsl:text>[</xsl:text>
    <xsl:number count="//prod" level="any" format="1"/>
  <xsl:text>]</xsl:text>
</xsl:template>


<!-- =============================================================== -->
<!-- lhs: just a string wrapped into a block                         -->

<xsl:template match="lhs">
  <fo:block>
    <xsl:apply-templates/>
  </fo:block>
</xsl:template>

<!-- =============================================================== -->
<!-- rhs: the element itself is placed into the fourth column        -->
<!--      (vc|wfc|com|constraint)*  all go to the last column        -->

<xsl:template match="rhs">
  <fo:table-cell>
    <fo:block text-align="start">
      <xsl:apply-templates/>
    </fo:block>
  </fo:table-cell>

  <!-- Start enumerating (vc|wfc|com|constraint)* -->
  <fo:table-cell>
    <fo:block text-align="start">
      <xsl:for-each select="(following-sibling::*)[1][name()!='rhs']">
        <xsl:call-template name="enumerate-constraints"/>
      </xsl:for-each>
    </fo:block>
  </fo:table-cell>

</xsl:template>

<!-- =============================================================== -->
<!--    Auxiliary template: loops over (vc|wfc|com|constraint)*      -->
<!--                        intil another 'rhs' is found             -->

<xsl:template name="enumerate-constraints">

  <fo:block>
    <xsl:apply-templates select="."/>
  </fo:block>

  <!-- continue enumerating -->
  <xsl:for-each select="(following-sibling::*)[1][name()!='rhs']">
    <xsl:call-template name="enumerate-constraints"/>
  </xsl:for-each>

</xsl:template>

<!-- =============================================================== -->
<!-- VC, WFC, and constraint refer to the correspondent notes        -->

<xsl:template match="vc">
  <xsl:apply-templates select="key('vcnote-id', @ref)" mode="ref-mode"/>
</xsl:template>

<xsl:template match="wfc">
  <xsl:apply-templates select="key('wfcnote-id', @ref)" mode="ref-mode"/>
</xsl:template>

<xsl:template match="constraint">
  <xsl:apply-templates select="key('constraintnote-id', @ref)" mode="ref-mode"/>
</xsl:template>

<!-- =============================================================== -->
<!-- 'com' is embraced in comment markers and color highlighted      -->

<xsl:template match="com">
  <fo:wrapper color="#008000">
    <xsl:text>/* </xsl:text>
    <xsl:apply-templates/>
    <xsl:text> */</xsl:text>
  </fo:wrapper>
</xsl:template>

<!-- =============================================================== -->
<!-- Tables. Both 'table' and 'htable' are supported. Pixel units    -->
<!-- are converted to points (1px = 1pt). Treatment of attributes    -->
<!-- is very incomplete.                                             -->
<!-- =============================================================== -->

<xsl:template match="table|htable">

  <xsl:variable name="border-width">
    <xsl:choose>
      <xsl:when test="@border and number(@border) = 0">
        <xsl:value-of select="0"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="0.5"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:variable>

  <!-- Caption -->
  <xsl:apply-templates select="caption"/>

  <!-- Table itself -->
  <fo:table space-before.optimum="6pt" 
            space-after.optimum="6pt"
            space-after.precedence="force">

    <xsl:choose>
      <xsl:when test="@class='propindex'"/>
      <xsl:when test="parent::div2[ancestor::back]">
        <xsl:attribute name="border-top">0.25pt solid black</xsl:attribute>
        <xsl:attribute name="border-bottom">0.25pt solid black</xsl:attribute>
      </xsl:when>
      <xsl:otherwise> 
        <xsl:attribute name="border"><xsl:value-of select="concat (string($border-width), 'pt solid black')"/></xsl:attribute>
      </xsl:otherwise>
    </xsl:choose>

    <!-- Translate table attributes -->
    <xsl:if test="@cellspacing">
      <xsl:attribute name="border-collapse">separate</xsl:attribute> 
      <xsl:attribute name="border-spacing"> 
        <xsl:value-of select="number(@cellspacing)*0.5"/>
        <xsl:text>pt</xsl:text>
      </xsl:attribute>
    </xsl:if>

    <xsl:if test="@bgcolor">
      <xsl:attribute name="background-color">
        <xsl:value-of select="@bgcolor"/>
      </xsl:attribute>
    </xsl:if>

    <xsl:attribute name="text-align">
      <xsl:choose>
        <xsl:when test="not(@align)">start</xsl:when>
        <xsl:when test="@align='left'">start</xsl:when>
        <xsl:when test="@align='right'">end</xsl:when>
        <xsl:otherwise><xsl:value-of select="@align"/></xsl:otherwise>
      </xsl:choose>
    </xsl:attribute>
   
    <!-- Adjust column width for tables in XSL FO property definitions -->
    <!-- This is a FO2PDF-specific hack that compensates absence of    -->
    <!-- automatic table layout -->

    <xsl:if test="@class='prop-summary'">
      <fo:table-column column-width="1.5in"/>
    </xsl:if>

    <!-- Adjust column width for property tables in XSL FO -->
    <!-- This is again a FO2PDF-specific hack  -->

    <xsl:if test="@class='propindex'">
      <fo:table-column column-width="1.5in"/>
      <fo:table-column column-width="1.5in"/>
    </xsl:if>

    <!-- Table contents -->
    <xsl:if test="not(parent::div2[ancestor::back])">
      <xsl:apply-templates select="col|colgroup"/> <!-- XSL FO hack -->
    </xsl:if>
    <xsl:apply-templates select="thead|hthead"/>
    <xsl:apply-templates select="tfoot|htfoot"/>
    <xsl:apply-templates select="tbody|htbody"/>
  </fo:table>
</xsl:template>


<!-- =============================================================== -->
<xsl:template match="table/caption|htable/caption">
  <fo:block space-before.optimum="12pt"
            font-size="13pt"
            xsl:use-attribute-sets="title-attrs">
    <xsl:apply-templates/>
  </fo:block>
</xsl:template>

<!-- =============================================================== -->
<xsl:template match="table/col | htable/col |
                     table/colgroup/col | htable/colgroup/col">
  <fo:table-column>
    <!-- Translate column attributes -->
    <xsl:if test="@span and number(@span) != 1">
      <xsl:attribute name="number-columns-spanned">
        <xsl:value-of select="@span"/>
      </xsl:attribute>
    </xsl:if>
    <xsl:if test="@bgcolor">
      <xsl:attribute name="background-color">
        <xsl:value-of select="@bgcolor"/>
      </xsl:attribute>
    </xsl:if>
    <xsl:if test="@width">
      <xsl:attribute name="column-width">
        <xsl:value-of select="@width"/>
        <xsl:if test="not (contains(@width, '%'))">
          <xsl:text>pt</xsl:text>
        </xsl:if>
      </xsl:attribute>
    </xsl:if>
    <xsl:if test="@align">
      <xsl:attribute name="text-align">
        <xsl:choose>
          <xsl:when test="@align='left'">start</xsl:when>
          <xsl:when test="@align='right'">end</xsl:when>
          <xsl:otherwise><xsl:value-of select="@align"/></xsl:otherwise>
        </xsl:choose>
      </xsl:attribute>
    </xsl:if>
    <xsl:if test="@valign">
      <xsl:attribute name="display-align">
        <xsl:choose>
          <xsl:when test="@valign='top'">before</xsl:when>
          <xsl:when test="@valign='bottom'">after</xsl:when>
          <xsl:when test="@valign='center'">center</xsl:when>
          <xsl:otherwise>auto</xsl:otherwise>
        </xsl:choose>
      </xsl:attribute>
    </xsl:if>
  </fo:table-column>
</xsl:template>

<!-- =============================================================== -->
<!-- Temporary; to be refined                                        -->
<xsl:template match="table/colgroup|htable/colgroup">
  <xsl:apply-templates select="col"/>
</xsl:template>

<!-- =============================================================== -->
<!-- Headers/footers/tbodies are treated the same                    -->

<xsl:template match="thead | hthead">
  <fo:table-header font-weight="bold">
    <xsl:call-template name="process-row-group-attributes"/>
    <xsl:apply-templates select="tr"/>
  </fo:table-header>
</xsl:template>

<xsl:template match="tfoot | htfoot">
  <fo:table-footer font-weight="bold">
    <xsl:call-template name="process-row-group-attributes"/>
    <xsl:apply-templates select="tr"/>
  </fo:table-footer>
</xsl:template>

<xsl:template match="tbody | htbody">
  <xsl:choose>
    <xsl:when test="preceding-sibling::thead 
                 or preceding-sibling::hthead">
      <fo:table-body>
        <xsl:call-template name="process-row-group-attributes"/>
        <xsl:apply-templates select="tr"/>
      </fo:table-body>
    </xsl:when>
    <xsl:otherwise>
      <fo:table-body>
        <xsl:call-template name="process-row-group-attributes"/>
        <xsl:apply-templates select="tr"/>
      </fo:table-body>
    </xsl:otherwise>
  </xsl:choose>


</xsl:template>


<xsl:template name="process-row-group-attributes">
  <!-- Translate attributes -->
  <xsl:if test="@bgcolor">
    <xsl:attribute name="background-color">
      <xsl:value-of select="@bgcolor"/>
    </xsl:attribute>
  </xsl:if>
  <xsl:if test="@align">
    <xsl:attribute name="text-align">
      <xsl:choose>
        <xsl:when test="@align='left'">start</xsl:when>
        <xsl:when test="@align='right'">end</xsl:when>
        <xsl:otherwise><xsl:value-of select="@align"/></xsl:otherwise>
      </xsl:choose>
    </xsl:attribute>
  </xsl:if>
  <xsl:if test="@valign">
    <xsl:attribute name="display-align">
      <xsl:choose>
        <xsl:when test="@valign='top'">before</xsl:when>
        <xsl:when test="@valign='bottom'">after</xsl:when>
        <xsl:when test="@valign='center'">center</xsl:when>
        <xsl:otherwise>auto</xsl:otherwise>
      </xsl:choose>
    </xsl:attribute>
  </xsl:if>
</xsl:template>
  
<!-- =============================================================== -->
<!-- Table row                                                       -->

<xsl:template match="tr">
  <fo:table-row>
    <!-- Translate row attributes -->
    <xsl:if test="@bgcolor">
      <xsl:attribute name="background-color">
        <xsl:value-of select="@bgcolor"/>
      </xsl:attribute>
    </xsl:if>
    <xsl:if test="@align">
      <xsl:attribute name="text-align">
        <xsl:choose>
          <xsl:when test="@align='left'">start</xsl:when>
          <xsl:when test="@align='right'">end</xsl:when>
          <xsl:otherwise><xsl:value-of select="@align"/></xsl:otherwise>
        </xsl:choose>
      </xsl:attribute>
    </xsl:if>
    <xsl:if test="@valign">
      <xsl:attribute name="display-align">
        <xsl:choose>
          <xsl:when test="@valign='top'">before</xsl:when>
          <xsl:when test="@valign='bottom'">after</xsl:when>
          <xsl:when test="@valign='center'">center</xsl:when>
          <xsl:otherwise>auto</xsl:otherwise>
        </xsl:choose>
      </xsl:attribute>
    </xsl:if>

    <!-- Rows consisting entirely of TH's are treated -->
    <!-- as if they were non-repeatable headers -->
    <xsl:if test="th and not (td)"> 
      <xsl:attribute name="keep-with-next.within-column">always</xsl:attribute>
    </xsl:if>

    <xsl:apply-templates select="td|th"/>
  </fo:table-row>
</xsl:template>

<!-- =============================================================== -->
<!-- Table cell                                                      -->

<xsl:template match="tr/td|tr/th">
  <fo:table-cell>

  <!-- XSL FO hack -->
  <xsl:if test="ancestor::div2[ancestor::back] or ancestor::table[caption]">
    <xsl:attribute name="keep-together.within-column">always</xsl:attribute> 
    <xsl:choose>
      <xsl:when test="self::td[ancestor::tbody]">
        <xsl:attribute name="font-size">9pt</xsl:attribute>
      </xsl:when>
      <xsl:otherwise>
        <xsl:attribute name="font-size">10pt</xsl:attribute> 
        <xsl:attribute name="background-color">#e0e0e0</xsl:attribute>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:if>

  <xsl:choose>
    <xsl:when test="self::td[ancestor::tbody]">
      <xsl:attribute name="padding">2pt</xsl:attribute>
    </xsl:when>
    <xsl:otherwise>
      <xsl:attribute name="padding">4pt</xsl:attribute>
    </xsl:otherwise>
  </xsl:choose>

  <!-- Translate cell attributes -->
    <xsl:if test="@colspan and number(@colspan) != 1">
      <xsl:attribute name="number-columns-spanned">
        <xsl:value-of select="@colspan"/>
      </xsl:attribute>
    </xsl:if>
    <xsl:if test="@rowspan and number(@rowspan) != 1">
      <xsl:attribute name="number-rows-spanned">
        <xsl:value-of select="@rowspan"/>
      </xsl:attribute>
    </xsl:if>
    <xsl:if test="@bgcolor">
      <xsl:attribute name="background-color">
        <xsl:value-of select="@bgcolor"/>
      </xsl:attribute>
    </xsl:if>

    <xsl:choose>
      <xsl:when test="self::th">
        <xsl:attribute name="text-align">center</xsl:attribute>
      </xsl:when>
      <xsl:when test="@align">
        <xsl:attribute name="text-align">
          <xsl:choose>
            <xsl:when test="@align='left'">start</xsl:when>
            <xsl:when test="@align='right'">end</xsl:when>
            <xsl:otherwise><xsl:value-of select="@align"/></xsl:otherwise>
          </xsl:choose>
        </xsl:attribute>
      </xsl:when>
    </xsl:choose>

    <xsl:if test="@valign">
      <xsl:attribute name="display-align">
        <xsl:choose>
          <xsl:when test="@valign='top'">before</xsl:when>
          <xsl:when test="@valign='bottom'">after</xsl:when>
          <xsl:when test="@valign='center'">center</xsl:when>
          <xsl:otherwise>auto</xsl:otherwise>
        </xsl:choose>
      </xsl:attribute>
    </xsl:if>

    <xsl:variable name="border-width">
      <xsl:choose>
        <xsl:when test="@border and number(@border)=0">
          <xsl:value-of select="0"/>
        </xsl:when>
        <xsl:when test="../@border and number(../@border)=0">
          <xsl:value-of select="0"/>
        </xsl:when>
        <xsl:when test="../../@border and number(../../@border)=0">
          <xsl:value-of select="0"/>
        </xsl:when>
        <xsl:when test="../../../@border and number(../../../@border)=0">
          <xsl:value-of select="0"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="0.5"/>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>

    <xsl:variable name="border-value"
          select="concat(string($border-width), 'pt solid black')"/>

    <xsl:choose>
      <xsl:when test="ancestor::table[@cellpadding != 0]">
        <xsl:attribute name="border"><xsl:value-of select="$border-value"/></xsl:attribute>
      </xsl:when>
      <xsl:otherwise>
        <xsl:choose>

          <xsl:when test="ancestor::div2[ancestor::back] 
                  and not (ancestor::table[thead])">
            <xsl:attribute name="border-top">0.25pt solid black</xsl:attribute>
            <xsl:attribute name="border-bottom">0.25pt solid black</xsl:attribute>
          </xsl:when>
          <xsl:otherwise>
            <xsl:attribute name="border-bottom"><xsl:value-of select="$border-value"/></xsl:attribute>
          </xsl:otherwise>
        </xsl:choose>

        <xsl:attribute name="border-right"><xsl:value-of select="$border-value"/></xsl:attribute>
        <xsl:attribute name="border-left"><xsl:value-of select="$border-value"/></xsl:attribute>

        <xsl:if test="not(../preceding-sibling::tr) 
                 and not (../../preceding-sibling::thead or ../../preceding-sibling::hthead)">
           <xsl:attribute name="border-top"><xsl:value-of select="$border-value"/></xsl:attribute>
        </xsl:if>      
      </xsl:otherwise>
    </xsl:choose>

    <fo:block>
      <xsl:if test="self::th">
        <xsl:attribute name="font-weight">bold</xsl:attribute>
      </xsl:if>
      <xsl:apply-templates/>
    </fo:block>
  </fo:table-cell>
  <xsl:text>&#xA;</xsl:text>
</xsl:template>


<!-- =============================================================== -->
<!-- IDL Definitions. These are not properly documented in the       -->
<!-- description, and no XML source for DOM spec is publicly         -->
<!-- avaliable. Therefore, the corresponding part has been skipped.  -->
<!-- =============================================================== -->

<xsl:template match="definitions"/>

<!-- =============================================================== -->
<!-- Phrase-level elements.                                          -->
<!-- =============================================================== -->

<!-- =============================================================== -->
<!-- Footnote                                                        -->

<xsl:template match="footnote">
  <fo:footnote>
    <fo:inline baseline-shift="super" font-size="smaller">
      <xsl:number count="//footnote" level="any" format="(1)"/>
    </fo:inline>
    <fo:footnote-body>
      <fo:list-block provisional-distance-between-starts="24pt"
                     provisional-label-separation="0pt"
                     space-after.optimum="6pt">
        <fo:list-item>
          <fo:list-item-label end-indent="label-end()">
            <fo:block line-height-shift-adjustment="disregard-shifts">
              <fo:inline baseline-shift="super"
                                font-size="smaller">
                <xsl:number count="//footnote" level="any" format="(1)"/>
              </fo:inline>
            </fo:block>
          </fo:list-item-label>

          <fo:list-item-body start-indent="body-start()">
            <fo:block line-height-shift-adjustment="disregard-shifts">
              <xsl:apply-templates/>
            </fo:block>
          </fo:list-item-body>
        </fo:list-item>        
      </fo:list-block>
    </fo:footnote-body>
  </fo:footnote>
</xsl:template>
 

<!-- =============================================================== -->
<!-- Term                                                            -->

<xsl:template match="term">
  <fo:wrapper font-style="italic"><xsl:apply-templates/></fo:wrapper>
</xsl:template>

<!-- =============================================================== -->
<!-- Trait name (XSL FO only)                                        -->

<xsl:template match="trait">
  <fo:wrapper font-style="italic"><xsl:apply-templates/></fo:wrapper>
</xsl:template>


<!-- =============================================================== -->
<!-- Term definition. In reference mode, the text is taken from      -->
<!-- an external parameter; if the parameter is empty, then a @term  -->
<!-- is inserted                                                     -->

<xsl:template match="termdef">
  <fo:wrapper id="{generate-id()}"><xsl:apply-templates/></fo:wrapper>
</xsl:template>

<xsl:template match="termdef" mode="ref-mode">
  <xsl:param name="ref-text"/>

  <fo:basic-link internal-destination="{generate-id()}"
                  color="{$href-color}">
    <xsl:choose>
      <xsl:when test="string-length($ref-text)=0">
        <xsl:value-of select="@term"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:copy-of select="$ref-text"/>
      </xsl:otherwise>
    </xsl:choose>
  </fo:basic-link>
</xsl:template>

<!-- =============================================================== -->
<!-- Emphasized text                                                 -->

<xsl:template match="emph">
  <fo:wrapper font-style="italic"><xsl:apply-templates/></fo:wrapper>
</xsl:template>


<!-- =============================================================== -->
<!-- Quoted text                                                     -->

<xsl:template match="quote">
  <xsl:text>&quotedblleft;</xsl:text>
  <xsl:apply-templates/>
  <xsl:text>&quotedblright;</xsl:text>
</xsl:template>

<!-- *************************************************************** -->
<!-- Internal and external links                                     -->
<!-- *************************************************************** -->

<!-- =============================================================== -->
<!-- External links                                                  -->
<!-- =============================================================== -->

<xsl:template match="xnt|xspecref">
  <fo:basic-link external-destination="url('{@href}')"
                  xsl:use-attribute-sets="href-attrs">
    <xsl:apply-templates/>
  </fo:basic-link>
</xsl:template>


<xsl:template match="loc">
  <fo:basic-link color="{$href-color}">
    <xsl:choose>
      <xsl:when test="substring(@href, 1, 1) = '#'">
        <xsl:variable name="destination"
                      select="key('generic-id', substring(@href, 2))"/>
        <xsl:if test="$destination">
          <xsl:attribute name="internal-destination">
            <xsl:value-of select="generate-id($destination)"/>
          </xsl:attribute>
        </xsl:if>
      </xsl:when>
      <xsl:otherwise>
        <xsl:attribute name="external-destination">
          <xsl:text>url('</xsl:text>
          <xsl:value-of select="@href"/>
          <xsl:text>')</xsl:text>
        </xsl:attribute>
        <xsl:attribute name="text-decoration">underline</xsl:attribute>
      </xsl:otherwise>
    </xsl:choose>
                  
    <xsl:apply-templates/>
  </fo:basic-link>
</xsl:template>


<!-- Special case - links to errata in XML Second Edition. -->
<!-- In this version, they are suppressed; to enable them, -->
<!-- decrease the priority of the first template and let   -->
<!-- the second template fire.                             -->

<xsl:template match="loc[@role='erratumref']" priority="3"/>

<xsl:template match="loc[@role='erratumref']" priority="2">
  <fo:basic-link color="white" background-color="{$href-color}"
                 baseline-shift="0.15em" font="bold 70% Times"
                 padding="0pt 1pt" border="1pt white solid"
                 external-destination="url('{@href}')">
    <xsl:value-of select="translate(., '[]', '')"/>
  </fo:basic-link>
</xsl:template>

<xsl:template match="titleref">
  <fo:basic-link font-style="italic"
                 color="{$href-color}">
    <xsl:variable name="destination" select="key('generic-id', translate(@href, '#', ''))"/>
    <xsl:choose>
      <xsl:when test="$destination">
        <xsl:attribute name="internal-destination">
          <xsl:value-of select="generate-id($destination)"/>
        </xsl:attribute>
      </xsl:when>
      <xsl:otherwise>
        <xsl:attribute name="external-destination">
          <xsl:text>url('</xsl:text>
          <xsl:value-of select="@href"/>
          <xsl:text>')</xsl:text>
        </xsl:attribute>
        <xsl:attribute name="text-decoration">underline</xsl:attribute>
      </xsl:otherwise>
    </xsl:choose>
                  
    <xsl:apply-templates/>
  </fo:basic-link>
</xsl:template>

<xsl:template match="email">
  <fo:wrapper color="blue">
    &lt;<fo:basic-link external-destination="url('{@href}')" 
                       xsl:use-attribute-sets="href-attrs">
          <xsl:apply-templates/>
        </fo:basic-link>&gt;
  </fo:wrapper>
</xsl:template>


<!-- =============================================================== -->
<!-- Reference elements                                              -->
<!-- =============================================================== -->

<!-- =============================================================== -->
<!-- Reference to the bibliographical entry                          -->

<xsl:template match="bibref">
  <xsl:apply-templates select="key('bibl-id', @ref)" mode="ref-mode"/>
</xsl:template>


<!-- =============================================================== -->
<!-- Term reference (see termdef). This may have #PCDATA contents.   -->

<xsl:template match="termref">
  <xsl:apply-templates select="key('termdef-id', @def)" mode="ref-mode">
    <xsl:with-param name="ref-text">
      <xsl:apply-templates/>  <!-- pass current #PCDATA as parameter -->
    </xsl:with-param>
  </xsl:apply-templates>
</xsl:template>


<!-- =============================================================== -->
<!-- Reference to a location of the current spec. In order to work   -->
<!-- properly, the referenced element should have an appropriate     -->
<!-- mode="specref-mode" template defined.                           -->

<xsl:template match="specref">
  <xsl:apply-templates select="key('generic-id', @ref)" mode="specref-mode"/>
</xsl:template>

<!-- =============================================================== -->
<!-- Additional modes for specref, used in XSL FO                    -->

<xsl:template match="ulist/item/p/specref[normalize-space(..) = normalize-space(.)] |
                     sitem/specref[starts-with(normalize-space(..), normalize-space(.))]" priority="2">
  <xsl:apply-templates select="key('generic-id', @ref)" mode="property-list-mode"/>
</xsl:template>


<xsl:template match="specref [ancestor::table/@class='propindex']" priority="2">
  <xsl:apply-templates select="key('generic-id', @ref)" mode="table-mode"/>
</xsl:template>


<!-- *************************************************************** -->
<!-- Technical markup                                                -->
<!-- *************************************************************** -->

<!-- Code sample -->
<xsl:template match="code|kw">
  <fo:wrapper font-family="Courier" font-size-adjust="0.42">
    <xsl:apply-templates/>
  </fo:wrapper>
</xsl:template>

<!-- Trait value -->
<xsl:template match="code[@role='value']" priority="1">
  <fo:wrapper font-style="italic" font-weight="bold">
    <xsl:apply-templates/>
  </fo:wrapper>
</xsl:template>


<!-- =============================================================== -->
<!-- Nonterminal -->

<xsl:template match="nt">
  <xsl:variable name="nttext" select="normalize-space(text())"/>

  <xsl:for-each select="key('prod-id', @def)">
    <fo:basic-link internal-destination="{generate-id()}" 
                    font-weight="bold"
                    color="{$href-color}">
      <xsl:value-of select="$nttext"/>
    </fo:basic-link>
  </xsl:for-each>

</xsl:template>

<!-- =============================================================== -->
<!-- Ednote          -->

<xsl:template match="ednote">
  <xsl:variable name="note-type">
    <xsl:text>Editor Note </xsl:text>
    <xsl:apply-templates select="name"/>
    <xsl:apply-templates select="date"/>
    <xsl:text>: </xsl:text>
  </xsl:variable>

  <xsl:for-each select="edtext">
    <xsl:call-template name="generic-note">
      <xsl:with-param name="note-type" select="$note-type"/>
    </xsl:call-template>
  </xsl:for-each>

</xsl:template>


<xsl:template match="ednote/name">
  <xsl:text>(</xsl:text>
  <xsl:apply-templates/>
  <xsl:choose>
    <xsl:when test="../date">
      <xsl:text>, </xsl:text>
    </xsl:when>
    <xsl:otherwise>
      <xsl:text>)</xsl:text>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>

<xsl:template match="ednote/date">
  <xsl:choose>
    <xsl:when test="../name"/>
    <xsl:otherwise>
      <xsl:text>(</xsl:text>
    </xsl:otherwise>
  </xsl:choose>
  <xsl:apply-templates/>
  <xsl:text>)</xsl:text>
</xsl:template>


<!-- ****************************************************** -->
<!--                                                        -->
<!-- Document structure elements (divisions)                -->
<!--                                                        -->
<!-- ****************************************************** -->


<xsl:template match="front|body|back">
  <xsl:apply-templates/>
</xsl:template>

<!-- =============================================================== -->
<!-- Division number   -->

<xsl:template name="head-number">
  <xsl:variable name="front" select="count(ancestor::front)"/>
  <xsl:variable name="body" select="count(ancestor::body)"/>
  <xsl:variable name="back" select="count(ancestor::back)"/>

  <xsl:variable name="number-format">
    <xsl:choose>
      <xsl:when test="$body=1">1.1.1.1</xsl:when>
      <xsl:otherwise>A.1.1.1</xsl:otherwise>
    </xsl:choose>   
  </xsl:variable>

  <xsl:number level="multiple" 
              count="div1|inform-div1|div2|div3|div4|div5" 
              format="{$number-format}"/>
</xsl:template>

<!-- =============================================================== -->
<!-- Numbered division name   -->

<xsl:template name="numbered-head-text">
  <xsl:call-template name="head-number"/>
  <xsl:text>. </xsl:text>
  <xsl:apply-templates select="head"/>
</xsl:template>

<!-- =============================================================== -->
<!-- Marker mode   -->
<xsl:template match="*" mode="marker-mode" priority="-1"/>

<xsl:template match="div1/head | inform-div1/head" mode="marker-mode">
  <fo:marker marker-class-name="div1">
    <fo:wrapper font="bold 10pt Times"><xsl:apply-templates/></fo:wrapper>
  </fo:marker>
  <fo:marker marker-class-name="div2">
    <fo:wrapper font="bold 10pt Times"><xsl:apply-templates/></fo:wrapper>
  </fo:marker>
</xsl:template>
  
<xsl:template match="div2/head | inform-div2/head" mode="marker-mode">
  <fo:marker marker-class-name="div2">
    <fo:wrapper font="bold 10pt Times"><xsl:apply-templates/></fo:wrapper>
  </fo:marker>
</xsl:template>
  
<!-- =============================================================== -->
<!-- Division title, properly numbered, sized and spaced   -->

<xsl:template name="div-title">
  <xsl:variable name="level" select="count(ancestor-or-self::div1 |
                                           ancestor-or-self::inform-div1 |
                                           ancestor-or-self::div2 |
                                           ancestor-or-self::div3 |
                                           ancestor-or-self::div4 |
                                           ancestor-or-self::div5)"/>
  <xsl:apply-templates select="head" mode="marker-mode"/>
  <fo:block xsl:use-attribute-sets="title-attrs">
    <xsl:attribute name="font-size">
      <xsl:choose>
        <xsl:when test="$level=1">18pt</xsl:when>
        <xsl:when test="$level=2">14pt</xsl:when>
        <xsl:when test="$level=3">12pt</xsl:when>
        <xsl:otherwise>11pt</xsl:otherwise>
      </xsl:choose>
    </xsl:attribute>
 
    <!-- If the division follows the head of the parent division, -->
    <!-- the space before it is reduced to 6pt.                   -->
    <xsl:attribute name="space-before.optimum">
      <xsl:choose>
        <xsl:when test="preceding-sibling::head">6pt</xsl:when>
        <xsl:when test="$level=1">24pt</xsl:when>
        <xsl:when test="$level=2">18pt</xsl:when>
        <xsl:when test="$level=3">12pt</xsl:when>
        <xsl:otherwise>9pt</xsl:otherwise>
      </xsl:choose>
    </xsl:attribute>

    <xsl:if test="$level=1">
      <xsl:attribute name="space-before.conditionality">retain</xsl:attribute>
      <xsl:if test="parent::back">
        <xsl:text>Appendix </xsl:text>
      </xsl:if>
    </xsl:if>

    <xsl:call-template name="numbered-head-text"/>

    <xsl:if test="self::inform-div1">
      <xsl:text> (Non-Normative)</xsl:text>
    </xsl:if>

  </fo:block>
</xsl:template>

<!-- =============================================================== -->
<!-- Divisions -->

<xsl:template match="div1|inform-div1|div2|div3|div4|div5">

  <fo:block id="{generate-id()}" text-align="justify">
    <xsl:call-template name="div-title"/>
    <xsl:apply-templates select="*[not(self::head)]"/>
  </fo:block> 

</xsl:template>

<!-- Division reference in specref inside text -->
<xsl:template match="div1|inform-div1|div2|div3|div4|div5" 
              mode="specref-mode">
  <xsl:variable name="level" select="count(ancestor-or-self::div1 |
                                           ancestor-or-self::inform-div1 |
                                           ancestor-or-self::div2 |
                                           ancestor-or-self::div3 |
                                           ancestor-or-self::div4 |
                                           ancestor-or-self::div5)"/>

  <fo:basic-link internal-destination="{generate-id()}"
                  color="{$href-color}">
    <fo:inline keep-together.within-line="always">
      <xsl:choose>
        <xsl:when test="ancestor::back">
          <xsl:text>Appendix </xsl:text>
        </xsl:when>
        <xsl:when test="ancestor::front">
          <xsl:text>Preface </xsl:text>
        </xsl:when>
        <xsl:otherwise>  
          <xsl:text>&section; </xsl:text>
        </xsl:otherwise>  
      </xsl:choose>
      <xsl:call-template name="head-number"/>

      <xsl:text> &endash;</xsl:text>
      </fo:inline>  
    <xsl:text> </xsl:text>
    <xsl:apply-templates select="head"/>
  </fo:basic-link>

  <xsl:text> on page </xsl:text>
  <fo:page-number-citation ref-id="{generate-id()}"/>

</xsl:template>


<!-- Division reference in specref in the property list  -->
<xsl:template match="div1|inform-div1|div2|div3|div4|div5" 
              mode="property-list-mode">
  <xsl:variable name="level" select="count(ancestor-or-self::div1 |
                                           ancestor-or-self::inform-div1 |
                                           ancestor-or-self::div2 |
                                           ancestor-or-self::div3 |
                                           ancestor-or-self::div4 |
                                           ancestor-or-self::div5)"/>

  <fo:basic-link internal-destination="{generate-id()}"
                  color="{$href-color}">
    <xsl:apply-templates select="head"/>
  </fo:basic-link>

  <xsl:text> &emdash; </xsl:text>
  <xsl:choose>
    <xsl:when test="ancestor::back">
      <xsl:text>Appendix </xsl:text>
    </xsl:when>
    <xsl:when test="ancestor::front">
      <xsl:text>Preface </xsl:text>
    </xsl:when>
    <xsl:otherwise>  
      <xsl:text>&section; </xsl:text>
    </xsl:otherwise>  
  </xsl:choose>
  <xsl:call-template name="head-number"/>

  <xsl:text> on page </xsl:text>
  <fo:page-number-citation ref-id="{generate-id()}"/>

</xsl:template>


<!-- Division reference inside property table -->
<!-- Just property name, no indices (there's too few space -->
<xsl:template match="div1|inform-div1|div2|div3|div4|div5" 
              mode="table-mode">
  <fo:basic-link internal-destination="{generate-id()}"
                  color="{$href-color}">
    <xsl:apply-templates select="head"/>
  </fo:basic-link>
</xsl:template>


<!-- Division reference in TOC -->
<xsl:template match="div1|inform-div1|div2|div3|div4|div5" 
              mode="toc-mode">
  <xsl:variable name="level" select="count(ancestor-or-self::div1 |
                                           ancestor-or-self::inform-div1 |
                                           ancestor-or-self::div2 |
                                           ancestor-or-self::div3 |
                                           ancestor-or-self::div4 |
                                           ancestor-or-self::div5)"/>

  <fo:block end-indent="0.5in" last-line-end-indent="-0.5in"
            text-align-last="justify">
    <xsl:attribute name="margin-left">
      <xsl:choose>
        <xsl:when test="$level=1">0pt</xsl:when>
        <xsl:when test="$level=2">18pt</xsl:when>
        <xsl:when test="$level=3">36pt</xsl:when>
        <xsl:when test="$level=4">54pt</xsl:when>
        <xsl:when test="$level=5">72pt</xsl:when>
        <xsl:otherwise>90pt</xsl:otherwise>
      </xsl:choose>
    </xsl:attribute>

    <xsl:if test="$level=1">
      <xsl:attribute name="font-weight">bold</xsl:attribute>
      <xsl:attribute name="font-size">11.5pt</xsl:attribute>
    </xsl:if>

    <xsl:attribute name="space-before.optimum">
      <xsl:choose>
        <xsl:when test="$level=1">9pt</xsl:when>
        <xsl:when test="$level=2">4pt</xsl:when>
        <xsl:when test="$level=3">2pt</xsl:when>
        <xsl:otherwise>0pt</xsl:otherwise>
      </xsl:choose>
    </xsl:attribute>

    <xsl:call-template name="head-number"/>
    <xsl:text>. </xsl:text>

    <fo:basic-link internal-destination="{generate-id()}"
                   color="{$href-color}">
      <xsl:apply-templates select="head"/>
      <xsl:if test="self::inform-div1">
        <xsl:text> (Non-Normative)</xsl:text>
      </xsl:if>
    </fo:basic-link>
    <xsl:text> </xsl:text>

    <fo:inline keep-together.within-line="always">
      <fo:leader leader-pattern="dots"/>
      <xsl:text> </xsl:text>
      <fo:page-number-citation ref-id="{generate-id()}"/>
    </fo:inline>
    
  </fo:block>
</xsl:template>


<!-- *************************************************************** -->
<!-- Table of Contents                                               -->
<!-- *************************************************************** -->

<xsl:template name="toc">
  <fo:block space-before.optimum="18pt" space-after.optimum="6pt"
            space-before.conditionality="retain">
    <fo:block font-size="18pt"
              xsl:use-attribute-sets="title-attrs"
              space-after.optimum="6pt">
      Table of Contents
    </fo:block>

    <xsl:if test="front">
      <fo:block font-size="15pt"
                xsl:use-attribute-sets="title-attrs"
                space-before.optimum="6pt">
        Preface
      </fo:block>
      <xsl:for-each select="front//div1 | front//div2 |
                            front//div3 | front//div4 |
                            front//div5">
        <xsl:apply-templates select="." mode="toc-mode"/>
      </xsl:for-each>
    </xsl:if>

    <xsl:for-each select="body//div1 | body//div2 |
                          body//div3 | body//div4 |
                          body//div5">
      <xsl:apply-templates select="." mode="toc-mode"/>
    </xsl:for-each>

    <xsl:if test="back">
      <fo:block font-size="14pt"
                xsl:use-attribute-sets="title-attrs"
                space-before.optimum="12pt">
        Appendices
      </fo:block>
      <xsl:for-each select="back//div1 | back//inform-div1 |
                            back//div2 | back//div3 |
                            back//div4 | back//div5">
        <xsl:apply-templates select="." mode="toc-mode"/>
      </xsl:for-each>
    </xsl:if>
  </fo:block>
</xsl:template>


<!-- *************************************************************** -->
<!-- XSLT/XPath Extensions to the XMLspec                            -->
<!-- *************************************************************** -->

<!-- XPath function prototype -->

<xsl:template match="proto">
  <fo:block space-after.optimum="6pt" 
            id="{generate-id()}"
            keep-with-next.within-column="always">

    <fo:wrapper font-weight="bold">
      <xsl:text>Function: </xsl:text>
    </fo:wrapper>

    <fo:wrapper font-family="Helvetica" font-size-adjust="0.46">

      <fo:wrapper font-style="italic">
        <xsl:value-of select="@return-type"/>
      </fo:wrapper>

      <xsl:text> </xsl:text>
 
      <fo:wrapper font-weight="bold">
        <xsl:value-of select="@name"/>
      </fo:wrapper>

      <xsl:text>(</xsl:text>
      <fo:wrapper font-style="italic">
        <xsl:apply-templates select="arg"/>
      </fo:wrapper>
      <xsl:text>)</xsl:text>

    </fo:wrapper>

  </fo:block>

</xsl:template>


<xsl:template match="proto" mode="ref-mode">
  <fo:basic-link font-weight="bold"
                 font-family="Helvetica"
                 font-size-adjust="0.46"
                 internal-destination="{generate-id()}"
                 color="{$href-color}">
    <xsl:value-of select="@name"/>
  </fo:basic-link>
</xsl:template>


<!-- =============================================================== -->
<!-- Prototype argument list -->

<xsl:template match="proto/arg">

    <xsl:value-of select="@type"/>
    <xsl:if test="@occur='opt'">
      <xsl:text>?</xsl:text>
    </xsl:if>
    <xsl:if test="position() != last()">
      <xsl:text>, </xsl:text>
    </xsl:if>

</xsl:template>

<!-- =============================================================== -->
<!-- Reference to a <proto> -->
<xsl:template match="function">
  <xsl:variable name="nameref" select="normalize-space(.)"/>
  <xsl:apply-templates select="key('proto-name', $nameref)" mode="ref-mode"/>
</xsl:template>


<!-- =============================================================== -->
<!-- Reference to an external <proto> (XSLT only) -->

<xsl:template match="xfunction">

  <xsl:variable name="href">
    <xsl:text>http://www.w3c.org/TR/xpath#function-</xsl:text>
    <xsl:value-of select="text()"/>
  </xsl:variable>

  <fo:basic-link external-destination="url('{$href}')"
                  font-family="Helvetica"
                  font-size-adjust="0.46"
                  font-weight="bold"
                  xsl:use-attribute-sets="href-attrs">
    <xsl:value-of select="text()"/>
  </fo:basic-link>

</xsl:template>


<!-- =============================================================== -->
<!-- Namespace Constraint (XMLnames only)                            -->

<xsl:template match="nscnote">
  <xsl:call-template name="constraint-note">
    <xsl:with-param name="note-type">Namespace Constraint</xsl:with-param>
  </xsl:call-template>
</xsl:template>


<xsl:template match="nscnote" mode="ref-mode">
  [<xsl:call-template name="constraint-note-reference">
    <xsl:with-param name="note-type">NSC</xsl:with-param>
  </xsl:call-template>]
</xsl:template>

<!-- =============================================================== -->
<!-- Figure - includes a graphic and a caption (XSL FO only)         -->

<xsl:template match="figure">
<!--  <fo:float float="before"> -->
    <fo:block space-after.optimum="6pt">
      <xsl:apply-templates select="graphic"/>
      <xsl:apply-templates select="*[not(self::graphic)]"/>
    </fo:block>
<!--  </fo:float> -->
</xsl:template>

<!-- Figure Caption -->
<!-- Treated very inconsistently in XSL FO spec -->

<xsl:template match="figcap">
  <fo:block>
    <xsl:if test="p[1][string-length(.) &lt; 80]">
      <fo:block text-align="center" font-weight="bold">
        <xsl:apply-templates select="p[1]"/>
      </fo:block>
    </xsl:if>
    <xsl:apply-templates select="p[preceding-sibling::p] 
                               | p[string-length(.) &gt; 79]"/>
  </fo:block>
</xsl:template>

<!-- =============================================================== -->
<!-- Variable name (XSL FO only)                                     -->

<xsl:template match="var">
  <fo:wrapper font-style="italic"><xsl:apply-templates/></fo:wrapper>
</xsl:template>

<!-- =============================================================== -->
<!-- Subscripts/superscripts (XSL FO only)                           -->

<xsl:template match="sub">
  <fo:inline font-size="75%" baseline-shift="sub"><xsl:apply-templates/></fo:inline>
</xsl:template>

<xsl:template match="sup">
  <fo:inline font-size="75%" baseline-shift="super"><xsl:apply-templates/></fo:inline>
</xsl:template>

<!-- =============================================================== -->
<!-- Character entities (XSL FO only)                                -->

<!-- Latin-1 character set -->

<xsl:template match="entity[@name='nbsp']">&#160;</xsl:template>
<xsl:template match="entity[@name='iexcl']">&#161;</xsl:template>
<xsl:template match="entity[@name='cent']">&#162;</xsl:template>
<xsl:template match="entity[@name='pound']">&#163;</xsl:template>
<xsl:template match="entity[@name='curren']">&#164;</xsl:template>
<xsl:template match="entity[@name='yen']">&#165;</xsl:template>
<xsl:template match="entity[@name='brvbar']">&#166;</xsl:template>
<xsl:template match="entity[@name='sect']">&#167;</xsl:template>
<xsl:template match="entity[@name='uml']">&#168;</xsl:template>
<xsl:template match="entity[@name='copy']">&#169;</xsl:template>
<xsl:template match="entity[@name='ordf']">&#170;</xsl:template>
<xsl:template match="entity[@name='laquo']">&#171;</xsl:template>
<xsl:template match="entity[@name='not']">&#172;</xsl:template>
<xsl:template match="entity[@name='shy']">&#173;</xsl:template>
<xsl:template match="entity[@name='reg']">&#174;</xsl:template>
<xsl:template match="entity[@name='macr']">&#175;</xsl:template>
<xsl:template match="entity[@name='deg']">&#176;</xsl:template>
<xsl:template match="entity[@name='plusmn']">&#177;</xsl:template>
<xsl:template match="entity[@name='sup2']">&#178;</xsl:template>
<xsl:template match="entity[@name='sup3']">&#179;</xsl:template>
<xsl:template match="entity[@name='acute']">&#180;</xsl:template>
<xsl:template match="entity[@name='micro']">&#181;</xsl:template>
<xsl:template match="entity[@name='para']">&#182;</xsl:template>
<xsl:template match="entity[@name='middot']">&#183;</xsl:template>
<xsl:template match="entity[@name='cedil']">&#184;</xsl:template>
<xsl:template match="entity[@name='sup1']">&#185;</xsl:template>
<xsl:template match="entity[@name='ordm']">&#186;</xsl:template>
<xsl:template match="entity[@name='raquo']">&#187;</xsl:template>
<xsl:template match="entity[@name='frac14']">&#188;</xsl:template>
<xsl:template match="entity[@name='frac12']">&#189;</xsl:template>
<xsl:template match="entity[@name='frac34']">&#190;</xsl:template>
<xsl:template match="entity[@name='iquest']">&#191;</xsl:template>
<xsl:template match="entity[@name='Agrave']">&#192;</xsl:template>
<xsl:template match="entity[@name='Aacute']">&#193;</xsl:template>
<xsl:template match="entity[@name='Acirc']">&#194;</xsl:template>
<xsl:template match="entity[@name='Atilde']">&#195;</xsl:template>
<xsl:template match="entity[@name='Auml']">&#196;</xsl:template>
<xsl:template match="entity[@name='Aring']">&#197;</xsl:template>
<xsl:template match="entity[@name='AElig']">&#198;</xsl:template>
<xsl:template match="entity[@name='Ccedil']">&#199;</xsl:template>
<xsl:template match="entity[@name='Egrave']">&#200;</xsl:template>
<xsl:template match="entity[@name='Eacute']">&#201;</xsl:template>
<xsl:template match="entity[@name='Ecirc']">&#202;</xsl:template>
<xsl:template match="entity[@name='Euml']">&#203;</xsl:template>
<xsl:template match="entity[@name='Igrave']">&#204;</xsl:template>
<xsl:template match="entity[@name='Iacute']">&#205;</xsl:template>
<xsl:template match="entity[@name='Icirc']">&#206;</xsl:template>
<xsl:template match="entity[@name='Iuml']">&#207;</xsl:template>
<xsl:template match="entity[@name='ETH']">&#208;</xsl:template>
<xsl:template match="entity[@name='Ntilde']">&#209;</xsl:template>
<xsl:template match="entity[@name='Ograve']">&#210;</xsl:template>
<xsl:template match="entity[@name='Oacute']">&#211;</xsl:template>
<xsl:template match="entity[@name='Ocirc']">&#212;</xsl:template>
<xsl:template match="entity[@name='Otilde']">&#213;</xsl:template>
<xsl:template match="entity[@name='Ouml']">&#214;</xsl:template>
<xsl:template match="entity[@name='times']">&#215;</xsl:template>
<xsl:template match="entity[@name='Oslash']">&#216;</xsl:template>
<xsl:template match="entity[@name='Ugrave']">&#217;</xsl:template>
<xsl:template match="entity[@name='Uacute']">&#218;</xsl:template>
<xsl:template match="entity[@name='Ucirc']">&#219;</xsl:template>
<xsl:template match="entity[@name='Uuml']">&#220;</xsl:template>
<xsl:template match="entity[@name='Yacute']">&#221;</xsl:template>
<xsl:template match="entity[@name='THORN']">&#222;</xsl:template>
<xsl:template match="entity[@name='szlig']">&#223;</xsl:template>
<xsl:template match="entity[@name='agrave']">&#224;</xsl:template>
<xsl:template match="entity[@name='aacute']">&#225;</xsl:template>
<xsl:template match="entity[@name='acirc']">&#226;</xsl:template>
<xsl:template match="entity[@name='atilde']">&#227;</xsl:template>
<xsl:template match="entity[@name='auml']">&#228;</xsl:template>
<xsl:template match="entity[@name='aring']">&#229;</xsl:template>
<xsl:template match="entity[@name='aelig']">&#230;</xsl:template>
<xsl:template match="entity[@name='ccedil']">&#231;</xsl:template>
<xsl:template match="entity[@name='egrave']">&#232;</xsl:template>
<xsl:template match="entity[@name='eacute']">&#233;</xsl:template>
<xsl:template match="entity[@name='ecirc']">&#234;</xsl:template>
<xsl:template match="entity[@name='euml']">&#235;</xsl:template>
<xsl:template match="entity[@name='igrave']">&#236;</xsl:template>
<xsl:template match="entity[@name='iacute']">&#237;</xsl:template>
<xsl:template match="entity[@name='icirc']">&#238;</xsl:template>
<xsl:template match="entity[@name='iuml']">&#239;</xsl:template>
<xsl:template match="entity[@name='eth']">&#240;</xsl:template>
<xsl:template match="entity[@name='ntilde']">&#241;</xsl:template>
<xsl:template match="entity[@name='ograve']">&#242;</xsl:template>
<xsl:template match="entity[@name='oacute']">&#243;</xsl:template>
<xsl:template match="entity[@name='ocirc']">&#244;</xsl:template>
<xsl:template match="entity[@name='otilde']">&#245;</xsl:template>
<xsl:template match="entity[@name='ouml']">&#246;</xsl:template>
<xsl:template match="entity[@name='divide']">&#247;</xsl:template>
<xsl:template match="entity[@name='oslash']">&#248;</xsl:template>
<xsl:template match="entity[@name='ugrave']">&#249;</xsl:template>
<xsl:template match="entity[@name='uacute']">&#250;</xsl:template>
<xsl:template match="entity[@name='ucirc']">&#251;</xsl:template>
<xsl:template match="entity[@name='uuml']">&#252;</xsl:template>
<xsl:template match="entity[@name='yacute']">&#253;</xsl:template>
<xsl:template match="entity[@name='thorn']">&#254;</xsl:template>
<xsl:template match="entity[@name='yuml']">&#255;</xsl:template>

<!-- WinAnsi additions to Latin-1 -->

<xsl:template match="entity[@name='OElig']">&#338;</xsl:template>
<xsl:template match="entity[@name='oelig']">&#339;</xsl:template>
<xsl:template match="entity[@name='Scaron']">&#352;</xsl:template>
<xsl:template match="entity[@name='scaron']">&#353;</xsl:template>
<xsl:template match="entity[@name='Yuml']">&#376;</xsl:template>
<xsl:template match="entity[@name='circ']">&#710;</xsl:template>
<xsl:template match="entity[@name='tilde']">&#732;</xsl:template>
<xsl:template match="entity[@name='ndash']">&#8211;</xsl:template>
<xsl:template match="entity[@name='mdash']">&#8212;</xsl:template>
<xsl:template match="entity[@name='lsquo']">&#8216;</xsl:template>
<xsl:template match="entity[@name='rsquo']">&#8217;</xsl:template>
<xsl:template match="entity[@name='sbquo']">&#8218;</xsl:template>
<xsl:template match="entity[@name='ldquo']">&#8220;</xsl:template>
<xsl:template match="entity[@name='rdquo']">&#8221;</xsl:template>
<xsl:template match="entity[@name='bdquo']">&#8222;</xsl:template>
<xsl:template match="entity[@name='dagger']">&#8224;</xsl:template>
<xsl:template match="entity[@name='Dagger']">&#8225;</xsl:template>
<xsl:template match="entity[@name='permil']">&#8240;</xsl:template>
<xsl:template match="entity[@name='lsaquo']">&#8249;</xsl:template>
<xsl:template match="entity[@name='rsaquo']">&#8250;</xsl:template>
<xsl:template match="entity[@name='euro']">&#8364;</xsl:template>
<xsl:template match="entity[@name='Zcaron']">&#x017D;</xsl:template>
<xsl:template match="entity[@name='zcaron']">&#x017E;</xsl:template>
<xsl:template match="entity[@name='fnof']">&#x0192;</xsl:template>
<xsl:template match="entity[@name='bull']">&#x2022;</xsl:template>
<xsl:template match="entity[@name='hellip']">&#x2026;</xsl:template>
<xsl:template match="entity[@name='trade']">&#x2122;</xsl:template>

<!-- =============================================================== -->
<!-- CSS2 Citation (XSL FO only)                                     -->

<xsl:template match="css-cited">
  <fo:block space-before.optimum="6pt"
            space-after.optimum="6pt"
            space-after.precedence="force">
    <xsl:if test="@border">
      <xsl:attribute name="border-style">ridge</xsl:attribute>
      <xsl:attribute name="border-color">silver</xsl:attribute>

      <xsl:attribute name="border-width"><xsl:value-of select="@border"/></xsl:attribute>
      <xsl:attribute name="border-before-width.conditionality">discard</xsl:attribute>      
      <xsl:attribute name="border-after-width.conditionality">discard</xsl:attribute>      

      <xsl:attribute name="padding">3pt 6pt</xsl:attribute>
      <xsl:attribute name="padding-before.conditionality">discard</xsl:attribute>      
      <xsl:attribute name="padding-after.conditionality">discard</xsl:attribute>      
    </xsl:if>
    <xsl:apply-templates/>
  </fo:block>
</xsl:template>


<!-- *************************************************************** -->
<!-- *************************************************************** -->
<!-- Element syntax descriptions from XSLT (xmlns:e)                 -->
<!-- *************************************************************** -->
<!-- *************************************************************** -->

<xsl:template match="e:element-syntax">
  <fo:block space-before.optimum="6pt" 
            space-after.optimum="6pt" 
            space-after.precedence="force"
            border="1pt solid gray"
            padding="6pt 12pt">
    <xsl:call-template name="draw-element"/>
  </fo:block>
</xsl:template>

<xsl:template name="draw-element">
  <fo:block font-family="Courier" keep-together.within-column="always">

    <!-- List of categories to which the element belongs -->
    <xsl:apply-templates select="e:in-category"/>

    <!-- Opening tag -->    
    <fo:block font-weight="bold">
      <xsl:text>&lt;</xsl:text>
      <fo:wrapper color="#A00000">
        <xsl:text>xsl:</xsl:text>
        <xsl:value-of select="@name"/>
      </fo:wrapper>
      <xsl:if test="not(e:attribute)">
        <xsl:if test="e:empty">
          <xsl:text>/</xsl:text>
        </xsl:if>
        <xsl:text>&gt;</xsl:text>
      </xsl:if>
    </fo:block>
   
    <!-- Attributes -->    
    <xsl:apply-templates select="e:attribute"/>

    <!-- Content model and closure tag -->
    <xsl:if test="not(e:empty)">
      <fo:block padding-left="36pt">
        <xsl:text>&lt;!-- Content: </xsl:text>
        <xsl:apply-templates select="e:text|e:element|e:model|e:sequence|e:choice"/>
        <xsl:text> --&gt;</xsl:text>
      </fo:block>

      <!-- Closure tag -->
      <fo:block font-weight="bold">
        <xsl:text>&lt;/</xsl:text>
        <fo:wrapper color="#A00000">
          <xsl:text>xsl:</xsl:text>
          <xsl:value-of select="@name"/>
        </fo:wrapper>
        <xsl:text>&gt;</xsl:text>
      </fo:block>
    </xsl:if>

  </fo:block>
</xsl:template>


<xsl:template match="e:attribute">
  <fo:block padding-left="36pt">
    <fo:wrapper>
      <xsl:if test="@required='yes'">
        <xsl:attribute name="font-weight">bold</xsl:attribute>
      </xsl:if>
      <xsl:value-of select="@name"/>
    </fo:wrapper>
    <xsl:text> = </xsl:text>
    <xsl:apply-templates/>
    
    <!-- Last attribute closes the tag -->
    <xsl:if test="not(following-sibling::e:attribute)">
      <fo:wrapper font-weight="bold">
        <xsl:if test="../e:empty">
          <xsl:text>/</xsl:text>
        </xsl:if>
        <xsl:text>&gt;</xsl:text>
      </fo:wrapper>
    </xsl:if>
  </fo:block>
</xsl:template>

<xsl:template match="e:in-category">
  <fo:block>
    <xsl:text>&lt;!-- Category: </xsl:text>
    <fo:wrapper font-style="italic">
      <xsl:value-of select="@name"/>
    </fo:wrapper>
    <xsl:text> --&gt;</xsl:text>
  </fo:block>
</xsl:template>

<xsl:template match="e:attribute-value-template">
  <xsl:text>{ </xsl:text>
  <xsl:apply-templates/>
  <xsl:text> }</xsl:text>
</xsl:template>

<xsl:template match="e:data-type">
  <fo:wrapper font-style="italic">
    <xsl:value-of select="@name"/>
  </fo:wrapper>

  <xsl:if test="following-sibling::e:data-type or 
                following-sibling::e:constant">
    <xsl:text> | </xsl:text>
  </xsl:if>
</xsl:template>

<xsl:template match="e:constant">
  <xsl:text>&quot;</xsl:text>
  <xsl:value-of select="@value"/>
  <xsl:text>&quot;</xsl:text>

  <xsl:if test="following-sibling::e:data-type or 
                following-sibling::e:constant">
    <xsl:text> | </xsl:text>
  </xsl:if>
</xsl:template>

<xsl:template match="e:text">
  <xsl:text>#PCDATA</xsl:text>
</xsl:template>

<xsl:template match="e:model">
  <fo:wrapper font-style="italic"><xsl:value-of select="@name"/></fo:wrapper>
</xsl:template>

<xsl:template match="e:element">
  <xsl:text>xsl:</xsl:text>
  <xsl:value-of select="@name"/>
  <xsl:apply-templates select="@repeat"/>
</xsl:template>

<xsl:template match="e:sequence | e:choice">
  <xsl:text>(</xsl:text>
    <xsl:for-each select="*">
      <xsl:apply-templates select="."/>
      <xsl:if test="following-sibling::*">
        <xsl:apply-templates select=".." mode="separator-mode"/>
      </xsl:if>
    </xsl:for-each>
  <xsl:text>)</xsl:text>
  <xsl:apply-templates select="@repeat"/>
</xsl:template>

<xsl:template match="e:sequence" mode="separator-mode">, </xsl:template>
<xsl:template match="e:choice" mode="separator-mode"> | </xsl:template>

<xsl:template match="@repeat[.='zero-or-one']">?</xsl:template>
<xsl:template match="@repeat[.='zero-or-more']">*</xsl:template>
<xsl:template match="@repeat[.='one-or-more']">+</xsl:template>

<!-- Summary of all elements -->

<xsl:template match="e:element-syntax-summary">
  <xsl:for-each select="/descendant::e:element-syntax">
    <xsl:sort select="@name"/>
    <fo:block space-before.optimum="9pt"
              space-after.optimum="9pt"> 
      <xsl:call-template name="draw-element"/>
    </fo:block>
  </xsl:for-each>
</xsl:template>

</xsl:stylesheet>

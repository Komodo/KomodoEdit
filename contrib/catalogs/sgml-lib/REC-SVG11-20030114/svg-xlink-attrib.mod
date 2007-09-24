<!-- ....................................................................... -->
<!-- SVG 1.1 XLink Attribute Module ........................................ -->
<!-- file: svg-xlink-attrib.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-xlink-attrib.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ENTITIES SVG 1.1 XLink Attribute//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-xlink-attrib.mod"

     ....................................................................... -->

<!-- XLink Attribute

       type, href, role, arcrole, title, show, actuate

     This module defines the XLink, XLinkRequired, XLinkEmbed, and
     XLinkReplace attribute set.
-->

<!ENTITY % SVG.XLink.extra.attrib "" >

<!ENTITY % SVG.XLink.attrib
    "%XLINK.xmlns.attrib;
     %XLINK.pfx;type ( simple ) #FIXED 'simple'
     %XLINK.pfx;href %URI.datatype; #IMPLIED
     %XLINK.pfx;role %URI.datatype; #IMPLIED
     %XLINK.pfx;arcrole %URI.datatype; #IMPLIED
     %XLINK.pfx;title CDATA #IMPLIED
     %XLINK.pfx;show ( other ) 'other'
     %XLINK.pfx;actuate ( onLoad ) #FIXED 'onLoad'
     %SVG.XLink.extra.attrib;"
>

<!ENTITY % SVG.XLinkRequired.extra.attrib "" >

<!ENTITY % SVG.XLinkRequired.attrib
    "%XLINK.xmlns.attrib;
     %XLINK.pfx;type ( simple ) #FIXED 'simple'
     %XLINK.pfx;href %URI.datatype; #REQUIRED
     %XLINK.pfx;role %URI.datatype; #IMPLIED
     %XLINK.pfx;arcrole %URI.datatype; #IMPLIED
     %XLINK.pfx;title CDATA #IMPLIED
     %XLINK.pfx;show ( other ) 'other'
     %XLINK.pfx;actuate ( onLoad ) #FIXED 'onLoad'
     %SVG.XLinkRequired.extra.attrib;"
>

<!ENTITY % SVG.XLinkEmbed.extra.attrib "" >

<!ENTITY % SVG.XLinkEmbed.attrib
    "%XLINK.xmlns.attrib;
     %XLINK.pfx;type ( simple ) #FIXED 'simple'
     %XLINK.pfx;href %URI.datatype; #REQUIRED
     %XLINK.pfx;role %URI.datatype; #IMPLIED
     %XLINK.pfx;arcrole %URI.datatype; #IMPLIED
     %XLINK.pfx;title CDATA #IMPLIED
     %XLINK.pfx;show ( embed ) 'embed'
     %XLINK.pfx;actuate ( onLoad ) #FIXED 'onLoad'
     %SVG.XLinkEmbed.extra.attrib;"
>

<!ENTITY % SVG.XLinkReplace.extra.attrib "" >

<!ENTITY % SVG.XLinkReplace.attrib
    "%XLINK.xmlns.attrib;
     %XLINK.pfx;type ( simple ) #FIXED 'simple'
     %XLINK.pfx;href %URI.datatype; #REQUIRED
     %XLINK.pfx;role %URI.datatype; #IMPLIED
     %XLINK.pfx;arcrole %URI.datatype; #IMPLIED
     %XLINK.pfx;title CDATA #IMPLIED
     %XLINK.pfx;show ( new | replace ) 'replace'
     %XLINK.pfx;actuate ( onRequest ) #FIXED 'onRequest'
     %SVG.XLinkReplace.extra.attrib;"
>

<!-- end of svg-xlink-attrib.mod -->

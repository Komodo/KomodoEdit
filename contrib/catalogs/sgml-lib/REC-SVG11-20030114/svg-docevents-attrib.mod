<!-- ....................................................................... -->
<!-- SVG 1.1 Document Events Attribute Module .............................. -->
<!-- file: svg-docevents-attrib.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-docevents-attrib.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ENTITIES SVG 1.1 Document Events Attribute//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-docevents-attrib.mod"

     ....................................................................... -->

<!-- Document Events Attribute

        onunload, onabort, onerror, onresize, onscroll, onzoom

     This module defines the DocumentEvents attribute set.
-->

<!ENTITY % SVG.onunload.attrib
    "onunload %Script.datatype; #IMPLIED"
>

<!ENTITY % SVG.onabort.attrib
    "onabort %Script.datatype; #IMPLIED"
>

<!ENTITY % SVG.onerror.attrib
    "onerror %Script.datatype; #IMPLIED"
>

<!ENTITY % SVG.onresize.attrib
    "onresize %Script.datatype; #IMPLIED"
>

<!ENTITY % SVG.onscroll.attrib
    "onscroll %Script.datatype; #IMPLIED"
>

<!ENTITY % SVG.onzoom.attrib
    "onzoom %Script.datatype; #IMPLIED"
>

<!ENTITY % SVG.DocumentEvents.extra.attrib "" >

<!ENTITY % SVG.DocumentEvents.attrib
    "%SVG.onunload.attrib;
     %SVG.onabort.attrib;
     %SVG.onerror.attrib;
     %SVG.onresize.attrib;
     %SVG.onscroll.attrib;
     %SVG.onzoom.attrib;
     %SVG.DocumentEvents.extra.attrib;"
>

<!-- end of svg-docevents-attrib.mod -->

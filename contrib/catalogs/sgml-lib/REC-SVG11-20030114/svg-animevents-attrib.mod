<!-- ....................................................................... -->
<!-- SVG 1.1 Animation Events Attribute Module ............................. -->
<!-- file: svg-animevents-attrib.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-animevents-attrib.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ENTITIES SVG 1.1 Animation Events Attribute//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-animevents-attrib.mod"

     ....................................................................... -->

<!-- Animation Events Attribute

        onbegin, onend, onrepeat, onload

     This module defines the AnimationEvents attribute set.
-->

<!ENTITY % SVG.onbegin.attrib
    "onbegin %Script.datatype; #IMPLIED"
>

<!ENTITY % SVG.onend.attrib
    "onend %Script.datatype; #IMPLIED"
>

<!ENTITY % SVG.onrepeat.attrib
    "onrepeat %Script.datatype; #IMPLIED"
>

<!ENTITY % SVG.onload.attrib
    "onload %Script.datatype; #IMPLIED"
>

<!ENTITY % SVG.AnimationEvents.extra.attrib "" >

<!ENTITY % SVG.AnimationEvents.attrib
    "%SVG.onbegin.attrib;
     %SVG.onend.attrib;
     %SVG.onrepeat.attrib;
     %SVG.onload.attrib;
     %SVG.AnimationEvents.extra.attrib;"
>

<!-- end of svg-animevents-attrib.mod -->

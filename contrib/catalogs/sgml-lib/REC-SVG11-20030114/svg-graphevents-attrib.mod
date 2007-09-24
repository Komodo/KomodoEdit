<!-- ....................................................................... -->
<!-- SVG 1.1 Graphical Element Events Attribute Module ..................... -->
<!-- file: svg-graphevents-attrib.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-graphevents-attrib.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ENTITIES SVG 1.1 Graphical Element Events Attribute//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-graphevents-attrib.mod"

     ....................................................................... -->

<!-- Graphical Element Events Attribute

        onfocusin, onfocusout, onactivate, onclick, onmousedown, onmouseup,
        onmouseover, onmousemove, onmouseout, onload

     This module defines the GraphicalEvents attribute set.
-->

<!ENTITY % SVG.onfocusin.attrib
    "onfocusin %Script.datatype; #IMPLIED"
>

<!ENTITY % SVG.onfocusout.attrib
    "onfocusout %Script.datatype; #IMPLIED"
>

<!ENTITY % SVG.onactivate.attrib
    "onactivate %Script.datatype; #IMPLIED"
>

<!ENTITY % SVG.onclick.attrib
    "onclick %Script.datatype; #IMPLIED"
>

<!ENTITY % SVG.onmousedown.attrib
    "onmousedown %Script.datatype; #IMPLIED"
>

<!ENTITY % SVG.onmouseup.attrib
    "onmouseup %Script.datatype; #IMPLIED"
>

<!ENTITY % SVG.onmouseover.attrib
    "onmouseover %Script.datatype; #IMPLIED"
>

<!ENTITY % SVG.onmousemove.attrib
    "onmousemove %Script.datatype; #IMPLIED"
>

<!ENTITY % SVG.onmouseout.attrib
    "onmouseout %Script.datatype; #IMPLIED"
>

<!ENTITY % SVG.onload.attrib
    "onload %Script.datatype; #IMPLIED"
>

<!ENTITY % SVG.GraphicalEvents.extra.attrib "" >

<!ENTITY % SVG.GraphicalEvents.attrib
    "%SVG.onfocusin.attrib;
     %SVG.onfocusout.attrib;
     %SVG.onactivate.attrib;
     %SVG.onclick.attrib;
     %SVG.onmousedown.attrib;
     %SVG.onmouseup.attrib;
     %SVG.onmouseover.attrib;
     %SVG.onmousemove.attrib;
     %SVG.onmouseout.attrib;
     %SVG.onload.attrib;
     %SVG.GraphicalEvents.extra.attrib;"
>

<!-- end of svg-graphevents-attrib.mod -->

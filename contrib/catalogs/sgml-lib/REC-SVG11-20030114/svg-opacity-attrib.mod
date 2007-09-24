<!-- ....................................................................... -->
<!-- SVG 1.1 Paint Opacity Attribute Module ................................ -->
<!-- file: svg-opacity-attrib.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-opacity-attrib.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ENTITIES SVG 1.1 Paint Opacity Attribute//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-opacity-attrib.mod"

     ....................................................................... -->

<!-- Paint Opacity Attribute

        opacity, fill-opacity, stroke-opacity

     This module defines the Opacity attribute set.
-->

<!ENTITY % SVG.opacity.attrib
    "opacity %OpacityValue.datatype; #IMPLIED"
>

<!ENTITY % SVG.fill-opacity.attrib
    "fill-opacity %OpacityValue.datatype; #IMPLIED"
>

<!ENTITY % SVG.stroke-opacity.attrib
    "stroke-opacity %OpacityValue.datatype; #IMPLIED"
>

<!ENTITY % SVG.Opacity.extra.attrib "" >

<!ENTITY % SVG.Opacity.attrib
    "%SVG.opacity.attrib;
     %SVG.fill-opacity.attrib;
     %SVG.stroke-opacity.attrib;
     %SVG.Opacity.extra.attrib;"
>

<!-- end of svg-opacity-attrib.mod -->

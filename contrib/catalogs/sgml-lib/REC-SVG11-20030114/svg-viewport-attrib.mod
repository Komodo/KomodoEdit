<!-- ....................................................................... -->
<!-- SVG 1.1 Viewport Attribute Module ..................................... -->
<!-- file: svg-viewport-attrib.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-viewport-attrib.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ENTITIES SVG 1.1 Viewport Attribute//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-viewport-attrib.mod"

     ....................................................................... -->

<!-- Viewport Attribute

        clip, overflow

     This module defines the Viewport attribute set.
-->

<!-- 'clip' property/attribute value (e.g., 'auto', rect(...)) -->
<!ENTITY % ClipValue.datatype "CDATA" >

<!ENTITY % SVG.clip.attrib
    "clip %ClipValue.datatype; #IMPLIED"
>

<!ENTITY % SVG.overflow.attrib
    "overflow ( visible | hidden | scroll | auto | inherit ) #IMPLIED"
>

<!ENTITY % SVG.Viewport.extra.attrib "" >

<!ENTITY % SVG.Viewport.attrib
    "%SVG.clip.attrib;
     %SVG.overflow.attrib;
     %SVG.Viewport.extra.attrib;"
>

<!-- end of svg-viewport-attrib.mod -->

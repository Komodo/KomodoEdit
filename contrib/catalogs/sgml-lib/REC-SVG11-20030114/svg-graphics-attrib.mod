<!-- ....................................................................... -->
<!-- SVG 1.1 Graphics Attribute Module ..................................... -->
<!-- file: svg-graphics-attrib.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-graphics-attrib.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ENTITIES SVG 1.1 Graphics Attribute//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-graphics-attrib.mod"

     ....................................................................... -->

<!-- Graphics Attribute

        display, image-rendering, pointer-events, shape-rendering,
        text-rendering, visibility

     This module defines the Graphics attribute set.
-->

<!ENTITY % SVG.display.attrib
    "display ( inline | block | list-item | run-in | compact | marker |
               table | inline-table | table-row-group | table-header-group |
               table-footer-group | table-row | table-column-group |
               table-column | table-cell | table-caption | none | inherit )
               #IMPLIED"
>

<!ENTITY % SVG.image-rendering.attrib
    "image-rendering ( auto | optimizeSpeed | optimizeQuality | inherit )
                       #IMPLIED"
>

<!ENTITY % SVG.pointer-events.attrib
    "pointer-events ( visiblePainted | visibleFill | visibleStroke | visible |
                      painted | fill | stroke | all | none | inherit )
                      #IMPLIED"
>

<!ENTITY % SVG.shape-rendering.attrib
    "shape-rendering ( auto | optimizeSpeed | crispEdges | geometricPrecision |
                       inherit ) #IMPLIED"
>

<!ENTITY % SVG.text-rendering.attrib
    "text-rendering ( auto | optimizeSpeed | optimizeLegibility |
                      geometricPrecision | inherit ) #IMPLIED"
>

<!ENTITY % SVG.visibility.attrib
    "visibility ( visible | hidden | inherit ) #IMPLIED"
>

<!ENTITY % SVG.Graphics.extra.attrib "" >

<!ENTITY % SVG.Graphics.attrib
    "%SVG.display.attrib;
     %SVG.image-rendering.attrib;
     %SVG.pointer-events.attrib;
     %SVG.shape-rendering.attrib;
     %SVG.text-rendering.attrib;
     %SVG.visibility.attrib;
     %SVG.Graphics.extra.attrib;"
>

<!-- end of svg-graphics-attrib.mod -->

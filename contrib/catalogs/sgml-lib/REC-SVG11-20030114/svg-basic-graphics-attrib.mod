<!-- ....................................................................... -->
<!-- SVG 1.1 Basic Graphics Attribute Module ............................... -->
<!-- file: svg-basic-graphics-attrib.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-basic-graphics-attrib.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ENTITIES SVG 1.1 Basic Graphics Attribute//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-basic-graphics-attrib.mod"

     ....................................................................... -->

<!-- Basic Graphics Attribute

        display, visibility

     This module defines the Graphics attribute set.
-->

<!ENTITY % SVG.display.attrib
    "display ( inline | block | list-item | run-in | compact | marker |
               table | inline-table | table-row-group | table-header-group |
               table-footer-group | table-row | table-column-group |
               table-column | table-cell | table-caption | none | inherit )
               #IMPLIED"
>

<!ENTITY % SVG.visibility.attrib
    "visibility ( visible | hidden | inherit ) #IMPLIED"
>

<!ENTITY % SVG.Graphics.extra.attrib "" >

<!ENTITY % SVG.Graphics.attrib
    "%SVG.display.attrib;
     %SVG.visibility.attrib;
     %SVG.Graphics.extra.attrib;"
>

<!-- end of svg-basic-graphics-attrib.mod -->

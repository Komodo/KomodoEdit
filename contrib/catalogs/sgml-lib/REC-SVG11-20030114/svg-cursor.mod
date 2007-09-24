<!-- ....................................................................... -->
<!-- SVG 1.1 Cursor Module ................................................. -->
<!-- file: svg-cursor.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-cursor.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ELEMENTS SVG 1.1 Cursor//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-cursor.mod"

     ....................................................................... -->

<!-- Cursor

        cursor

     This module declares markup to provide support for cursor.
-->

<!-- 'cursor' property/attribute value (e.g., 'crosshair', <uri>) -->
<!ENTITY % CursorValue.datatype "CDATA" >

<!-- Qualified Names (Default) ......................... -->

<!ENTITY % SVG.cursor.qname "cursor" >

<!-- Attribute Collections (Default) ................... -->

<!ENTITY % SVG.Core.attrib "" >
<!ENTITY % SVG.Conditional.attrib "" >
<!ENTITY % SVG.XLinkRequired.attrib "" >
<!ENTITY % SVG.External.attrib "" >

<!-- SVG.Cursor.class .................................. -->

<!ENTITY % SVG.Cursor.extra.class "" >

<!ENTITY % SVG.Cursor.class
    "| %SVG.cursor.qname; %SVG.Cursor.extra.class;"
>

<!-- SVG.Cursor.attrib ................................. -->

<!ENTITY % SVG.Cursor.extra.attrib "" >

<!ENTITY % SVG.Cursor.attrib
    "cursor %CursorValue.datatype; #IMPLIED
     %SVG.Cursor.extra.attrib;"
>

<!-- cursor: Cursor Element ............................ -->

<!ENTITY % SVG.cursor.extra.content "" >

<!ENTITY % SVG.cursor.element "INCLUDE" >
<![%SVG.cursor.element;[
<!ENTITY % SVG.cursor.content
    "( %SVG.Description.class; %SVG.cursor.extra.content; )*"
>
<!ELEMENT %SVG.cursor.qname; %SVG.cursor.content; >
<!-- end of SVG.cursor.element -->]]>

<!ENTITY % SVG.cursor.attlist "INCLUDE" >
<![%SVG.cursor.attlist;[
<!ATTLIST %SVG.cursor.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.XLinkRequired.attrib;
    %SVG.External.attrib;
    x %Coordinate.datatype; #IMPLIED
    y %Coordinate.datatype; #IMPLIED
>
<!-- end of SVG.cursor.attlist -->]]>

<!-- end of svg-cursor.mod -->

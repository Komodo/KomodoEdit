<!-- ....................................................................... -->
<!-- SVG 1.1 Extensibility Module .......................................... -->
<!-- file: svg-extensibility.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-extensibility.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ELEMENTS SVG 1.1 Extensibility//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-extensibility.mod"

     ....................................................................... -->

<!-- Extensibility

        foreignObject

     This module declares markup to provide support for extensibility.
-->

<!-- Qualified Names (Default) ......................... -->

<!ENTITY % SVG.foreignObject.qname "foreignObject" >

<!-- Attribute Collections (Default) ................... -->

<!ENTITY % SVG.Core.attrib "" >
<!ENTITY % SVG.Conditional.attrib "" >
<!ENTITY % SVG.Style.attrib "" >
<!ENTITY % SVG.Viewport.attrib "" >
<!ENTITY % SVG.Text.attrib "" >
<!ENTITY % SVG.TextContent.attrib "" >
<!ENTITY % SVG.Font.attrib "" >
<!ENTITY % SVG.Paint.attrib "" >
<!ENTITY % SVG.Color.attrib "" >
<!ENTITY % SVG.Opacity.attrib "" >
<!ENTITY % SVG.Graphics.attrib "" >
<!ENTITY % SVG.Marker.attrib "" >
<!ENTITY % SVG.Gradient.attrib "" >
<!ENTITY % SVG.Clip.attrib "" >
<!ENTITY % SVG.Mask.attrib "" >
<!ENTITY % SVG.Filter.attrib "" >
<!ENTITY % SVG.FilterColor.attrib "" >
<!ENTITY % SVG.GraphicalEvents.attrib "" >
<!ENTITY % SVG.Cursor.attrib "" >
<!ENTITY % SVG.External.attrib "" >

<!-- SVG.Extensibility.class ........................... -->

<!ENTITY % SVG.Extensibility.extra.class "" >

<!ENTITY % SVG.Extensibility.class
    "| %SVG.foreignObject.qname; %SVG.Extensibility.extra.class;"
>

<!-- SVG.Presentation.attrib ........................... -->

<!ENTITY % SVG.Presentation.extra.attrib "" >

<!ENTITY % SVG.Presentation.attrib
    "%SVG.Container.attrib;
     %SVG.Viewport.attrib;
     %SVG.Text.attrib;
     %SVG.TextContent.attrib;
     %SVG.Font.attrib;
     %SVG.Paint.attrib;
     %SVG.Color.attrib;
     %SVG.Opacity.attrib;
     %SVG.Graphics.attrib;
     %SVG.Marker.attrib;
     %SVG.ColorProfile.attrib;
     %SVG.Gradient.attrib;
     %SVG.Clip.attrib;
     %SVG.Mask.attrib;
     %SVG.Filter.attrib;
     %SVG.FilterColor.attrib;
     %SVG.Cursor.attrib;
     flood-color %SVGColor.datatype; #IMPLIED
     flood-opacity %OpacityValue.datatype; #IMPLIED
     lighting-color %SVGColor.datatype; #IMPLIED
     %SVG.Presentation.extra.attrib;"
>

<!-- foreignObject: Foreign Object Element ............. -->

<!ENTITY % SVG.foreignObject.extra.content "" >

<!ENTITY % SVG.foreignObject.element "INCLUDE" >
<![%SVG.foreignObject.element;[
<!ENTITY % SVG.foreignObject.content
    "( #PCDATA %SVG.foreignObject.extra.content; )*"
>
<!ELEMENT %SVG.foreignObject.qname; %SVG.foreignObject.content; >
<!-- end of SVG.foreignObject.element -->]]>

<!ENTITY % SVG.foreignObject.attlist "INCLUDE" >
<![%SVG.foreignObject.attlist;[
<!ATTLIST %SVG.foreignObject.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.Style.attrib;
    %SVG.Presentation.attrib;
    %SVG.GraphicalEvents.attrib;
    %SVG.External.attrib;
    x %Coordinate.datatype; #IMPLIED
    y %Coordinate.datatype; #IMPLIED
    width %Length.datatype; #REQUIRED
    height %Length.datatype; #REQUIRED
    transform %TransformList.datatype; #IMPLIED
>
<!-- end of SVG.foreignObject.attlist -->]]>

<!-- end of svg-extensibility.mod -->

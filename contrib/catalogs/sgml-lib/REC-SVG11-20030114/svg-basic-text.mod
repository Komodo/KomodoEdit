<!-- ....................................................................... -->
<!-- SVG 1.1 Basic Text Module ............................................. -->
<!-- file: svg-basic-text.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-basic-text.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ELEMENTS SVG 1.1 Basic Text//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-basic-text.mod"

     ....................................................................... -->

<!-- Basic Text

        text

     This module declares markup to provide support for text.
-->

<!-- 'font-family' property/attribute value (i.e., list of fonts) -->
<!ENTITY % FontFamilyValue.datatype "CDATA" >

<!-- 'font-size' property/attribute value -->
<!ENTITY % FontSizeValue.datatype "CDATA" >

<!-- Qualified Names (Default) ......................... -->

<!ENTITY % SVG.text.qname "text" >

<!-- Attribute Collections (Default) ................... -->

<!ENTITY % SVG.Core.attrib "" >
<!ENTITY % SVG.Conditional.attrib "" >
<!ENTITY % SVG.Style.attrib "" >
<!ENTITY % SVG.Paint.attrib "" >
<!ENTITY % SVG.Color.attrib "" >
<!ENTITY % SVG.Opacity.attrib "" >
<!ENTITY % SVG.Graphics.attrib "" >
<!ENTITY % SVG.Clip.attrib "" >
<!ENTITY % SVG.Mask.attrib "" >
<!ENTITY % SVG.Filter.attrib "" >
<!ENTITY % SVG.GraphicalEvents.attrib "" >
<!ENTITY % SVG.Cursor.attrib "" >
<!ENTITY % SVG.External.attrib "" >

<!-- SVG.Text.class .................................... -->

<!ENTITY % SVG.Text.extra.class "" >

<!ENTITY % SVG.Text.class
    "| %SVG.text.qname; %SVG.Text.extra.class;"
>

<!-- SVG.TextContent.attrib ............................ -->

<!ENTITY % SVG.TextContent.extra.attrib "" >

<!ENTITY % SVG.TextContent.attrib
    "text-anchor ( start | middle | end | inherit ) #IMPLIED
     %SVG.TextContent.extra.attrib;"
>

<!-- SVG.Font.attrib ................................... -->

<!ENTITY % SVG.Font.extra.attrib "" >

<!ENTITY % SVG.Font.attrib
    "font-family %FontFamilyValue.datatype; #IMPLIED
     font-size %FontSizeValue.datatype; #IMPLIED
     font-style ( normal | italic | oblique | inherit ) #IMPLIED
     font-weight ( normal | bold | bolder | lighter | 100 | 200 | 300 | 400 |
                   500 | 600 | 700 | 800 | 900 | inherit ) #IMPLIED
     %SVG.Font.extra.attrib;"
>

<!-- text: Text Element ................................ -->

<!ENTITY % SVG.text.extra.content "" >

<!ENTITY % SVG.text.element "INCLUDE" >
<![%SVG.text.element;[
<!ENTITY % SVG.text.content
    "( #PCDATA | %SVG.Description.class; | %SVG.Animation.class;
       %SVG.Hyperlink.class; %SVG.text.extra.content; )*"
>
<!ELEMENT %SVG.text.qname; %SVG.text.content; >
<!-- end of SVG.text.element -->]]>

<!ENTITY % SVG.text.attlist "INCLUDE" >
<![%SVG.text.attlist;[
<!ATTLIST %SVG.text.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.Style.attrib;
    %SVG.TextContent.attrib;
    %SVG.Font.attrib;
    %SVG.Paint.attrib;
    %SVG.Color.attrib;
    %SVG.Opacity.attrib;
    %SVG.Graphics.attrib;
    %SVG.Clip.attrib;
    %SVG.Mask.attrib;
    %SVG.Filter.attrib;
    %SVG.GraphicalEvents.attrib;
    %SVG.Cursor.attrib;
    %SVG.External.attrib;
    x %Coordinates.datatype; #IMPLIED
    y %Coordinates.datatype; #IMPLIED
    rotate %Numbers.datatype; #IMPLIED
    transform %TransformList.datatype; #IMPLIED
>
<!-- end of SVG.text.attlist -->]]>

<!-- end of svg-basic-text.mod -->

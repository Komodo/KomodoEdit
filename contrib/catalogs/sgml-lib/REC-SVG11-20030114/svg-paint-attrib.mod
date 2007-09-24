<!-- ....................................................................... -->
<!-- SVG 1.1 Paint Attribute Module ........................................ -->
<!-- file: svg-paint-attrib.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-paint-attrib.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ENTITIES SVG 1.1 Paint Attribute//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-paint-attrib.mod"

     ....................................................................... -->

<!-- Paint Attribute

        fill, fill-rule, stroke, stroke-dasharray, stroke-dashoffset,
        stroke-linecap, stroke-linejoin, stroke-miterlimit, stroke-width, color,
        color-interpolation, color-rendering

     This module defines the Paint and Color attribute sets.
-->

<!-- a 'fill' or 'stroke' property/attribute value: <paint> -->
<!ENTITY % Paint.datatype "CDATA" >

<!-- 'stroke-dasharray' property/attribute value (e.g., 'none', list of <number>s) -->
<!ENTITY % StrokeDashArrayValue.datatype "CDATA" >

<!-- 'stroke-dashoffset' property/attribute value (e.g., 'none', <legnth>) -->
<!ENTITY % StrokeDashOffsetValue.datatype "CDATA" >

<!-- 'stroke-miterlimit' property/attribute value (e.g., <number>) -->
<!ENTITY % StrokeMiterLimitValue.datatype "CDATA" >

<!-- 'stroke-width' property/attribute value (e.g., <length>) -->
<!ENTITY % StrokeWidthValue.datatype "CDATA" >

<!ENTITY % SVG.fill.attrib
    "fill %Paint.datatype; #IMPLIED"
>

<!ENTITY % SVG.fill-rule.attrib
    "fill-rule %ClipFillRule.datatype; #IMPLIED"
>

<!ENTITY % SVG.stroke.attrib
    "stroke %Paint.datatype; #IMPLIED"
>

<!ENTITY % SVG.stroke-dasharray.attrib
    "stroke-dasharray %StrokeDashArrayValue.datatype; #IMPLIED"
>

<!ENTITY % SVG.stroke-dashoffset.attrib
    "stroke-dashoffset %StrokeDashOffsetValue.datatype; #IMPLIED"
>

<!ENTITY % SVG.stroke-linecap.attrib
    "stroke-linecap ( butt | round | square | inherit ) #IMPLIED"
>

<!ENTITY % SVG.stroke-linejoin.attrib
    "stroke-linejoin ( miter | round | bevel | inherit ) #IMPLIED"
>

<!ENTITY % SVG.stroke-miterlimit.attrib
    "stroke-miterlimit %StrokeMiterLimitValue.datatype; #IMPLIED"
>

<!ENTITY % SVG.stroke-width.attrib
    "stroke-width %StrokeWidthValue.datatype; #IMPLIED"
>

<!ENTITY % SVG.Paint.extra.attrib "" >

<!ENTITY % SVG.Paint.attrib
    "%SVG.fill.attrib;
     %SVG.fill-rule.attrib;
     %SVG.stroke.attrib;
     %SVG.stroke-dasharray.attrib;
     %SVG.stroke-dashoffset.attrib;
     %SVG.stroke-linecap.attrib;
     %SVG.stroke-linejoin.attrib;
     %SVG.stroke-miterlimit.attrib;
     %SVG.stroke-width.attrib;
     %SVG.Paint.extra.attrib;"
>

<!ENTITY % SVG.color.attrib
    "color %Color.datatype; #IMPLIED"
>

<!ENTITY % SVG.color-interpolation.attrib
    "color-interpolation ( auto | sRGB | linearRGB | inherit ) #IMPLIED"
>

<!ENTITY % SVG.color-rendering.attrib
    "color-rendering ( auto | optimizeSpeed | optimizeQuality | inherit )
                       #IMPLIED"
>

<!ENTITY % SVG.Color.extra.attrib "" >

<!ENTITY % SVG.Color.attrib
    "%SVG.color.attrib;
     %SVG.color-interpolation.attrib;
     %SVG.color-rendering.attrib;
     %SVG.Color.extra.attrib;"
>

<!-- end of svg-paint-attrib.mod -->

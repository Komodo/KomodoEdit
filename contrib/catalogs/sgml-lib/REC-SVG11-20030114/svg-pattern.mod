<!-- ....................................................................... -->
<!-- SVG 1.1 Pattern Module ................................................ -->
<!-- file: svg-pattern.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-pattern.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ELEMENTS SVG 1.1 Pattern//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-pattern.mod"

     ....................................................................... -->

<!-- Pattern

        pattern

     This module declares markup to provide support for pattern fill.
-->

<!-- Qualified Names (Default) ......................... -->

<!ENTITY % SVG.pattern.qname "pattern" >

<!-- Attribute Collections (Default) ................... -->

<!ENTITY % SVG.Core.attrib "" >
<!ENTITY % SVG.Container.attrib "" >
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
<!ENTITY % SVG.ColorProfile.attrib "" >
<!ENTITY % SVG.Gradient.attrib "" >
<!ENTITY % SVG.Clip.attrib "" >
<!ENTITY % SVG.Mask.attrib "" >
<!ENTITY % SVG.Filter.attrib "" >
<!ENTITY % SVG.FilterColor.attrib "" >
<!ENTITY % SVG.Cursor.attrib "" >
<!ENTITY % SVG.XLink.attrib "" >
<!ENTITY % SVG.External.attrib "" >

<!-- SVG.Pattern.class ................................. -->

<!ENTITY % SVG.Pattern.extra.class "" >

<!ENTITY % SVG.Pattern.class
    "| %SVG.pattern.qname; %SVG.Pattern.extra.class;"
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

<!-- pattern: Pattern Element .......................... -->

<!ENTITY % SVG.pattern.extra.content "" >

<!ENTITY % SVG.pattern.element "INCLUDE" >
<![%SVG.pattern.element;[
<!ENTITY % SVG.pattern.content
    "( %SVG.Description.class; | %SVG.Animation.class; %SVG.Structure.class;
       %SVG.Conditional.class; %SVG.Image.class; %SVG.Style.class;
       %SVG.Shape.class; %SVG.Text.class; %SVG.Marker.class;
       %SVG.ColorProfile.class; %SVG.Gradient.class; %SVG.Pattern.class;
       %SVG.Clip.class; %SVG.Mask.class; %SVG.Filter.class; %SVG.Cursor.class;
       %SVG.Hyperlink.class; %SVG.View.class; %SVG.Script.class;
       %SVG.Font.class; %SVG.pattern.extra.content; )*"
>
<!ELEMENT %SVG.pattern.qname; %SVG.pattern.content; >
<!-- end of SVG.pattern.element -->]]>

<!ENTITY % SVG.pattern.attlist "INCLUDE" >
<![%SVG.pattern.attlist;[
<!ATTLIST %SVG.pattern.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.Style.attrib;
    %SVG.Presentation.attrib;
    %SVG.XLink.attrib;
    %SVG.External.attrib;
    x %Coordinate.datatype; #IMPLIED
    y %Coordinate.datatype; #IMPLIED
    width %Length.datatype; #IMPLIED
    height %Length.datatype; #IMPLIED
    patternUnits ( userSpaceOnUse | objectBoundingBox ) #IMPLIED
    patternContentUnits ( userSpaceOnUse | objectBoundingBox ) #IMPLIED
    patternTransform %TransformList.datatype; #IMPLIED
    viewBox %ViewBoxSpec.datatype; #IMPLIED
    preserveAspectRatio %PreserveAspectRatioSpec.datatype; 'xMidYMid meet'
>
<!-- end of SVG.pattern.attlist -->]]>

<!-- end of svg-pattern.mod -->

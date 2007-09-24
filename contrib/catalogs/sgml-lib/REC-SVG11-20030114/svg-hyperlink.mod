<!-- ....................................................................... -->
<!-- SVG 1.1 Hyperlinking Module ........................................... -->
<!-- file: svg-hyperlink.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-hyperlink.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ELEMENTS SVG 1.1 Hyperlinking//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-hyperlink.mod"

     ....................................................................... -->

<!-- Hyperlinking

        a

     This module declares markup to provide support for hyper linking.
-->

<!-- link to this target -->
<!ENTITY % LinkTarget.datatype "NMTOKEN" >

<!-- Qualified Names (Default) ......................... -->

<!ENTITY % SVG.a.qname "a" >

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
<!ENTITY % SVG.XLinkReplace.attrib "" >
<!ENTITY % SVG.External.attrib "" >

<!-- SVG.Hyperlink.class ............................... -->

<!ENTITY % SVG.Hyperlink.extra.class "" >

<!ENTITY % SVG.Hyperlink.class
    "| %SVG.a.qname; %SVG.Hyperlink.extra.class;"
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

<!-- a: Anchor Element ................................. -->

<!ENTITY % SVG.a.extra.content "" >

<!ENTITY % SVG.a.element "INCLUDE" >
<![%SVG.a.element;[
<!ENTITY % SVG.a.content
    "( #PCDATA | %SVG.Description.class; | %SVG.Animation.class;
       %SVG.Structure.class; %SVG.Conditional.class; %SVG.Image.class;
       %SVG.Style.class; %SVG.Shape.class; %SVG.Text.class; %SVG.Marker.class;
       %SVG.ColorProfile.class; %SVG.Gradient.class; %SVG.Pattern.class;
       %SVG.Clip.class; %SVG.Mask.class; %SVG.Filter.class; %SVG.Cursor.class;
       %SVG.Hyperlink.class; %SVG.View.class; %SVG.Script.class;
       %SVG.Font.class; %SVG.a.extra.content; )*"
>
<!ELEMENT %SVG.a.qname; %SVG.a.content; >
<!-- end of SVG.a.element -->]]>

<!ENTITY % SVG.a.attlist "INCLUDE" >
<![%SVG.a.attlist;[
<!ATTLIST %SVG.a.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.Style.attrib;
    %SVG.Presentation.attrib;
    %SVG.GraphicalEvents.attrib;
    %SVG.XLinkReplace.attrib;
    %SVG.External.attrib;
    transform %TransformList.datatype; #IMPLIED
    target %LinkTarget.datatype; #IMPLIED
>
<!-- end of SVG.a.attlist -->]]>

<!-- end of svg-hyperlink.mod -->

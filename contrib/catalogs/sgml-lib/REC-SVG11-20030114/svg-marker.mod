<!-- ....................................................................... -->
<!-- SVG 1.1 Marker Module ................................................. -->
<!-- file: svg-marker.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-marker.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ELEMENTS SVG 1.1 Marker//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-marker.mod"

     ....................................................................... -->

<!-- Marker

        marker

     This module declares markup to provide support for marker.
-->

<!-- 'marker' property/attribute value (e.g., 'none', <uri>) -->
<!ENTITY % MarkerValue.datatype "CDATA" >

<!-- Qualified Names (Default) ......................... -->

<!ENTITY % SVG.marker.qname "marker" >

<!-- Attribute Collections (Default) ................... -->

<!ENTITY % SVG.Core.attrib "" >
<!ENTITY % SVG.Container.attrib "" >
<!ENTITY % SVG.Style.attrib "" >
<!ENTITY % SVG.Viewport.attrib "" >
<!ENTITY % SVG.Text.attrib "" >
<!ENTITY % SVG.TextContent.attrib "" >
<!ENTITY % SVG.Font.attrib "" >
<!ENTITY % SVG.Paint.attrib "" >
<!ENTITY % SVG.Color.attrib "" >
<!ENTITY % SVG.Opacity.attrib "" >
<!ENTITY % SVG.Graphics.attrib "" >
<!ENTITY % SVG.ColorProfile.attrib "" >
<!ENTITY % SVG.Gradient.attrib "" >
<!ENTITY % SVG.Clip.attrib "" >
<!ENTITY % SVG.Mask.attrib "" >
<!ENTITY % SVG.Filter.attrib "" >
<!ENTITY % SVG.FilterColor.attrib "" >
<!ENTITY % SVG.Cursor.attrib "" >
<!ENTITY % SVG.External.attrib "" >

<!-- SVG.Marker.class .................................. -->

<!ENTITY % SVG.Marker.extra.class "" >

<!ENTITY % SVG.Marker.class
    "| %SVG.marker.qname; %SVG.Marker.extra.class;"
>

<!-- SVG.Marker.attrib ................................. -->

<!ENTITY % SVG.Marker.extra.attrib "" >

<!ENTITY % SVG.Marker.attrib
    "marker-start %MarkerValue.datatype; #IMPLIED
     marker-mid %MarkerValue.datatype; #IMPLIED
     marker-end %MarkerValue.datatype; #IMPLIED
     %SVG.Marker.extra.attrib;"
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

<!-- marker: Marker Element ............................ -->

<!ENTITY % SVG.marker.extra.content "" >

<!ENTITY % SVG.marker.element "INCLUDE" >
<![%SVG.marker.element;[
<!ENTITY % SVG.marker.content
    "( %SVG.Description.class; | %SVG.Animation.class; %SVG.Structure.class;
       %SVG.Conditional.class; %SVG.Image.class; %SVG.Style.class;
       %SVG.Shape.class; %SVG.Text.class; %SVG.Marker.class;
       %SVG.ColorProfile.class; %SVG.Gradient.class; %SVG.Pattern.class;
       %SVG.Clip.class; %SVG.Mask.class; %SVG.Filter.class; %SVG.Cursor.class;
       %SVG.Hyperlink.class; %SVG.View.class; %SVG.Script.class;
       %SVG.Font.class; %SVG.marker.extra.content; )*"
>
<!ELEMENT %SVG.marker.qname; %SVG.marker.content; >
<!-- end of SVG.marker.element -->]]>

<!ENTITY % SVG.marker.attlist "INCLUDE" >
<![%SVG.marker.attlist;[
<!ATTLIST %SVG.marker.qname;
    %SVG.Core.attrib;
    %SVG.Style.attrib;
    %SVG.Presentation.attrib;
    %SVG.External.attrib;
    refX %Coordinate.datatype; #IMPLIED
    refY %Coordinate.datatype; #IMPLIED
    markerUnits ( strokeWidth | userSpaceOnUse ) #IMPLIED
    markerWidth  %Length.datatype; #IMPLIED
    markerHeight %Length.datatype; #IMPLIED
    orient CDATA #IMPLIED
    viewBox %ViewBoxSpec.datatype; #IMPLIED
    preserveAspectRatio %PreserveAspectRatioSpec.datatype; 'xMidYMid meet'
>
<!-- end of SVG.marker.attlist -->]]>

<!-- end of svg-marker.mod -->

<!-- ....................................................................... -->
<!-- SVG 1.1 Basic Structure Module ........................................ -->
<!-- file: svg-basic-structure.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-basic-structure.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ELEMENTS SVG 1.1 Basic Structure//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-basic-structure.mod"

     ....................................................................... -->

<!-- Basic Structure

        svg, g, defs, desc, title, metadata, use

     This module declares the major structural elements and their attributes.
-->

<!-- Qualified Names (Default) ......................... -->

<!ENTITY % SVG.svg.qname "svg" >
<!ENTITY % SVG.g.qname "g" >
<!ENTITY % SVG.defs.qname "defs" >
<!ENTITY % SVG.desc.qname "desc" >
<!ENTITY % SVG.title.qname "title" >
<!ENTITY % SVG.metadata.qname "metadata" >
<!ENTITY % SVG.use.qname "use" >

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
<!ENTITY % SVG.DocumentEvents.attrib "" >
<!ENTITY % SVG.GraphicalEvents.attrib "" >
<!ENTITY % SVG.Cursor.attrib "" >
<!ENTITY % SVG.XLinkEmbed.attrib "" >
<!ENTITY % SVG.External.attrib "" >

<!-- SVG.Description.class ............................. -->

<!ENTITY % SVG.Description.extra.class "" >

<!ENTITY % SVG.Description.class
    "%SVG.desc.qname; | %SVG.title.qname; | %SVG.metadata.qname;
     %SVG.Description.extra.class;"
>

<!-- SVG.Use.class ..................................... -->

<!ENTITY % SVG.Use.extra.class "" >

<!ENTITY % SVG.Use.class
    "| %SVG.use.qname; %SVG.Use.extra.class;"
>

<!-- SVG.Structure.class ............................... -->

<!ENTITY % SVG.Structure.extra.class "" >

<!ENTITY % SVG.Structure.class
    "| %SVG.g.qname; | %SVG.defs.qname; %SVG.Use.class;
       %SVG.Structure.extra.class;"
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

<!-- svg: SVG Document Element ......................... -->

<!ENTITY % SVG.svg.extra.content "" >

<!ENTITY % SVG.svg.element "INCLUDE" >
<![%SVG.svg.element;[
<!ENTITY % SVG.svg.content
    "( %SVG.Description.class; | %SVG.Animation.class; %SVG.Structure.class;
       %SVG.Conditional.class; %SVG.Image.class; %SVG.Style.class;
       %SVG.Shape.class; %SVG.Text.class; %SVG.Marker.class;
       %SVG.ColorProfile.class; %SVG.Gradient.class; %SVG.Pattern.class;
       %SVG.Clip.class; %SVG.Mask.class; %SVG.Filter.class; %SVG.Cursor.class;
       %SVG.Hyperlink.class; %SVG.View.class; %SVG.Script.class;
       %SVG.Font.class; %SVG.svg.extra.content; )*"
>
<!ELEMENT %SVG.svg.qname; %SVG.svg.content; >
<!-- end of SVG.svg.element -->]]>

<!ENTITY % SVG.svg.attlist "INCLUDE" >
<![%SVG.svg.attlist;[
<!ATTLIST %SVG.svg.qname;
    %SVG.xmlns.attrib;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.Style.attrib;
    %SVG.Presentation.attrib;
    %SVG.DocumentEvents.attrib;
    %SVG.GraphicalEvents.attrib;
    %SVG.External.attrib;
    x %Coordinate.datatype; #IMPLIED
    y %Coordinate.datatype; #IMPLIED
    width %Length.datatype; #IMPLIED
    height %Length.datatype; #IMPLIED
    viewBox %ViewBoxSpec.datatype; #IMPLIED
    preserveAspectRatio %PreserveAspectRatioSpec.datatype; 'xMidYMid meet'
    zoomAndPan ( disable | magnify ) 'magnify'
    version %Number.datatype; #FIXED '1.1'
    baseProfile %Text.datatype; #IMPLIED
>
<!-- end of SVG.svg.attlist -->]]>

<!-- g: Group Element .................................. -->

<!ENTITY % SVG.g.extra.content "" >

<!ENTITY % SVG.g.element "INCLUDE" >
<![%SVG.g.element;[
<!ENTITY % SVG.g.content
    "( %SVG.Description.class; | %SVG.Animation.class; %SVG.Structure.class;
       %SVG.Conditional.class; %SVG.Image.class; %SVG.Style.class;
       %SVG.Shape.class; %SVG.Text.class; %SVG.Marker.class;
       %SVG.ColorProfile.class; %SVG.Gradient.class; %SVG.Pattern.class;
       %SVG.Clip.class; %SVG.Mask.class; %SVG.Filter.class; %SVG.Cursor.class;
       %SVG.Hyperlink.class; %SVG.View.class; %SVG.Script.class;
       %SVG.Font.class; %SVG.g.extra.content; )*"
>
<!ELEMENT %SVG.g.qname; %SVG.g.content; >
<!-- end of SVG.g.element -->]]>

<!ENTITY % SVG.g.attlist "INCLUDE" >
<![%SVG.g.attlist;[
<!ATTLIST %SVG.g.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.Style.attrib;
    %SVG.Presentation.attrib;
    %SVG.GraphicalEvents.attrib;
    %SVG.External.attrib;
    transform %TransformList.datatype; #IMPLIED
>
<!-- end of SVG.g.attlist -->]]>

<!-- defs: Definisions Element ......................... -->

<!ENTITY % SVG.defs.extra.content "" >

<!ENTITY % SVG.defs.element "INCLUDE" >
<![%SVG.defs.element;[
<!ENTITY % SVG.defs.content
    "( %SVG.Description.class; | %SVG.Animation.class; %SVG.Structure.class;
       %SVG.Conditional.class; %SVG.Image.class; %SVG.Style.class;
       %SVG.Shape.class; %SVG.Text.class; %SVG.Marker.class;
       %SVG.ColorProfile.class; %SVG.Gradient.class; %SVG.Pattern.class;
       %SVG.Clip.class; %SVG.Mask.class; %SVG.Filter.class; %SVG.Cursor.class;
       %SVG.Hyperlink.class; %SVG.View.class; %SVG.Script.class;
       %SVG.Font.class; %SVG.defs.extra.content; )*"
>
<!ELEMENT %SVG.defs.qname; %SVG.defs.content; >
<!-- end of SVG.defs.element -->]]>

<!ENTITY % SVG.defs.attlist "INCLUDE" >
<![%SVG.defs.attlist;[
<!ATTLIST %SVG.defs.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.Style.attrib;
    %SVG.Presentation.attrib;
    %SVG.GraphicalEvents.attrib;
    %SVG.External.attrib;
    transform %TransformList.datatype; #IMPLIED
>
<!-- end of SVG.defs.attlist -->]]>

<!-- desc: Description Element ......................... -->

<!ENTITY % SVG.desc.extra.content "" >

<!ENTITY % SVG.desc.element "INCLUDE" >
<![%SVG.desc.element;[
<!ENTITY % SVG.desc.content
    "( #PCDATA %SVG.desc.extra.content; )*"
>
<!ELEMENT %SVG.desc.qname; %SVG.desc.content; >
<!-- end of SVG.desc.element -->]]>

<!ENTITY % SVG.desc.attlist "INCLUDE" >
<![%SVG.desc.attlist;[
<!ATTLIST %SVG.desc.qname;
    %SVG.Core.attrib;
    %SVG.Style.attrib;
>
<!-- end of SVG.desc.attlist -->]]>

<!-- title: Title Element .............................. -->

<!ENTITY % SVG.title.extra.content "" >

<!ENTITY % SVG.title.element "INCLUDE" >
<![%SVG.title.element;[
<!ENTITY % SVG.title.content
    "( #PCDATA %SVG.title.extra.content; )*"
>
<!ELEMENT %SVG.title.qname; %SVG.title.content; >
<!-- end of SVG.title.element -->]]>

<!ENTITY % SVG.title.attlist "INCLUDE" >
<![%SVG.title.attlist;[
<!ATTLIST %SVG.title.qname;
    %SVG.Core.attrib;
    %SVG.Style.attrib;
>
<!-- end of SVG.title.attlist -->]]>

<!-- metadata: Metadata Element ........................ -->

<!ENTITY % SVG.metadata.extra.content "" >

<!ENTITY % SVG.metadata.element "INCLUDE" >
<![%SVG.metadata.element;[
<!ENTITY % SVG.metadata.content
    "( #PCDATA %SVG.metadata.extra.content; )*"
>
<!ELEMENT %SVG.metadata.qname; %SVG.metadata.content; >
<!-- end of SVG.metadata.element -->]]>

<!ENTITY % SVG.metadata.attlist "INCLUDE" >
<![%SVG.metadata.attlist;[
<!ATTLIST %SVG.metadata.qname;
    %SVG.Core.attrib;
>
<!-- end of SVG.metadata.attlist -->]]>

<!-- use: Use Element .................................. -->

<!ENTITY % SVG.use.extra.content "" >

<!ENTITY % SVG.use.element "INCLUDE" >
<![%SVG.use.element;[
<!ENTITY % SVG.use.content
    "(( %SVG.Description.class; )*, ( %SVG.Animation.class;
        %SVG.use.extra.content; )*)"
>
<!ELEMENT %SVG.use.qname; %SVG.use.content; >
<!-- end of SVG.use.element -->]]>

<!ENTITY % SVG.use.attlist "INCLUDE" >
<![%SVG.use.attlist;[
<!ATTLIST %SVG.use.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.Style.attrib;
    %SVG.Presentation.attrib;
    %SVG.GraphicalEvents.attrib;
    %SVG.XLinkEmbed.attrib;
    %SVG.External.attrib;
    x %Coordinate.datatype; #IMPLIED
    y %Coordinate.datatype; #IMPLIED
    width %Length.datatype; #IMPLIED
    height %Length.datatype; #IMPLIED
    transform %TransformList.datatype; #IMPLIED
>
<!-- end of SVG.use.attlist -->]]>

<!-- end of svg-basic-structure.mod -->

<!-- ....................................................................... -->
<!-- SVG 1.1 Shape Module .................................................. -->
<!-- file: svg-shape.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-shape.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ELEMENTS SVG 1.1 Shape//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-shape.mod"

     ....................................................................... -->

<!-- Shape

        path, rect, circle, line, ellipse, polyline, polygon

     This module declares markup to provide support for graphical shapes.
-->

<!-- a list of points -->
<!ENTITY % Points.datatype "CDATA" >

<!-- Qualified Names (Default) ......................... -->

<!ENTITY % SVG.path.qname "path" >
<!ENTITY % SVG.rect.qname "rect" >
<!ENTITY % SVG.circle.qname "circle" >
<!ENTITY % SVG.line.qname "line" >
<!ENTITY % SVG.ellipse.qname "ellipse" >
<!ENTITY % SVG.polyline.qname "polyline" >
<!ENTITY % SVG.polygon.qname "polygon" >

<!-- Attribute Collections (Default) ................... -->

<!ENTITY % SVG.Core.attrib "" >
<!ENTITY % SVG.Conditional.attrib "" >
<!ENTITY % SVG.Style.attrib "" >
<!ENTITY % SVG.Paint.attrib "" >
<!ENTITY % SVG.Color.attrib "" >
<!ENTITY % SVG.Opacity.attrib "" >
<!ENTITY % SVG.Graphics.attrib "" >
<!ENTITY % SVG.Marker.attrib "" >
<!ENTITY % SVG.Clip.attrib "" >
<!ENTITY % SVG.Mask.attrib "" >
<!ENTITY % SVG.Filter.attrib "" >
<!ENTITY % SVG.GraphicalEvents.attrib "" >
<!ENTITY % SVG.Cursor.attrib "" >
<!ENTITY % SVG.External.attrib "" >

<!-- SVG.Shape.class ................................... -->

<!ENTITY % SVG.Shape.extra.class "" >

<!ENTITY % SVG.Shape.class
    "| %SVG.path.qname; | %SVG.rect.qname; | %SVG.circle.qname;
     | %SVG.line.qname; | %SVG.ellipse.qname; | %SVG.polyline.qname;
     | %SVG.polygon.qname; %SVG.Shape.extra.class;"
>

<!-- path: Path Element ................................ -->

<!ENTITY % SVG.path.extra.content "" >

<!ENTITY % SVG.path.element "INCLUDE" >
<![%SVG.path.element;[
<!ENTITY % SVG.path.content
    "(( %SVG.Description.class; )*, ( %SVG.Animation.class;
        %SVG.path.extra.content; )*)"
>
<!ELEMENT %SVG.path.qname; %SVG.path.content; >
<!-- end of SVG.path.element -->]]>

<!ENTITY % SVG.path.attlist "INCLUDE" >
<![%SVG.path.attlist;[
<!ATTLIST %SVG.path.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.Style.attrib;
    %SVG.Paint.attrib;
    %SVG.Color.attrib;
    %SVG.Opacity.attrib;
    %SVG.Graphics.attrib;
    %SVG.Marker.attrib;
    %SVG.Clip.attrib;
    %SVG.Mask.attrib;
    %SVG.Filter.attrib;
    %SVG.GraphicalEvents.attrib;
    %SVG.Cursor.attrib;
    %SVG.External.attrib;
    d %PathData.datatype; #REQUIRED
    pathLength %Number.datatype; #IMPLIED
    transform %TransformList.datatype; #IMPLIED
>
<!-- end of SVG.path.attlist -->]]>

<!-- rect: Rectangle Element ........................... -->

<!ENTITY % SVG.rect.extra.content "" >

<!ENTITY % SVG.rect.element "INCLUDE" >
<![%SVG.rect.element;[
<!ENTITY % SVG.rect.content
    "(( %SVG.Description.class; )*, ( %SVG.Animation.class;
        %SVG.rect.extra.content; )*)"
>
<!ELEMENT %SVG.rect.qname; %SVG.rect.content; >
<!-- end of SVG.rect.element -->]]>

<!ENTITY % SVG.rect.attlist "INCLUDE" >
<![%SVG.rect.attlist;[
<!ATTLIST %SVG.rect.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.Style.attrib;
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
    x %Coordinate.datatype; #IMPLIED
    y %Coordinate.datatype; #IMPLIED
    width %Length.datatype; #REQUIRED
    height %Length.datatype; #REQUIRED
    rx %Length.datatype; #IMPLIED
    ry %Length.datatype; #IMPLIED
    transform %TransformList.datatype; #IMPLIED
>
<!-- end of SVG.rect.attlist -->]]>

<!-- circle: Circle Element ............................ -->

<!ENTITY % SVG.circle.extra.content "" >

<!ENTITY % SVG.circle.element "INCLUDE" >
<![%SVG.circle.element;[
<!ENTITY % SVG.circle.content
    "(( %SVG.Description.class; )*, ( %SVG.Animation.class;
        %SVG.circle.extra.content; )*)"
>
<!ELEMENT %SVG.circle.qname; %SVG.circle.content; >
<!-- end of SVG.circle.element -->]]>

<!ENTITY % SVG.circle.attlist "INCLUDE" >
<![%SVG.circle.attlist;[
<!ATTLIST %SVG.circle.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.Style.attrib;
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
    cx %Coordinate.datatype; #IMPLIED
    cy %Coordinate.datatype; #IMPLIED
    r %Length.datatype; #REQUIRED
    transform %TransformList.datatype; #IMPLIED
>
<!-- end of SVG.circle.attlist -->]]>

<!-- line: Line Element ................................ -->

<!ENTITY % SVG.line.extra.content "" >

<!ENTITY % SVG.line.element "INCLUDE" >
<![%SVG.line.element;[
<!ENTITY % SVG.line.content
    "(( %SVG.Description.class; )*, ( %SVG.Animation.class;
        %SVG.line.extra.content; )*)"
>
<!ELEMENT %SVG.line.qname; %SVG.line.content; >
<!-- end of SVG.line.element -->]]>

<!ENTITY % SVG.line.attlist "INCLUDE" >
<![%SVG.line.attlist;[
<!ATTLIST %SVG.line.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.Style.attrib;
    %SVG.Paint.attrib;
    %SVG.Color.attrib;
    %SVG.Opacity.attrib;
    %SVG.Graphics.attrib;
    %SVG.Marker.attrib;
    %SVG.Clip.attrib;
    %SVG.Mask.attrib;
    %SVG.Filter.attrib;
    %SVG.GraphicalEvents.attrib;
    %SVG.Cursor.attrib;
    %SVG.External.attrib;
    x1 %Coordinate.datatype; #IMPLIED
    y1 %Coordinate.datatype; #IMPLIED
    x2 %Coordinate.datatype; #IMPLIED
    y2 %Coordinate.datatype; #IMPLIED
    transform %TransformList.datatype; #IMPLIED
>
<!-- end of SVG.line.attlist -->]]>

<!-- ellipse: Ellipse Element .......................... -->

<!ENTITY % SVG.ellipse.extra.content "" >

<!ENTITY % SVG.ellipse.element "INCLUDE" >
<![%SVG.ellipse.element;[
<!ENTITY % SVG.ellipse.content
    "(( %SVG.Description.class; )*, ( %SVG.Animation.class;
        %SVG.ellipse.extra.content; )*)"
>
<!ELEMENT %SVG.ellipse.qname; %SVG.ellipse.content; >
<!-- end of SVG.ellipse.element -->]]>

<!ENTITY % SVG.ellipse.attlist "INCLUDE" >
<![%SVG.ellipse.attlist;[
<!ATTLIST %SVG.ellipse.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.Style.attrib;
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
    cx %Coordinate.datatype; #IMPLIED
    cy %Coordinate.datatype; #IMPLIED
    rx %Length.datatype; #REQUIRED
    ry %Length.datatype; #REQUIRED
    transform %TransformList.datatype; #IMPLIED
>
<!-- end of SVG.ellipse.attlist -->]]>

<!-- polyline: Polyline Element ........................ -->

<!ENTITY % SVG.polyline.extra.content "" >

<!ENTITY % SVG.polyline.element "INCLUDE" >
<![%SVG.polyline.element;[
<!ENTITY % SVG.polyline.content
    "(( %SVG.Description.class; )*, ( %SVG.Animation.class;
        %SVG.polyline.extra.content; )*)"
>
<!ELEMENT %SVG.polyline.qname; %SVG.polyline.content; >
<!-- end of SVG.polyline.element -->]]>

<!ENTITY % SVG.polyline.attlist "INCLUDE" >
<![%SVG.polyline.attlist;[
<!ATTLIST %SVG.polyline.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.Style.attrib;
    %SVG.Paint.attrib;
    %SVG.Color.attrib;
    %SVG.Opacity.attrib;
    %SVG.Graphics.attrib;
    %SVG.Marker.attrib;
    %SVG.Clip.attrib;
    %SVG.Mask.attrib;
    %SVG.Filter.attrib;
    %SVG.GraphicalEvents.attrib;
    %SVG.Cursor.attrib;
    %SVG.External.attrib;
    points %Points.datatype; #REQUIRED
    transform %TransformList.datatype; #IMPLIED
>
<!-- end of SVG.polyline.attlist -->]]>

<!-- polygon: Polygon Element .......................... -->

<!ENTITY % SVG.polygon.extra.content "" >

<!ENTITY % SVG.polygon.element "INCLUDE" >
<![%SVG.polygon.element;[
<!ENTITY % SVG.polygon.content
    "(( %SVG.Description.class; )*, ( %SVG.Animation.class;
        %SVG.polygon.extra.content; )*)"
>
<!ELEMENT %SVG.polygon.qname; %SVG.polygon.content; >
<!-- end of SVG.polygon.element -->]]>

<!ENTITY % SVG.polygon.attlist "INCLUDE" >
<![%SVG.polygon.attlist;[
<!ATTLIST %SVG.polygon.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.Style.attrib;
    %SVG.Paint.attrib;
    %SVG.Color.attrib;
    %SVG.Opacity.attrib;
    %SVG.Graphics.attrib;
    %SVG.Marker.attrib;
    %SVG.Clip.attrib;
    %SVG.Mask.attrib;
    %SVG.Filter.attrib;
    %SVG.GraphicalEvents.attrib;
    %SVG.Cursor.attrib;
    %SVG.External.attrib;
    points %Points.datatype; #REQUIRED
    transform %TransformList.datatype; #IMPLIED
>
<!-- end of SVG.polygon.attlist -->]]>

<!-- end of svg-shape.mod -->

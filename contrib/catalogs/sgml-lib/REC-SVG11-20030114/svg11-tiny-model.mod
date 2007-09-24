<!-- ....................................................................... -->
<!-- SVG 1.1 Tiny Document Model Module .................................... -->
<!-- file: svg11-tiny-model.mod

     This is SVG Tiny, a proper subset of SVG.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg11-tiny-model.mod,v 1.1.2.1 2003/06/08 20:19:48 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ENTITIES SVG 1.1 Tiny Document Model//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11-tiny-model.mod"

     ....................................................................... -->

<!-- SVG 1.1 Tiny Document Model

     This module describes the groupings of elements that make up
     common content models for SVG elements.
-->

<!-- Content Models (Default) .......................... -->

<!ENTITY % SVG.Style.class "" >
<!ENTITY % SVG.TextContent.class "" >
<!ENTITY % SVG.Marker.class "" >
<!ENTITY % SVG.ColorProfile.class "" >
<!ENTITY % SVG.Gradient.class "" >
<!ENTITY % SVG.Pattern.class "" >
<!ENTITY % SVG.Clip.class "" >
<!ENTITY % SVG.Mask.class "" >
<!ENTITY % SVG.Filter.class "" >
<!ENTITY % SVG.FilterPrimitive.class "" >
<!ENTITY % SVG.Cursor.class "" >
<!ENTITY % SVG.View.class "" >
<!ENTITY % SVG.Script.class "" >

<!-- module: svg-basic-structure.mod ................... -->

<!ENTITY % SVG.Description.extra.class "" >
<!ENTITY % SVG.Description.class
    "%SVG.desc.qname; | %SVG.title.qname; | %SVG.metadata.qname;
     %SVG.Description.extra.class;"
>

<!ENTITY % SVG.Use.extra.class "" >
<!ENTITY % SVG.Use.class
    "| %SVG.use.qname; %SVG.Use.extra.class;"
>

<!ENTITY % SVG.Structure.extra.class "" >
<!ENTITY % SVG.Structure.class
    "| %SVG.g.qname; | %SVG.defs.qname; %SVG.Use.class;
       %SVG.Structure.extra.class;"
>

<!-- module: svg-conditional.mod ....................... -->

<!ENTITY % SVG.Conditional.extra.class "" >
<!ENTITY % SVG.Conditional.class
    "| %SVG.switch.qname; %SVG.Conditional.extra.class;"
>

<!-- module: svg-image.mod ............................. -->

<!ENTITY % SVG.Image.extra.class "" >
<!ENTITY % SVG.Image.class
    "| %SVG.image.qname; %SVG.Image.extra.class;"
>

<!-- module: svg-shape.mod ............................. -->

<!ENTITY % SVG.Shape.extra.class "" >
<!ENTITY % SVG.Shape.class
    "| %SVG.path.qname; | %SVG.rect.qname; | %SVG.circle.qname;
     | %SVG.line.qname; | %SVG.ellipse.qname; | %SVG.polyline.qname;
     | %SVG.polygon.qname; %SVG.Shape.extra.class;"
>

<!-- module: svg-basic-text.mod ........................ -->

<!ENTITY % SVG.Text.extra.class "" >
<!ENTITY % SVG.Text.class
    "| %SVG.text.qname; %SVG.Text.extra.class;"
>

<!-- module: svg-hyperlink.mod ......................... -->

<!ENTITY % SVG.Hyperlink.extra.class "" >
<!ENTITY % SVG.Hyperlink.class
    "| %SVG.a.qname; %SVG.Hyperlink.extra.class;"
>

<!-- module: svg-animation.mod ......................... -->

<!ENTITY % SVG.Animation.extra.class "" >
<!ENTITY % SVG.Animation.class
    "%SVG.animate.qname; | %SVG.set.qname; | %SVG.animateMotion.qname; |
     %SVG.animateColor.qname; | %SVG.animateTransform.qname;
     %SVG.Animation.extra.class;"
>

<!-- module: svg-basic-font.mod ........................ -->

<!ENTITY % SVG.Font.extra.class "" >
<!ENTITY % SVG.Font.class
    "| %SVG.font.qname; | %SVG.font-face.qname; %SVG.Font.extra.class;"
>

<!-- module: svg-extensibility.mod ..................... -->

<!ENTITY % SVG.Extensibility.extra.class "" >
<!ENTITY % SVG.Extensibility.class
    "| %SVG.foreignObject.qname; %SVG.Extensibility.extra.class;"
>

<!-- end of svg11-tiny-model.mod -->

<!-- ....................................................................... -->
<!-- SVG 1.1 Document Model Module ......................................... -->
<!-- file: svg11-model.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg11-model.mod,v 1.1.2.1 2003/06/08 20:19:48 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ENTITIES SVG 1.1 Document Model//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11-model.mod"

     ....................................................................... -->

<!-- SVG 1.1 Document Model

     This module describes the groupings of elements that make up
     common content models for SVG elements.
-->

<!-- module: svg-structure.mod ......................... -->

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
    "| %SVG.svg.qname; | %SVG.g.qname; | %SVG.defs.qname; | %SVG.symbol.qname;
       %SVG.Use.class; %SVG.Structure.extra.class;"
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

<!-- module: svg-style.mod ............................. -->

<!ENTITY % SVG.Style.extra.class "" >
<!ENTITY % SVG.Style.class
    "| %SVG.style.qname; %SVG.Style.extra.class;"
>

<!-- module: svg-shape.mod ............................. -->

<!ENTITY % SVG.Shape.extra.class "" >
<!ENTITY % SVG.Shape.class
    "| %SVG.path.qname; | %SVG.rect.qname; | %SVG.circle.qname;
     | %SVG.line.qname; | %SVG.ellipse.qname; | %SVG.polyline.qname;
     | %SVG.polygon.qname; %SVG.Shape.extra.class;"
>

<!-- module: svg-text.mod .............................. -->

<!ENTITY % SVG.Text.extra.class "" >
<!ENTITY % SVG.Text.class
    "| %SVG.text.qname; | %SVG.altGlyphDef.qname; %SVG.Text.extra.class;"
>

<!ENTITY % SVG.TextContent.extra.class "" >
<!ENTITY % SVG.TextContent.class
    "| %SVG.tspan.qname; | %SVG.tref.qname; | %SVG.textPath.qname;
     | %SVG.altGlyph.qname; %SVG.TextContent.extra.class;"
>

<!-- module: svg-marker.mod ............................ -->

<!ENTITY % SVG.Marker.extra.class "" >
<!ENTITY % SVG.Marker.class
    "| %SVG.marker.qname; %SVG.Marker.extra.class;"
>

<!-- module: svg-profile.mod ........................... -->

<!ENTITY % SVG.ColorProfile.extra.class "" >
<!ENTITY % SVG.ColorProfile.class
    "| %SVG.color-profile.qname; %SVG.ColorProfile.extra.class;"
>

<!-- module: svg-gradient.mod .......................... -->

<!ENTITY % SVG.Gradient.extra.class "" >
<!ENTITY % SVG.Gradient.class
    "| %SVG.linearGradient.qname; | %SVG.radialGradient.qname;
       %SVG.Gradient.extra.class;"
>

<!-- module: svg-pattern.mod ........................... -->

<!ENTITY % SVG.Pattern.extra.class "" >
<!ENTITY % SVG.Pattern.class
    "| %SVG.pattern.qname; %SVG.Pattern.extra.class;"
>

<!-- module: svg-clip.mod .............................. -->

<!ENTITY % SVG.Clip.extra.class "" >
<!ENTITY % SVG.Clip.class
    "| %SVG.clipPath.qname; %SVG.Clip.extra.class;"
>

<!-- module: svg-mask.mod .............................. -->

<!ENTITY % SVG.Mask.extra.class "" >
<!ENTITY % SVG.Mask.class
    "| %SVG.mask.qname; %SVG.Mask.extra.class;"
>

<!-- module: svg-filter.mod ............................ -->

<!ENTITY % SVG.Filter.extra.class "" >
<!ENTITY % SVG.Filter.class
    "| %SVG.filter.qname; %SVG.Filter.extra.class;"
>

<!ENTITY % SVG.FilterPrimitive.extra.class "" >
<!ENTITY % SVG.FilterPrimitive.class
    "| %SVG.feBlend.qname; | %SVG.feColorMatrix.qname;
     | %SVG.feComponentTransfer.qname; | %SVG.feComposite.qname;
     | %SVG.feConvolveMatrix.qname; | %SVG.feDiffuseLighting.qname;
     | %SVG.feDisplacementMap.qname; | %SVG.feFlood.qname;
     | %SVG.feGaussianBlur.qname; | %SVG.feImage.qname; | %SVG.feMerge.qname;
     | %SVG.feMorphology.qname; | %SVG.feOffset.qname;
     | %SVG.feSpecularLighting.qname; | %SVG.feTile.qname;
     | %SVG.feTurbulence.qname; %SVG.FilterPrimitive.extra.class;"
>

<!-- module: svg-cursor.mod ............................ -->

<!ENTITY % SVG.Cursor.extra.class "" >
<!ENTITY % SVG.Cursor.class
    "| %SVG.cursor.qname; %SVG.Cursor.extra.class;"
>

<!-- module: svg-hyperlink.mod ......................... -->

<!ENTITY % SVG.Hyperlink.extra.class "" >
<!ENTITY % SVG.Hyperlink.class
    "| %SVG.a.qname; %SVG.Hyperlink.extra.class;"
>

<!-- module: svg-view.mod .............................. -->

<!ENTITY % SVG.View.extra.class "" >
<!ENTITY % SVG.View.class
    "| %SVG.view.qname; %SVG.View.extra.class;"
>

<!-- module: svg-script.mod ............................ -->

<!ENTITY % SVG.Script.extra.class "" >
<!ENTITY % SVG.Script.class
    "| %SVG.script.qname; %SVG.Script.extra.class;"
>

<!-- module: svg-animation.mod ......................... -->

<!ENTITY % SVG.Animation.extra.class "" >
<!ENTITY % SVG.Animation.class
    "%SVG.animate.qname; | %SVG.set.qname; | %SVG.animateMotion.qname; |
     %SVG.animateColor.qname; | %SVG.animateTransform.qname;
     %SVG.Animation.extra.class;"
>

<!-- module: svg-font.mod .............................. -->

<!ENTITY % SVG.Font.extra.class "" >
<!ENTITY % SVG.Font.class
    "| %SVG.font.qname; | %SVG.font-face.qname; %SVG.Font.extra.class;"
>

<!-- module: svg-extensibility.mod ..................... -->

<!ENTITY % SVG.Extensibility.extra.class "" >
<!ENTITY % SVG.Extensibility.class
    "| %SVG.foreignObject.qname; %SVG.Extensibility.extra.class;"
>

<!-- end of svg11-model.mod -->

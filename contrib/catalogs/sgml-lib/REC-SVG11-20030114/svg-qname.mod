<!-- ....................................................................... -->
<!-- SVG 1.1 Qualified Name Module ......................................... -->
<!-- file: svg-qname.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-qname.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ENTITIES SVG 1.1 Qualified Name//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-qname.mod"

     ....................................................................... -->

<!-- Qualified Name

     This module is contained in two parts, labeled Section 'A' and 'B':

        Section A declares parameter entities to support namespace-
        qualified names, namespace declarations, and name prefixing
        for SVG and extensions.

        Section B declares parameter entities used to provide
        namespace-qualified names for all SVG element types:
-->

<!-- Section A: SVG XML Namespace Framework :::::::::::::::::::::: -->

<!-- 1. Declare a %SVG.prefixed; conditional section keyword, used
        to activate namespace prefixing. The default value should
        inherit '%NS.prefixed;' from the DTD driver, so that unless
        overridden, the default behaviour follows the overall DTD
        prefixing scheme.
-->
<!ENTITY % NS.prefixed "IGNORE" >
<!ENTITY % SVG.prefixed "%NS.prefixed;" >

<!-- 2. Declare a parameter entity (eg., %SVG.xmlns;) containing
        the URI reference used to identify the SVG namespace:
-->
<!ENTITY % SVG.xmlns "http://www.w3.org/2000/svg" >
<!ENTITY % XLINK.xmlns "http://www.w3.org/1999/xlink" >

<!-- 3. Declare parameter entities (eg., %SVG.prefix;) containing
        the default namespace prefix string(s) to use when prefixing
        is enabled. This may be overridden in the DTD driver or the
        internal subset of an document instance. If no default prefix
        is desired, this may be declared as an empty string.
-->
<!ENTITY % SVG.prefix "" >
<!ENTITY % XLINK.prefix "xlink" >

<!-- 4. Declare parameter entities (eg., %SVG.pfx;) containing the
        colonized prefix(es) (eg., '%SVG.prefix;:') used when
        prefixing is active, an empty string when it is not.
-->
<![%SVG.prefixed;[
<!ENTITY % SVG.pfx "%SVG.prefix;:" >
]]>
<!ENTITY % SVG.pfx "" >
<!ENTITY % XLINK.pfx "%XLINK.prefix;:" >

<!-- 5. The parameter entity %SVG.xmlns.extra.attrib; may be
        redeclared to contain any non-SVG namespace declaration
        attributes for namespaces embedded in SVG. The default
        is an empty string.
-->
<!ENTITY % SVG.xmlns.extra.attrib "" >

<!-- Declare a parameter entity XLINK.xmlns.attrib containing
     the XML Namespace declarations for XLink.
-->
<!ENTITY % XLINK.xmlns.attrib
     "xmlns:%XLINK.prefix; %URI.datatype; #FIXED '%XLINK.xmlns;'"
>

<!-- Declare a parameter entity %NS.decl.attrib; containing
     all XML Namespace declarations used in the DTD, plus the
     xmlns declaration for SVG, its form dependent on whether
     prefixing is active.
-->
<![%SVG.prefixed;[
<!ENTITY % NS.decl.attrib
    "xmlns:%SVG.prefix; %URI.datatype; #FIXED '%SVG.xmlns;'
     %XLINK.xmlns.attrib;
     %SVG.xmlns.extra.attrib;"
>
]]>
<!ENTITY % NS.decl.attrib
    "%XLINK.xmlns.attrib;
     %SVG.xmlns.extra.attrib;"
>

<!-- Declare a parameter entity %SVG.xmlns.attrib; containing
     all XML namespace declaration attributes used by SVG,
     including a default xmlns attribute when prefixing is
     inactive.
-->
<![%SVG.prefixed;[
<!ENTITY % SVG.xmlns.attrib
     "%NS.decl.attrib;"
>
]]>
<!ENTITY % SVG.xmlns.attrib
     "xmlns %URI.datatype; #FIXED '%SVG.xmlns;'
      %XLINK.xmlns.attrib;"
>

<!-- Section B: SVG Qualified Names :::::::::::::::::::::::::::::: -->

<!-- 6. This section declares parameter entities used to provide
        namespace-qualified names for all SVG element types.
-->

<!-- module: svg-structure.mod ......................... -->

<!ENTITY % SVG.svg.qname "%SVG.pfx;svg" >
<!ENTITY % SVG.g.qname "%SVG.pfx;g" >
<!ENTITY % SVG.defs.qname "%SVG.pfx;defs" >
<!ENTITY % SVG.desc.qname "%SVG.pfx;desc" >
<!ENTITY % SVG.title.qname "%SVG.pfx;title" >
<!ENTITY % SVG.metadata.qname "%SVG.pfx;metadata" >
<!ENTITY % SVG.symbol.qname "%SVG.pfx;symbol" >
<!ENTITY % SVG.use.qname "%SVG.pfx;use" >

<!-- module: svg-conditional.mod ....................... -->

<!ENTITY % SVG.switch.qname "%SVG.pfx;switch" >

<!-- module: svg-image.mod ............................. -->

<!ENTITY % SVG.image.qname "%SVG.pfx;image" >

<!-- module: svg-style.mod ............................. -->

<!ENTITY % SVG.style.qname "%SVG.pfx;style" >

<!-- module: svg-shape.mod ............................. -->

<!ENTITY % SVG.path.qname "%SVG.pfx;path" >
<!ENTITY % SVG.rect.qname "%SVG.pfx;rect" >
<!ENTITY % SVG.circle.qname "%SVG.pfx;circle" >
<!ENTITY % SVG.line.qname "%SVG.pfx;line" >
<!ENTITY % SVG.ellipse.qname "%SVG.pfx;ellipse" >
<!ENTITY % SVG.polyline.qname "%SVG.pfx;polyline" >
<!ENTITY % SVG.polygon.qname "%SVG.pfx;polygon" >

<!-- module: svg-text.mod .............................. -->

<!ENTITY % SVG.text.qname "%SVG.pfx;text" >
<!ENTITY % SVG.tspan.qname "%SVG.pfx;tspan" >
<!ENTITY % SVG.tref.qname "%SVG.pfx;tref" >
<!ENTITY % SVG.textPath.qname "%SVG.pfx;textPath" >
<!ENTITY % SVG.altGlyph.qname "%SVG.pfx;altGlyph" >
<!ENTITY % SVG.altGlyphDef.qname "%SVG.pfx;altGlyphDef" >
<!ENTITY % SVG.altGlyphItem.qname "%SVG.pfx;altGlyphItem" >
<!ENTITY % SVG.glyphRef.qname "%SVG.pfx;glyphRef" >

<!-- module: svg-marker.mod ............................ -->

<!ENTITY % SVG.marker.qname "%SVG.pfx;marker" >

<!-- module: svg-profile.mod ........................... -->

<!ENTITY % SVG.color-profile.qname "%SVG.pfx;color-profile" >

<!-- module: svg-gradient.mod .......................... -->

<!ENTITY % SVG.linearGradient.qname "%SVG.pfx;linearGradient" >
<!ENTITY % SVG.radialGradient.qname "%SVG.pfx;radialGradient" >
<!ENTITY % SVG.stop.qname "%SVG.pfx;stop" >

<!-- module: svg-pattern.mod ........................... -->

<!ENTITY % SVG.pattern.qname "%SVG.pfx;pattern" >

<!-- module: svg-clip.mod .............................. -->

<!ENTITY % SVG.clipPath.qname "%SVG.pfx;clipPath" >

<!-- module: svg-mask.mod .............................. -->

<!ENTITY % SVG.mask.qname "%SVG.pfx;mask" >

<!-- module: svg-filter.mod ............................ -->

<!ENTITY % SVG.filter.qname "%SVG.pfx;filter" >
<!ENTITY % SVG.feBlend.qname "%SVG.pfx;feBlend" >
<!ENTITY % SVG.feColorMatrix.qname "%SVG.pfx;feColorMatrix" >
<!ENTITY % SVG.feComponentTransfer.qname "%SVG.pfx;feComponentTransfer" >
<!ENTITY % SVG.feComposite.qname "%SVG.pfx;feComposite" >
<!ENTITY % SVG.feConvolveMatrix.qname "%SVG.pfx;feConvolveMatrix" >
<!ENTITY % SVG.feDiffuseLighting.qname "%SVG.pfx;feDiffuseLighting" >
<!ENTITY % SVG.feDisplacementMap.qname "%SVG.pfx;feDisplacementMap" >
<!ENTITY % SVG.feFlood.qname "%SVG.pfx;feFlood" >
<!ENTITY % SVG.feGaussianBlur.qname "%SVG.pfx;feGaussianBlur" >
<!ENTITY % SVG.feImage.qname "%SVG.pfx;feImage" >
<!ENTITY % SVG.feMerge.qname "%SVG.pfx;feMerge" >
<!ENTITY % SVG.feMergeNode.qname "%SVG.pfx;feMergeNode" >
<!ENTITY % SVG.feMorphology.qname "%SVG.pfx;feMorphology" >
<!ENTITY % SVG.feOffset.qname "%SVG.pfx;feOffset" >
<!ENTITY % SVG.feSpecularLighting.qname "%SVG.pfx;feSpecularLighting" >
<!ENTITY % SVG.feTile.qname "%SVG.pfx;feTile" >
<!ENTITY % SVG.feTurbulence.qname "%SVG.pfx;feTurbulence" >
<!ENTITY % SVG.feDistantLight.qname "%SVG.pfx;feDistantLight" >
<!ENTITY % SVG.fePointLight.qname "%SVG.pfx;fePointLight" >
<!ENTITY % SVG.feSpotLight.qname "%SVG.pfx;feSpotLight" >
<!ENTITY % SVG.feFuncR.qname "%SVG.pfx;feFuncR" >
<!ENTITY % SVG.feFuncG.qname "%SVG.pfx;feFuncG" >
<!ENTITY % SVG.feFuncB.qname "%SVG.pfx;feFuncB" >
<!ENTITY % SVG.feFuncA.qname "%SVG.pfx;feFuncA" >

<!-- module: svg-cursor.mod ............................ -->

<!ENTITY % SVG.cursor.qname "%SVG.pfx;cursor" >

<!-- module: svg-hyperlink.mod ......................... -->

<!ENTITY % SVG.a.qname "%SVG.pfx;a" >

<!-- module: svg-view.mod .............................. -->

<!ENTITY % SVG.view.qname "%SVG.pfx;view" >

<!-- module: svg-script.mod ............................ -->

<!ENTITY % SVG.script.qname "%SVG.pfx;script" >

<!-- module: svg-animation.mod ......................... -->

<!ENTITY % SVG.animate.qname "%SVG.pfx;animate" >
<!ENTITY % SVG.set.qname "%SVG.pfx;set" >
<!ENTITY % SVG.animateMotion.qname "%SVG.pfx;animateMotion" >
<!ENTITY % SVG.animateColor.qname "%SVG.pfx;animateColor" >
<!ENTITY % SVG.animateTransform.qname "%SVG.pfx;animateTransform" >
<!ENTITY % SVG.mpath.qname "%SVG.pfx;mpath" >

<!-- module: svg-font.mod .............................. -->

<!ENTITY % SVG.font.qname "%SVG.pfx;font" >
<!ENTITY % SVG.font-face.qname "%SVG.pfx;font-face" >
<!ENTITY % SVG.glyph.qname "%SVG.pfx;glyph" >
<!ENTITY % SVG.missing-glyph.qname "%SVG.pfx;missing-glyph" >
<!ENTITY % SVG.hkern.qname "%SVG.pfx;hkern" >
<!ENTITY % SVG.vkern.qname "%SVG.pfx;vkern" >
<!ENTITY % SVG.font-face-src.qname "%SVG.pfx;font-face-src" >
<!ENTITY % SVG.font-face-uri.qname "%SVG.pfx;font-face-uri" >
<!ENTITY % SVG.font-face-format.qname "%SVG.pfx;font-face-format" >
<!ENTITY % SVG.font-face-name.qname "%SVG.pfx;font-face-name" >
<!ENTITY % SVG.definition-src.qname "%SVG.pfx;definition-src" >

<!-- module: svg-extensibility.mod ..................... -->

<!ENTITY % SVG.foreignObject.qname "%SVG.pfx;foreignObject" >

<!-- end of svg-qname.mod -->

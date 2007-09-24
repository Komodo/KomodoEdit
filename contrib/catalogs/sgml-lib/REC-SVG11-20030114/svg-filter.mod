<!-- ....................................................................... -->
<!-- SVG 1.1 Filter Module ................................................. -->
<!-- file: svg-filter.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-filter.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ELEMENTS SVG 1.1 Filter//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-filter.mod"

     ....................................................................... -->

<!-- Filter

        filter, feBlend, feColorMatrix, feComponentTransfer, feComposite,
        feConvolveMatrix, feDiffuseLighting, feDisplacementMap, feFlood,
        feGaussianBlur, feImage, feMerge, feMergeNode, feMorphology, feOffset,
        feSpecularLighting, feTile, feTurbulence, feDistantLight, fePointLight,
        feSpotLight, feFuncR, feFuncG, feFuncB, feFuncA

     This module declares markup to provide support for filter effect.
-->

<!-- 'filter' property/attribute value (e.g., 'none', <uri>) -->
<!ENTITY % FilterValue.datatype "CDATA" >

<!-- list of <number>s, but at least one and at most two -->
<!ENTITY % NumberOptionalNumber.datatype "CDATA" >

<!-- Qualified Names (Default) ......................... -->

<!ENTITY % SVG.filter.qname "filter" >
<!ENTITY % SVG.feBlend.qname "feBlend" >
<!ENTITY % SVG.feColorMatrix.qname "feColorMatrix" >
<!ENTITY % SVG.feComponentTransfer.qname "feComponentTransfer" >
<!ENTITY % SVG.feComposite.qname "feComposite" >
<!ENTITY % SVG.feConvolveMatrix.qname "feConvolveMatrix" >
<!ENTITY % SVG.feDiffuseLighting.qname "feDiffuseLighting" >
<!ENTITY % SVG.feDisplacementMap.qname "feDisplacementMap" >
<!ENTITY % SVG.feFlood.qname "feFlood" >
<!ENTITY % SVG.feGaussianBlur.qname "feGaussianBlur" >
<!ENTITY % SVG.feImage.qname "feImage" >
<!ENTITY % SVG.feMerge.qname "feMerge" >
<!ENTITY % SVG.feMergeNode.qname "feMergeNode" >
<!ENTITY % SVG.feMorphology.qname "feMorphology" >
<!ENTITY % SVG.feOffset.qname "feOffset" >
<!ENTITY % SVG.feSpecularLighting.qname "feSpecularLighting" >
<!ENTITY % SVG.feTile.qname "feTile" >
<!ENTITY % SVG.feTurbulence.qname "feTurbulence" >
<!ENTITY % SVG.feDistantLight.qname "feDistantLight" >
<!ENTITY % SVG.fePointLight.qname "fePointLight" >
<!ENTITY % SVG.feSpotLight.qname "feSpotLight" >
<!ENTITY % SVG.feFuncR.qname "feFuncR" >
<!ENTITY % SVG.feFuncG.qname "feFuncG" >
<!ENTITY % SVG.feFuncB.qname "feFuncB" >
<!ENTITY % SVG.feFuncA.qname "feFuncA" >

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
<!ENTITY % SVG.Marker.attrib "" >
<!ENTITY % SVG.ColorProfile.attrib "" >
<!ENTITY % SVG.Gradient.attrib "" >
<!ENTITY % SVG.Clip.attrib "" >
<!ENTITY % SVG.Mask.attrib "" >
<!ENTITY % SVG.Cursor.attrib "" >
<!ENTITY % SVG.XLink.attrib "" >
<!ENTITY % SVG.XLinkEmbed.attrib "" >
<!ENTITY % SVG.External.attrib "" >

<!-- SVG.Filter.class .................................. -->

<!ENTITY % SVG.Filter.extra.class "" >

<!ENTITY % SVG.Filter.class
    "| %SVG.filter.qname; %SVG.Filter.extra.class;"
>

<!-- SVG.FilterPrimitive.class ......................... -->

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

<!-- SVG.Filter.attrib ................................. -->

<!ENTITY % SVG.Filter.extra.attrib "" >

<!ENTITY % SVG.Filter.attrib
    "filter %FilterValue.datatype; #IMPLIED
     %SVG.Filter.extra.attrib;"
>

<!-- SVG.FilterColor.attrib ............................ -->

<!ENTITY % SVG.FilterColor.extra.attrib "" >

<!ENTITY % SVG.FilterColor.attrib
    "color-interpolation-filters ( auto | sRGB | linearRGB | inherit )
                                   #IMPLIED
     %SVG.FilterColor.extra.attrib;"
>

<!-- SVG.FilterPrimitive.attrib ........................ -->

<!ENTITY % SVG.FilterPrimitive.extra.attrib "" >

<!ENTITY % SVG.FilterPrimitive.attrib
    "x %Coordinate.datatype; #IMPLIED
     y %Coordinate.datatype; #IMPLIED
     width %Length.datatype; #IMPLIED
     height %Length.datatype; #IMPLIED
     result CDATA #IMPLIED
     %SVG.FilterPrimitive.extra.attrib;"
>

<!-- SVG.FilterPrimitiveWithIn.attrib .................. -->

<!ENTITY % SVG.FilterPrimitiveWithIn.extra.attrib "" >

<!ENTITY % SVG.FilterPrimitiveWithIn.attrib
    "%SVG.FilterPrimitive.attrib;
     in CDATA #IMPLIED
     %SVG.FilterPrimitiveWithIn.extra.attrib;"
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

<!-- filter: Filter Element ............................ -->

<!ENTITY % SVG.filter.extra.content "" >

<!ENTITY % SVG.filter.element "INCLUDE" >
<![%SVG.filter.element;[
<!ENTITY % SVG.filter.content
    "(( %SVG.Description.class; )*, ( %SVG.animate.qname; | %SVG.set.qname;
        %SVG.FilterPrimitive.class; %SVG.filter.extra.content; )*)"
>
<!ELEMENT %SVG.filter.qname; %SVG.filter.content; >
<!-- end of SVG.filter.element -->]]>

<!ENTITY % SVG.filter.attlist "INCLUDE" >
<![%SVG.filter.attlist;[
<!ATTLIST %SVG.filter.qname;
    %SVG.Core.attrib;
    %SVG.Style.attrib;
    %SVG.Presentation.attrib;
    %SVG.XLink.attrib;
    %SVG.External.attrib;
    x %Coordinate.datatype; #IMPLIED
    y %Coordinate.datatype; #IMPLIED
    width %Length.datatype; #IMPLIED
    height %Length.datatype; #IMPLIED
    filterRes %NumberOptionalNumber.datatype; #IMPLIED
    filterUnits ( userSpaceOnUse | objectBoundingBox ) #IMPLIED
    primitiveUnits ( userSpaceOnUse | objectBoundingBox ) #IMPLIED
>
<!-- end of SVG.filter.attlist -->]]>

<!-- feBlend: Filter Effect Blend Element .............. -->

<!ENTITY % SVG.feBlend.extra.content "" >

<!ENTITY % SVG.feBlend.element "INCLUDE" >
<![%SVG.feBlend.element;[
<!ENTITY % SVG.feBlend.content
    "( %SVG.animate.qname; | %SVG.set.qname; %SVG.feBlend.extra.content; )*"
>
<!ELEMENT %SVG.feBlend.qname; %SVG.feBlend.content; >
<!-- end of SVG.feBlend.element -->]]>

<!ENTITY % SVG.feBlend.attlist "INCLUDE" >
<![%SVG.feBlend.attlist;[
<!ATTLIST %SVG.feBlend.qname;
    %SVG.Core.attrib;
    %SVG.FilterColor.attrib;
    %SVG.FilterPrimitiveWithIn.attrib;
    in2 CDATA #REQUIRED
    mode ( normal | multiply | screen | darken | lighten ) 'normal'
>
<!-- end of SVG.feBlend.attlist -->]]>

<!-- feColorMatrix: Filter Effect Color Matrix Element . -->

<!ENTITY % SVG.feColorMatrix.extra.content "" >

<!ENTITY % SVG.feColorMatrix.element "INCLUDE" >
<![%SVG.feColorMatrix.element;[
<!ENTITY % SVG.feColorMatrix.content
    "( %SVG.animate.qname; | %SVG.set.qname;
       %SVG.feColorMatrix.extra.content; )*"
>
<!ELEMENT %SVG.feColorMatrix.qname; %SVG.feColorMatrix.content; >
<!-- end of SVG.feColorMatrix.element -->]]>

<!ENTITY % SVG.feColorMatrix.attlist "INCLUDE" >
<![%SVG.feColorMatrix.attlist;[
<!ATTLIST %SVG.feColorMatrix.qname;
    %SVG.Core.attrib;
    %SVG.FilterColor.attrib;
    %SVG.FilterPrimitiveWithIn.attrib;
    type ( matrix | saturate | hueRotate | luminanceToAlpha ) 'matrix'
    values CDATA #IMPLIED
>
<!-- end of SVG.feColorMatrix.attlist -->]]>

<!-- feComponentTransfer: Filter Effect Component Transfer Element -->

<!ENTITY % SVG.feComponentTransfer.extra.content "" >

<!ENTITY % SVG.feComponentTransfer.element "INCLUDE" >
<![%SVG.feComponentTransfer.element;[
<!ENTITY % SVG.feComponentTransfer.content
    "( %SVG.feFuncR.qname;?, %SVG.feFuncG.qname;?, %SVG.feFuncB.qname;?,
       %SVG.feFuncA.qname;? %SVG.feComponentTransfer.extra.content; )"
>
<!ELEMENT %SVG.feComponentTransfer.qname; %SVG.feComponentTransfer.content; >
<!-- end of SVG.feComponentTransfer.element -->]]>

<!ENTITY % SVG.feComponentTransfer.attlist "INCLUDE" >
<![%SVG.feComponentTransfer.attlist;[
<!ATTLIST %SVG.feComponentTransfer.qname;
    %SVG.Core.attrib;
    %SVG.FilterColor.attrib;
    %SVG.FilterPrimitiveWithIn.attrib;
>
<!-- end of SVG.feComponentTransfer.attlist -->]]>

<!-- feComposite: Filter Effect Composite Element ...... -->

<!ENTITY % SVG.feComposite.extra.content "" >

<!ENTITY % SVG.feComposite.element "INCLUDE" >
<![%SVG.feComposite.element;[
<!ENTITY % SVG.feComposite.content
    "( %SVG.animate.qname; | %SVG.set.qname; %SVG.feComposite.extra.content; )*"
>
<!ELEMENT %SVG.feComposite.qname; %SVG.feComposite.content; >
<!-- end of SVG.feComposite.element -->]]>

<!ENTITY % SVG.feComposite.attlist "INCLUDE" >
<![%SVG.feComposite.attlist;[
<!ATTLIST %SVG.feComposite.qname;
    %SVG.Core.attrib;
    %SVG.FilterColor.attrib;
    %SVG.FilterPrimitiveWithIn.attrib;
    in2 CDATA #REQUIRED
    operator ( over | in | out | atop | xor | arithmetic ) 'over'
    k1 %Number.datatype; #IMPLIED
    k2 %Number.datatype; #IMPLIED
    k3 %Number.datatype; #IMPLIED
    k4 %Number.datatype; #IMPLIED
>
<!-- end of SVG.feComposite.attlist -->]]>

<!-- feConvolveMatrix: Filter Effect Convolve Matrix Element -->

<!ENTITY % SVG.feConvolveMatrix.extra.content "" >

<!ENTITY % SVG.feConvolveMatrix.element "INCLUDE" >
<![%SVG.feConvolveMatrix.element;[
<!ENTITY % SVG.feConvolveMatrix.content
    "( %SVG.animate.qname; | %SVG.set.qname;
       %SVG.feConvolveMatrix.extra.content; )*"
>
<!ELEMENT %SVG.feConvolveMatrix.qname; %SVG.feConvolveMatrix.content; >
<!-- end of SVG.feConvolveMatrix.element -->]]>

<!ENTITY % SVG.feConvolveMatrix.attlist "INCLUDE" >
<![%SVG.feConvolveMatrix.attlist;[
<!ATTLIST %SVG.feConvolveMatrix.qname;
    %SVG.Core.attrib;
    %SVG.FilterColor.attrib;
    %SVG.FilterPrimitiveWithIn.attrib;
    order %NumberOptionalNumber.datatype; #REQUIRED
    kernelMatrix CDATA #REQUIRED
    divisor %Number.datatype; #IMPLIED
    bias %Number.datatype; #IMPLIED
    targetX %Integer.datatype; #IMPLIED
    targetY %Integer.datatype; #IMPLIED
    edgeMode ( duplicate | wrap | none ) 'duplicate'
    kernelUnitLength %NumberOptionalNumber.datatype; #IMPLIED
    preserveAlpha %Boolean.datatype; #IMPLIED
>
<!-- end of SVG.feConvolveMatrix.attlist -->]]>

<!-- feDiffuseLighting: Filter Effect Diffuse Lighting Element -->

<!ENTITY % SVG.feDiffuseLighting.extra.content "" >

<!ENTITY % SVG.feDiffuseLighting.element "INCLUDE" >
<![%SVG.feDiffuseLighting.element;[
<!ENTITY % SVG.feDiffuseLighting.content
    "(( %SVG.feDistantLight.qname; | %SVG.fePointLight.qname;
      | %SVG.feSpotLight.qname; ), ( %SVG.animate.qname; | %SVG.set.qname;
      | %SVG.animateColor.qname; %SVG.feDiffuseLighting.extra.content; )*)"
>
<!ELEMENT %SVG.feDiffuseLighting.qname; %SVG.feDiffuseLighting.content; >
<!-- end of SVG.feDiffuseLighting.element -->]]>

<!ENTITY % SVG.feDiffuseLighting.attlist "INCLUDE" >
<![%SVG.feDiffuseLighting.attlist;[
<!ATTLIST %SVG.feDiffuseLighting.qname;
    %SVG.Core.attrib;
    %SVG.Style.attrib;
    %SVG.Color.attrib;
    %SVG.FilterColor.attrib;
    %SVG.FilterPrimitiveWithIn.attrib;
    lighting-color %SVGColor.datatype; #IMPLIED
    surfaceScale %Number.datatype; #IMPLIED
    diffuseConstant %Number.datatype; #IMPLIED
    kernelUnitLength %NumberOptionalNumber.datatype; #IMPLIED
>
<!-- end of SVG.feDiffuseLighting.attlist -->]]>

<!-- feDisplacementMap: Filter Effect Displacement Map Element -->

<!ENTITY % SVG.feDisplacementMap.extra.content "" >

<!ENTITY % SVG.feDisplacementMap.element "INCLUDE" >
<![%SVG.feDisplacementMap.element;[
<!ENTITY % SVG.feDisplacementMap.content
    "( %SVG.animate.qname; | %SVG.set.qname;
       %SVG.feDisplacementMap.extra.content; )*"
>
<!ELEMENT %SVG.feDisplacementMap.qname; %SVG.feDisplacementMap.content; >
<!-- end of SVG.feDisplacementMap.element -->]]>

<!ENTITY % SVG.feDisplacementMap.attlist "INCLUDE" >
<![%SVG.feDisplacementMap.attlist;[
<!ATTLIST %SVG.feDisplacementMap.qname;
    %SVG.Core.attrib;
    %SVG.FilterColor.attrib;
    %SVG.FilterPrimitiveWithIn.attrib;
    in2 CDATA #REQUIRED
    scale %Number.datatype; #IMPLIED
    xChannelSelector ( R | G | B | A ) 'A'
    yChannelSelector ( R | G | B | A ) 'A'
>
<!-- end of SVG.feDisplacementMap.attlist -->]]>

<!-- feFlood: Filter Effect Flood Element .............. -->

<!ENTITY % SVG.feFlood.extra.content "" >

<!ENTITY % SVG.feFlood.element "INCLUDE" >
<![%SVG.feFlood.element;[
<!ENTITY % SVG.feFlood.content
    "( %SVG.animate.qname; | %SVG.set.qname; | %SVG.animateColor.qname;
       %SVG.feFlood.extra.content; )*"
>
<!ELEMENT %SVG.feFlood.qname; %SVG.feFlood.content; >
<!-- end of SVG.feFlood.element -->]]>

<!ENTITY % SVG.feFlood.attlist "INCLUDE" >
<![%SVG.feFlood.attlist;[
<!ATTLIST %SVG.feFlood.qname;
    %SVG.Core.attrib;
    %SVG.Style.attrib;
    %SVG.Color.attrib;
    %SVG.FilterColor.attrib;
    %SVG.FilterPrimitiveWithIn.attrib;
    flood-color %SVGColor.datatype; #IMPLIED
    flood-opacity %OpacityValue.datatype; #IMPLIED
>
<!-- end of SVG.feFlood.attlist -->]]>

<!-- feGaussianBlur: Filter Effect Gaussian Blur Element -->

<!ENTITY % SVG.feGaussianBlur.extra.content "" >

<!ENTITY % SVG.feGaussianBlur.element "INCLUDE" >
<![%SVG.feGaussianBlur.element;[
<!ENTITY % SVG.feGaussianBlur.content
    "( %SVG.animate.qname; | %SVG.set.qname;
       %SVG.feGaussianBlur.extra.content; )*"
>
<!ELEMENT %SVG.feGaussianBlur.qname; %SVG.feGaussianBlur.content; >
<!-- end of SVG.feGaussianBlur.element -->]]>

<!ENTITY % SVG.feGaussianBlur.attlist "INCLUDE" >
<![%SVG.feGaussianBlur.attlist;[
<!ATTLIST %SVG.feGaussianBlur.qname;
    %SVG.Core.attrib;
    %SVG.FilterColor.attrib;
    %SVG.FilterPrimitiveWithIn.attrib;
    stdDeviation %NumberOptionalNumber.datatype; #IMPLIED
>
<!-- end of SVG.feGaussianBlur.attlist -->]]>

<!-- feImage: Filter Effect Image Element .............. -->

<!ENTITY % SVG.feImage.extra.content "" >

<!ENTITY % SVG.feImage.element "INCLUDE" >
<![%SVG.feImage.element;[
<!ENTITY % SVG.feImage.content
    "( %SVG.animate.qname; | %SVG.set.qname; | %SVG.animateTransform.qname;
       %SVG.feImage.extra.content; )*"
>
<!ELEMENT %SVG.feImage.qname; %SVG.feImage.content; >
<!-- end of SVG.feImage.element -->]]>

<!ENTITY % SVG.feImage.attlist "INCLUDE" >
<![%SVG.feImage.attlist;[
<!ATTLIST %SVG.feImage.qname;
    %SVG.Core.attrib;
    %SVG.Style.attrib;
    %SVG.Presentation.attrib;
    %SVG.FilterPrimitive.attrib;
    %SVG.XLinkEmbed.attrib;
    %SVG.External.attrib;
    preserveAspectRatio %PreserveAspectRatioSpec.datatype; 'xMidYMid meet'
>
<!-- end of SVG.feImage.attlist -->]]>

<!-- feMerge: Filter Effect Merge Element .............. -->

<!ENTITY % SVG.feMerge.extra.content "" >

<!ENTITY % SVG.feMerge.element "INCLUDE" >
<![%SVG.feMerge.element;[
<!ENTITY % SVG.feMerge.content
    "( %SVG.feMergeNode.qname; %SVG.feMerge.extra.content; )*"
>
<!ELEMENT %SVG.feMerge.qname; %SVG.feMerge.content; >
<!-- end of SVG.feMerge.element -->]]>

<!ENTITY % SVG.feMerge.attlist "INCLUDE" >
<![%SVG.feMerge.attlist;[
<!ATTLIST %SVG.feMerge.qname;
    %SVG.Core.attrib;
    %SVG.FilterColor.attrib;
    %SVG.FilterPrimitive.attrib;
>
<!-- end of SVG.feMerge.attlist -->]]>

<!-- feMergeNode: Filter Effect Merge Node Element ..... -->

<!ENTITY % SVG.feMergeNode.extra.content "" >

<!ENTITY % SVG.feMergeNode.element "INCLUDE" >
<![%SVG.feMergeNode.element;[
<!ENTITY % SVG.feMergeNode.content
    "( %SVG.animate.qname; | %SVG.set.qname; %SVG.feMergeNode.extra.content; )*"
>
<!ELEMENT %SVG.feMergeNode.qname; %SVG.feMergeNode.content; >
<!-- end of SVG.feMergeNode.element -->]]>

<!ENTITY % SVG.feMergeNode.attlist "INCLUDE" >
<![%SVG.feMergeNode.attlist;[
<!ATTLIST %SVG.feMergeNode.qname;
    %SVG.Core.attrib;
    in CDATA #IMPLIED
>
<!-- end of SVG.feMergeNode.attlist -->]]>

<!-- feMorphology: Filter Effect Morphology Element .... -->

<!ENTITY % SVG.feMorphology.extra.content "" >

<!ENTITY % SVG.feMorphology.element "INCLUDE" >
<![%SVG.feMorphology.element;[
<!ENTITY % SVG.feMorphology.content
    "( %SVG.animate.qname; | %SVG.set.qname;
       %SVG.feMorphology.extra.content; )*"
>
<!ELEMENT %SVG.feMorphology.qname; %SVG.feMorphology.content; >
<!-- end of SVG.feMorphology.element -->]]>

<!ENTITY % SVG.feMorphology.attlist "INCLUDE" >
<![%SVG.feMorphology.attlist;[
<!ATTLIST %SVG.feMorphology.qname;
    %SVG.Core.attrib;
    %SVG.FilterColor.attrib;
    %SVG.FilterPrimitiveWithIn.attrib;
    operator ( erode | dilate ) 'erode'
    radius %NumberOptionalNumber.datatype; #IMPLIED
>
<!-- end of SVG.feMorphology.attlist -->]]>

<!-- feOffset: Filter Effect Offset Element ............ -->

<!ENTITY % SVG.feOffset.extra.content "" >

<!ENTITY % SVG.feOffset.element "INCLUDE" >
<![%SVG.feOffset.element;[
<!ENTITY % SVG.feOffset.content
    "( %SVG.animate.qname; | %SVG.set.qname; %SVG.feOffset.extra.content; )*"
>
<!ELEMENT %SVG.feOffset.qname; %SVG.feOffset.content; >
<!-- end of SVG.feOffset.element -->]]>

<!ENTITY % SVG.feOffset.attlist "INCLUDE" >
<![%SVG.feOffset.attlist;[
<!ATTLIST %SVG.feOffset.qname;
    %SVG.Core.attrib;
    %SVG.FilterColor.attrib;
    %SVG.FilterPrimitiveWithIn.attrib;
    dx %Number.datatype; #IMPLIED
    dy %Number.datatype; #IMPLIED
>
<!-- end of SVG.feOffset.attlist -->]]>

<!-- feSpecularLighting: Filter Effect Specular Lighting Element -->

<!ENTITY % SVG.feSpecularLighting.extra.content "" >

<!ENTITY % SVG.feSpecularLighting.element "INCLUDE" >
<![%SVG.feSpecularLighting.element;[
<!ENTITY % SVG.feSpecularLighting.content
    "(( %SVG.feDistantLight.qname; | %SVG.fePointLight.qname;
      | %SVG.feSpotLight.qname; ), ( %SVG.animate.qname; | %SVG.set.qname;
      | %SVG.animateColor.qname; %SVG.feSpecularLighting.extra.content; )*)"
>
<!ELEMENT %SVG.feSpecularLighting.qname; %SVG.feSpecularLighting.content; >
<!-- end of SVG.feSpecularLighting.element -->]]>

<!ENTITY % SVG.feSpecularLighting.attlist "INCLUDE" >
<![%SVG.feSpecularLighting.attlist;[
<!ATTLIST %SVG.feSpecularLighting.qname;
    %SVG.Core.attrib;
    %SVG.Style.attrib;
    %SVG.Color.attrib;
    %SVG.FilterColor.attrib;
    %SVG.FilterPrimitiveWithIn.attrib;
    lighting-color %SVGColor.datatype; #IMPLIED
    surfaceScale %Number.datatype; #IMPLIED
    specularConstant %Number.datatype; #IMPLIED
    specularExponent %Number.datatype; #IMPLIED
    kernelUnitLength %NumberOptionalNumber.datatype; #IMPLIED
>
<!-- end of SVG.feSpecularLighting.attlist -->]]>

<!-- feTile: Filter Effect Tile Element ................ -->

<!ENTITY % SVG.feTile.extra.content "" >

<!ENTITY % SVG.feTile.element "INCLUDE" >
<![%SVG.feTile.element;[
<!ENTITY % SVG.feTile.content
    "( %SVG.animate.qname; | %SVG.set.qname; %SVG.feTile.extra.content; )*"
>
<!ELEMENT %SVG.feTile.qname; %SVG.feTile.content; >
<!-- end of SVG.feTile.element -->]]>

<!ENTITY % SVG.feTile.attlist "INCLUDE" >
<![%SVG.feTile.attlist;[
<!ATTLIST %SVG.feTile.qname;
    %SVG.Core.attrib;
    %SVG.FilterColor.attrib;
    %SVG.FilterPrimitiveWithIn.attrib;
>
<!-- end of SVG.feTile.attlist -->]]>

<!-- feTurbulence: Filter Effect Turbulence Element .... -->

<!ENTITY % SVG.feTurbulence.extra.content "" >

<!ENTITY % SVG.feTurbulence.element "INCLUDE" >
<![%SVG.feTurbulence.element;[
<!ENTITY % SVG.feTurbulence.content
    "( %SVG.animate.qname; | %SVG.set.qname;
       %SVG.feTurbulence.extra.content; )*"
>
<!ELEMENT %SVG.feTurbulence.qname; %SVG.feTurbulence.content; >
<!-- end of SVG.feTurbulence.element -->]]>

<!ENTITY % SVG.feTurbulence.attlist "INCLUDE" >
<![%SVG.feTurbulence.attlist;[
<!ATTLIST %SVG.feTurbulence.qname;
    %SVG.Core.attrib;
    %SVG.FilterColor.attrib;
    %SVG.FilterPrimitive.attrib;
    baseFrequency %NumberOptionalNumber.datatype; #IMPLIED
    numOctaves %Integer.datatype; #IMPLIED
    seed %Number.datatype; #IMPLIED
    stitchTiles ( stitch | noStitch ) 'noStitch'
    type ( fractalNoise | turbulence ) 'turbulence'
>
<!-- end of SVG.feTurbulence.attlist -->]]>

<!-- feDistantLight: Filter Effect Distant Light Element -->

<!ENTITY % SVG.feDistantLight.extra.content "" >

<!ENTITY % SVG.feDistantLight.element "INCLUDE" >
<![%SVG.feDistantLight.element;[
<!ENTITY % SVG.feDistantLight.content
    "( %SVG.animate.qname; | %SVG.set.qname;
       %SVG.feDistantLight.extra.content; )*"
>
<!ELEMENT %SVG.feDistantLight.qname; %SVG.feDistantLight.content; >
<!-- end of SVG.feDistantLight.element -->]]>

<!ENTITY % SVG.feDistantLight.attlist "INCLUDE" >
<![%SVG.feDistantLight.attlist;[
<!ATTLIST %SVG.feDistantLight.qname;
    %SVG.Core.attrib;
    azimuth %Number.datatype; #IMPLIED
    elevation %Number.datatype; #IMPLIED
>
<!-- end of SVG.feDistantLight.attlist -->]]>

<!-- fePointLight: Filter Effect Point Light Element ... -->

<!ENTITY % SVG.fePointLight.extra.content "" >

<!ENTITY % SVG.fePointLight.element "INCLUDE" >
<![%SVG.fePointLight.element;[
<!ENTITY % SVG.fePointLight.content
    "( %SVG.animate.qname; | %SVG.set.qname;
       %SVG.fePointLight.extra.content; )*"
>
<!ELEMENT %SVG.fePointLight.qname; %SVG.fePointLight.content; >
<!-- end of SVG.fePointLight.element -->]]>

<!ENTITY % SVG.fePointLight.attlist "INCLUDE" >
<![%SVG.fePointLight.attlist;[
<!ATTLIST %SVG.fePointLight.qname;
    %SVG.Core.attrib;
    x %Number.datatype; #IMPLIED
    y %Number.datatype; #IMPLIED
    z %Number.datatype; #IMPLIED
>
<!-- end of SVG.fePointLight.attlist -->]]>

<!-- feSpotLight: Filter Effect Spot Light Element ..... -->

<!ENTITY % SVG.feSpotLight.extra.content "" >

<!ENTITY % SVG.feSpotLight.element "INCLUDE" >
<![%SVG.feSpotLight.element;[
<!ENTITY % SVG.feSpotLight.content
    "( %SVG.animate.qname; | %SVG.set.qname; %SVG.feSpotLight.extra.content; )*"
>
<!ELEMENT %SVG.feSpotLight.qname; %SVG.feSpotLight.content; >
<!-- end of SVG.feSpotLight.element -->]]>

<!ENTITY % SVG.feSpotLight.attlist "INCLUDE" >
<![%SVG.feSpotLight.attlist;[
<!ATTLIST %SVG.feSpotLight.qname;
    %SVG.Core.attrib;
    x %Number.datatype; #IMPLIED
    y %Number.datatype; #IMPLIED
    z %Number.datatype; #IMPLIED
    pointsAtX %Number.datatype; #IMPLIED
    pointsAtY %Number.datatype; #IMPLIED
    pointsAtZ %Number.datatype; #IMPLIED
    specularExponent %Number.datatype; #IMPLIED
    limitingConeAngle %Number.datatype; #IMPLIED
>
<!-- end of SVG.feSpotLight.attlist -->]]>

<!-- feFuncR: Filter Effect Function Red Element ....... -->

<!ENTITY % SVG.feFuncR.extra.content "" >

<!ENTITY % SVG.feFuncR.element "INCLUDE" >
<![%SVG.feFuncR.element;[
<!ENTITY % SVG.feFuncR.content
    "( %SVG.animate.qname; | %SVG.set.qname; %SVG.feFuncR.extra.content; )*"
>
<!ELEMENT %SVG.feFuncR.qname; %SVG.feFuncR.content; >
<!-- end of SVG.feFuncR.element -->]]>

<!ENTITY % SVG.feFuncR.attlist "INCLUDE" >
<![%SVG.feFuncR.attlist;[
<!ATTLIST %SVG.feFuncR.qname;
    %SVG.Core.attrib;
    type ( identity | table | discrete | linear | gamma ) #REQUIRED
    tableValues CDATA #IMPLIED
    slope %Number.datatype; #IMPLIED
    intercept %Number.datatype; #IMPLIED
    amplitude %Number.datatype; #IMPLIED
    exponent %Number.datatype; #IMPLIED
    offset %Number.datatype; #IMPLIED
>
<!-- end of SVG.feFuncR.attlist -->]]>

<!-- feFuncG: Filter Effect Function Green Element ..... -->

<!ENTITY % SVG.feFuncG.extra.content "" >

<!ENTITY % SVG.feFuncG.element "INCLUDE" >
<![%SVG.feFuncG.element;[
<!ENTITY % SVG.feFuncG.content
    "( %SVG.animate.qname; | %SVG.set.qname; %SVG.feFuncG.extra.content; )*"
>
<!ELEMENT %SVG.feFuncG.qname; %SVG.feFuncG.content; >
<!-- end of SVG.feFuncG.element -->]]>

<!ENTITY % SVG.feFuncG.attlist "INCLUDE" >
<![%SVG.feFuncG.attlist;[
<!ATTLIST %SVG.feFuncG.qname;
    %SVG.Core.attrib;
    type ( identity | table | discrete | linear | gamma ) #REQUIRED
    tableValues CDATA #IMPLIED
    slope %Number.datatype; #IMPLIED
    intercept %Number.datatype; #IMPLIED
    amplitude %Number.datatype; #IMPLIED
    exponent %Number.datatype; #IMPLIED
    offset %Number.datatype; #IMPLIED
>
<!-- end of SVG.feFuncG.attlist -->]]>

<!-- feFuncB: Filter Effect Function Blue Element ...... -->

<!ENTITY % SVG.feFuncB.extra.content "" >

<!ENTITY % SVG.feFuncB.element "INCLUDE" >
<![%SVG.feFuncB.element;[
<!ENTITY % SVG.feFuncB.content
    "( %SVG.animate.qname; | %SVG.set.qname; %SVG.feFuncB.extra.content; )*"
>
<!ELEMENT %SVG.feFuncB.qname; %SVG.feFuncB.content; >
<!-- end of SVG.feFuncB.element -->]]>

<!ENTITY % SVG.feFuncB.attlist "INCLUDE" >
<![%SVG.feFuncB.attlist;[
<!ATTLIST %SVG.feFuncB.qname;
    %SVG.Core.attrib;
    type ( identity | table | discrete | linear | gamma ) #REQUIRED
    tableValues CDATA #IMPLIED
    slope %Number.datatype; #IMPLIED
    intercept %Number.datatype; #IMPLIED
    amplitude %Number.datatype; #IMPLIED
    exponent %Number.datatype; #IMPLIED
    offset %Number.datatype; #IMPLIED
>
<!-- end of SVG.feFuncB.attlist -->]]>

<!-- feFuncA: Filter Effect Function Alpha Element ..... -->

<!ENTITY % SVG.feFuncA.extra.content "" >

<!ENTITY % SVG.feFuncA.element "INCLUDE" >
<![%SVG.feFuncA.element;[
<!ENTITY % SVG.feFuncA.content
    "( %SVG.animate.qname; | %SVG.set.qname; %SVG.feFuncA.extra.content; )*"
>
<!ELEMENT %SVG.feFuncA.qname; %SVG.feFuncA.content; >
<!-- end of SVG.feFuncA.element -->]]>

<!ENTITY % SVG.feFuncA.attlist "INCLUDE" >
<![%SVG.feFuncA.attlist;[
<!ATTLIST %SVG.feFuncA.qname;
    %SVG.Core.attrib;
    type ( identity | table | discrete | linear | gamma ) #REQUIRED
    tableValues CDATA #IMPLIED
    slope %Number.datatype; #IMPLIED
    intercept %Number.datatype; #IMPLIED
    amplitude %Number.datatype; #IMPLIED
    exponent %Number.datatype; #IMPLIED
    offset %Number.datatype; #IMPLIED
>
<!-- end of SVG.feFuncA.attlist -->]]>

<!-- end of svg-filter.mod -->

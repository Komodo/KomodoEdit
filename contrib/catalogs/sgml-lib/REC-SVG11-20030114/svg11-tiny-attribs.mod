<!-- ....................................................................... -->
<!-- SVG 1.1 Tiny Attribute Collection Module .............................. -->
<!-- file: svg11-tiny-attribs.mod

     This is SVG Tiny, a proper subset of SVG.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg11-tiny-attribs.mod,v 1.1.2.1 2003/06/08 20:19:48 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ENTITIES SVG 1.1 Tiny Attribute Collection//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11-tiny-attribs.mod"

     ....................................................................... -->

<!-- SVG 1.1 Tiny Attribute Collection

     This module defines the set of common attributes that can be present
     on many SVG elements.
-->

<!-- module: svg-conditional.mod ....................... -->

<!ENTITY % ExtensionList.datatype "CDATA" >
<!ENTITY % FeatureList.datatype "CDATA" >

<!ENTITY % SVG.Conditional.extra.attrib "" >
<!ENTITY % SVG.Conditional.attrib
    "requiredFeatures %FeatureList.datatype; #IMPLIED
     requiredExtensions %ExtensionList.datatype; #IMPLIED
     systemLanguage %LanguageCodes.datatype; #IMPLIED
     %SVG.Conditional.extra.attrib;"
>

<!-- module: svg-basic-text.mod ........................ -->

<!ENTITY % FontFamilyValue.datatype "CDATA" >
<!ENTITY % FontSizeValue.datatype "CDATA" >

<!ENTITY % SVG.TextContent.extra.attrib "" >
<!ENTITY % SVG.TextContent.attrib
    "text-anchor ( start | middle | end | inherit ) #IMPLIED
     %SVG.TextContent.extra.attrib;"
>

<!ENTITY % SVG.Font.extra.attrib "" >
<!ENTITY % SVG.Font.attrib
    "font-family %FontFamilyValue.datatype; #IMPLIED
     font-size %FontSizeValue.datatype; #IMPLIED
     font-style ( normal | italic | oblique | inherit ) #IMPLIED
     font-weight ( normal | bold | bolder | lighter | 100 | 200 | 300 | 400 |
                   500 | 600 | 700 | 800 | 900 | inherit ) #IMPLIED
     %SVG.Font.extra.attrib;"
>

<!-- end of svg11-tiny-attribs.mod -->

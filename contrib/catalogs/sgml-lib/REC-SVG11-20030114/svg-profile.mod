<!-- ....................................................................... -->
<!-- SVG 1.1 Color Profile Module .......................................... -->
<!-- file: svg-profile.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-profile.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ELEMENTS SVG 1.1 Color Profile//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-profile.mod"

     ....................................................................... -->

<!-- Color Profile

        color-profile

     This module declares markup to provide support for color profile.
-->

<!-- Qualified Names (Default) ......................... -->

<!ENTITY % SVG.color-profile.qname "color-profile" >

<!-- Attribute Collections (Default) ................... -->

<!ENTITY % SVG.Core.attrib "" >
<!ENTITY % SVG.XLink.attrib "" >

<!-- SVG.ColorProfile.class ............................ -->

<!ENTITY % SVG.ColorProfile.extra.class "" >

<!ENTITY % SVG.ColorProfile.class
    "| %SVG.color-profile.qname; %SVG.ColorProfile.extra.class;"
>

<!-- SVG.ColorProfile.attrib ........................... -->

<!ENTITY % SVG.ColorProfile.extra.attrib "" >

<!ENTITY % SVG.ColorProfile.attrib
    "color-profile CDATA #IMPLIED
     %SVG.ColorProfile.extra.attrib;"
>

<!-- color-profile: Color Profile Element .............. -->

<!ENTITY % SVG.color-profile.extra.content "" >

<!ENTITY % SVG.color-profile.element "INCLUDE" >
<![%SVG.color-profile.element;[
<!ENTITY % SVG.color-profile.content
    "( %SVG.Description.class; %SVG.color-profile.extra.content; )*"
>
<!ELEMENT %SVG.color-profile.qname; %SVG.color-profile.content; >
<!-- end of SVG.color-profile.element -->]]>

<!ENTITY % SVG.color-profile.attlist "INCLUDE" >
<![%SVG.color-profile.attlist;[
<!ATTLIST %SVG.color-profile.qname;
    %SVG.Core.attrib;
    %SVG.XLink.attrib;
    local CDATA #IMPLIED
    name CDATA #REQUIRED
    rendering-intent ( auto | perceptual | relative-colorimetric | saturation |
                       absolute-colorimetric ) 'auto'
>
<!-- end of SVG.color-profile.attlist -->]]>

<!-- end of svg-profile.mod -->

<!-- ....................................................................... -->
<!-- SVG 1.1 Font Module ................................................... -->
<!-- file: svg-font.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-font.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ELEMENTS SVG 1.1 Font//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-font.mod"

     ....................................................................... -->

<!-- Font

        font, font-face, glyph, missing-glyph, hkern, vkern, font-face-src,
        font-face-uri, font-face-format, font-face-name, definition-src

     This module declares markup to provide support for template.
-->

<!-- Qualified Names (Default) ......................... -->

<!ENTITY % SVG.font.qname "font" >
<!ENTITY % SVG.font-face.qname "font-face" >
<!ENTITY % SVG.glyph.qname "glyph" >
<!ENTITY % SVG.missing-glyph.qname "missing-glyph" >
<!ENTITY % SVG.hkern.qname "hkern" >
<!ENTITY % SVG.vkern.qname "vkern" >
<!ENTITY % SVG.font-face-src.qname "font-face-src" >
<!ENTITY % SVG.font-face-uri.qname "font-face-uri" >
<!ENTITY % SVG.font-face-format.qname "font-face-format" >
<!ENTITY % SVG.font-face-name.qname "font-face-name" >
<!ENTITY % SVG.definition-src.qname "definition-src" >

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
<!ENTITY % SVG.Filter.attrib "" >
<!ENTITY % SVG.FilterColor.attrib "" >
<!ENTITY % SVG.Cursor.attrib "" >
<!ENTITY % SVG.XLinkRequired.attrib "" >
<!ENTITY % SVG.External.attrib "" >

<!-- SVG.Font.class .................................... -->

<!ENTITY % SVG.Font.extra.class "" >

<!ENTITY % SVG.Font.class
    "| %SVG.font.qname; | %SVG.font-face.qname; %SVG.Font.extra.class;"
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

<!-- font: Font Element ................................ -->

<!ENTITY % SVG.font.extra.content "" >

<!ENTITY % SVG.font.element "INCLUDE" >
<![%SVG.font.element;[
<!ENTITY % SVG.font.content
    "(( %SVG.Description.class; )*, %SVG.font-face.qname;,
        %SVG.missing-glyph.qname;, ( %SVG.glyph.qname; | %SVG.hkern.qname;
      | %SVG.vkern.qname; %SVG.font.extra.content; )*)"
>
<!ELEMENT %SVG.font.qname; %SVG.font.content; >
<!-- end of SVG.font.element -->]]>

<!ENTITY % SVG.font.attlist "INCLUDE" >
<![%SVG.font.attlist;[
<!ATTLIST %SVG.font.qname;
    %SVG.Core.attrib;
    %SVG.Style.attrib;
    %SVG.Presentation.attrib;
    %SVG.External.attrib;
    horiz-origin-x %Number.datatype; #IMPLIED
    horiz-origin-y %Number.datatype; #IMPLIED
    horiz-adv-x %Number.datatype; #REQUIRED
    vert-origin-x %Number.datatype; #IMPLIED
    vert-origin-y %Number.datatype; #IMPLIED
    vert-adv-y %Number.datatype; #IMPLIED
>
<!-- end of SVG.font.attlist -->]]>

<!-- font-face: Font Face Element ...................... -->

<!ENTITY % SVG.font-face.extra.content "" >

<!ENTITY % SVG.font-face.element "INCLUDE" >
<![%SVG.font-face.element;[
<!ENTITY % SVG.font-face.content
    "(( %SVG.Description.class; )*, %SVG.font-face-src.qname;?,
        %SVG.definition-src.qname;? %SVG.font-face.extra.content; )"
>
<!ELEMENT %SVG.font-face.qname; %SVG.font-face.content; >
<!-- end of SVG.font-face.element -->]]>

<!ENTITY % SVG.font-face.attlist "INCLUDE" >
<![%SVG.font-face.attlist;[
<!ATTLIST %SVG.font-face.qname;
    %SVG.Core.attrib;
    font-family CDATA #IMPLIED
    font-style CDATA #IMPLIED
    font-variant CDATA #IMPLIED
    font-weight CDATA #IMPLIED
    font-stretch CDATA #IMPLIED
    font-size CDATA #IMPLIED
    unicode-range CDATA #IMPLIED
    units-per-em %Number.datatype; #IMPLIED
    panose-1 CDATA #IMPLIED
    stemv %Number.datatype; #IMPLIED
    stemh %Number.datatype; #IMPLIED
    slope %Number.datatype; #IMPLIED
    cap-height %Number.datatype; #IMPLIED
    x-height %Number.datatype; #IMPLIED
    accent-height %Number.datatype; #IMPLIED
    ascent %Number.datatype; #IMPLIED
    descent %Number.datatype; #IMPLIED
    widths CDATA #IMPLIED
    bbox CDATA #IMPLIED
    ideographic %Number.datatype; #IMPLIED
    alphabetic %Number.datatype; #IMPLIED
    mathematical %Number.datatype; #IMPLIED
    hanging %Number.datatype; #IMPLIED
    v-ideographic %Number.datatype; #IMPLIED
    v-alphabetic %Number.datatype; #IMPLIED
    v-mathematical %Number.datatype; #IMPLIED
    v-hanging %Number.datatype; #IMPLIED
    underline-position %Number.datatype; #IMPLIED
    underline-thickness %Number.datatype; #IMPLIED
    strikethrough-position %Number.datatype; #IMPLIED
    strikethrough-thickness %Number.datatype; #IMPLIED
    overline-position %Number.datatype; #IMPLIED
    overline-thickness %Number.datatype; #IMPLIED
>
<!-- end of SVG.font-face.attlist -->]]>

<!-- glyph: Glyph Element .............................. -->

<!ENTITY % SVG.glyph.extra.content "" >

<!ENTITY % SVG.glyph.element "INCLUDE" >
<![%SVG.glyph.element;[
<!ENTITY % SVG.glyph.content
    "( %SVG.Description.class; | %SVG.Animation.class; %SVG.Structure.class;
       %SVG.Conditional.class; %SVG.Image.class; %SVG.Style.class;
       %SVG.Shape.class; %SVG.Text.class; %SVG.Marker.class;
       %SVG.ColorProfile.class; %SVG.Gradient.class; %SVG.Pattern.class;
       %SVG.Clip.class; %SVG.Mask.class; %SVG.Filter.class; %SVG.Cursor.class;
       %SVG.Hyperlink.class; %SVG.View.class; %SVG.Script.class;
       %SVG.Font.class; %SVG.glyph.extra.content; )*"
>
<!ELEMENT %SVG.glyph.qname; %SVG.glyph.content; >
<!-- end of SVG.glyph.element -->]]>

<!ENTITY % SVG.glyph.attlist "INCLUDE" >
<![%SVG.glyph.attlist;[
<!ATTLIST %SVG.glyph.qname;
    %SVG.Core.attrib;
    %SVG.Style.attrib;
    %SVG.Presentation.attrib;
    unicode CDATA #IMPLIED
    glyph-name CDATA #IMPLIED
    d %PathData.datatype; #IMPLIED
    orientation CDATA #IMPLIED
    arabic-form CDATA #IMPLIED
    lang %LanguageCodes.datatype; #IMPLIED
    horiz-adv-x %Number.datatype; #IMPLIED
    vert-origin-x %Number.datatype; #IMPLIED
    vert-origin-y %Number.datatype; #IMPLIED
    vert-adv-y %Number.datatype; #IMPLIED
>
<!-- end of SVG.glyph.attlist -->]]>

<!-- missing-glyph: Missing Glyph Element .............. -->

<!ENTITY % SVG.missing-glyph.extra.content "" >

<!ENTITY % SVG.missing-glyph.element "INCLUDE" >
<![%SVG.missing-glyph.element;[
<!ENTITY % SVG.missing-glyph.content
    "( %SVG.Description.class; | %SVG.Animation.class; %SVG.Structure.class;
       %SVG.Conditional.class; %SVG.Image.class; %SVG.Style.class;
       %SVG.Shape.class; %SVG.Text.class; %SVG.Marker.class;
       %SVG.ColorProfile.class; %SVG.Gradient.class; %SVG.Pattern.class;
       %SVG.Clip.class; %SVG.Mask.class; %SVG.Filter.class; %SVG.Cursor.class;
       %SVG.Hyperlink.class; %SVG.View.class; %SVG.Script.class;
       %SVG.Font.class; %SVG.missing-glyph.extra.content; )*"
>
<!ELEMENT %SVG.missing-glyph.qname; %SVG.missing-glyph.content; >
<!-- end of SVG.missing-glyph.element -->]]>

<!ENTITY % SVG.missing-glyph.attlist "INCLUDE" >
<![%SVG.missing-glyph.attlist;[
<!ATTLIST %SVG.missing-glyph.qname;
    %SVG.Core.attrib;
    %SVG.Style.attrib;
    %SVG.Presentation.attrib;
    d %PathData.datatype; #IMPLIED
    horiz-adv-x %Number.datatype; #IMPLIED
    vert-origin-x %Number.datatype; #IMPLIED
    vert-origin-y %Number.datatype; #IMPLIED
    vert-adv-y %Number.datatype; #IMPLIED
>
<!-- end of SVG.missing-glyph.attlist -->]]>

<!-- hkern: Horizontal Kerning Element ................. -->

<!ENTITY % SVG.hkern.element "INCLUDE" >
<![%SVG.hkern.element;[
<!ENTITY % SVG.hkern.content "EMPTY" >
<!ELEMENT %SVG.hkern.qname; %SVG.hkern.content; >
<!-- end of SVG.hkern.element -->]]>

<!ENTITY % SVG.hkern.attlist "INCLUDE" >
<![%SVG.hkern.attlist;[
<!ATTLIST %SVG.hkern.qname;
    %SVG.Core.attrib;
    u1 CDATA #IMPLIED
    g1 CDATA #IMPLIED
    u2 CDATA #IMPLIED
    g2 CDATA #IMPLIED
    k %Number.datatype; #REQUIRED
>
<!-- end of SVG.hkern.attlist -->]]>

<!-- vkern: Vertical Kerning Element ................... -->

<!ENTITY % SVG.vkern.element "INCLUDE" >
<![%SVG.vkern.element;[
<!ENTITY % SVG.vkern.content "EMPTY" >
<!ELEMENT %SVG.vkern.qname; %SVG.vkern.content; >
<!-- end of SVG.vkern.element -->]]>

<!ENTITY % SVG.vkern.attlist "INCLUDE" >
<![%SVG.vkern.attlist;[
<!ATTLIST %SVG.vkern.qname;
    %SVG.Core.attrib;
    u1 CDATA #IMPLIED
    g1 CDATA #IMPLIED
    u2 CDATA #IMPLIED
    g2 CDATA #IMPLIED
    k %Number.datatype; #REQUIRED
>
<!-- end of SVG.vkern.attlist -->]]>

<!-- font-face-src: Font Face Source Element ........... -->

<!ENTITY % SVG.font-face-src.extra.content "" >

<!ENTITY % SVG.font-face-src.element "INCLUDE" >
<![%SVG.font-face-src.element;[
<!ENTITY % SVG.font-face-src.content
    "( %SVG.font-face-uri.qname; | %SVG.font-face-name.qname;
       %SVG.font-face-src.extra.content; )+"
>
<!ELEMENT %SVG.font-face-src.qname; %SVG.font-face-src.content; >
<!-- end of SVG.font-face-src.element -->]]>

<!ENTITY % SVG.font-face-src.attlist "INCLUDE" >
<![%SVG.font-face-src.attlist;[
<!ATTLIST %SVG.font-face-src.qname;
    %SVG.Core.attrib;
>
<!-- end of SVG.font-face-src.attlist -->]]>

<!-- font-face-uri: Font Face URI Element .............. -->

<!ENTITY % SVG.font-face-uri.extra.content "" >

<!ENTITY % SVG.font-face-uri.element "INCLUDE" >
<![%SVG.font-face-uri.element;[
<!ENTITY % SVG.font-face-uri.content
    "( %SVG.font-face-format.qname; %SVG.font-face-uri.extra.content; )*"
>
<!ELEMENT %SVG.font-face-uri.qname; %SVG.font-face-uri.content; >
<!-- end of SVG.font-face-uri.element -->]]>

<!ENTITY % SVG.font-face-uri.attlist "INCLUDE" >
<![%SVG.font-face-uri.attlist;[
<!ATTLIST %SVG.font-face-uri.qname;
    %SVG.Core.attrib;
    %SVG.XLinkRequired.attrib;
>
<!-- end of SVG.font-face-uri.attlist -->]]>

<!-- font-face-format: Font Face Format Element ........ -->

<!ENTITY % SVG.font-face-format.element "INCLUDE" >
<![%SVG.font-face-format.element;[
<!ENTITY % SVG.font-face-format.content "EMPTY" >
<!ELEMENT %SVG.font-face-format.qname; %SVG.font-face-format.content; >
<!-- end of SVG.font-face-format.element -->]]>

<!ENTITY % SVG.font-face-format.attlist "INCLUDE" >
<![%SVG.font-face-format.attlist;[
<!ATTLIST %SVG.font-face-format.qname;
    %SVG.Core.attrib;
    string CDATA #IMPLIED
>
<!-- end of SVG.font-face-format.attlist -->]]>

<!-- font-face-name: Font Face Name Element ............ -->

<!ENTITY % SVG.font-face-name.element "INCLUDE" >
<![%SVG.font-face-name.element;[
<!ENTITY % SVG.font-face-name.content "EMPTY" >
<!ELEMENT %SVG.font-face-name.qname; %SVG.font-face-name.content; >
<!-- end of SVG.font-face-name.element -->]]>

<!ENTITY % SVG.font-face-name.attlist "INCLUDE" >
<![%SVG.font-face-name.attlist;[
<!ATTLIST %SVG.font-face-name.qname;
    %SVG.Core.attrib;
    name CDATA #IMPLIED
>
<!-- end of SVG.font-face-name.attlist -->]]>

<!-- definition-src: Definition Source Element ......... -->

<!ENTITY % SVG.definition-src.element "INCLUDE" >
<![%SVG.definition-src.element;[
<!ENTITY % SVG.definition-src.content "EMPTY" >
<!ELEMENT %SVG.definition-src.qname; %SVG.definition-src.content; >
<!-- end of SVG.definition-src.element -->]]>

<!ENTITY % SVG.definition-src.attlist "INCLUDE" >
<![%SVG.definition-src.attlist;[
<!ATTLIST %SVG.definition-src.qname;
    %SVG.Core.attrib;
    %SVG.XLinkRequired.attrib;
>
<!-- end of SVG.definition-src.attlist -->]]>

<!-- end of svg-font.mod -->

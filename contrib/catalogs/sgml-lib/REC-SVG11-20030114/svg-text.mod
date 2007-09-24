<!-- ....................................................................... -->
<!-- SVG 1.1 Text Module ................................................... -->
<!-- file: svg-text.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-text.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ELEMENTS SVG 1.1 Text//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-text.mod"

     ....................................................................... -->

<!-- Text

        text, tspan, tref, textPath, altGlyph, altGlyphDef, altGlyphItem,
        glyphRef

     This module declares markup to provide support for alternate glyph.
-->

<!-- 'baseline-shift' property/attribute value (e.g., 'baseline', 'sub', etc.) -->
<!ENTITY % BaselineShiftValue.datatype "CDATA" >

<!-- 'font-family' property/attribute value (i.e., list of fonts) -->
<!ENTITY % FontFamilyValue.datatype "CDATA" >

<!-- 'font-size' property/attribute value -->
<!ENTITY % FontSizeValue.datatype "CDATA" >

<!-- 'font-size-adjust' property/attribute value -->
<!ENTITY % FontSizeAdjustValue.datatype "CDATA" >

<!-- 'glyph-orientation-horizontal' property/attribute value (e.g., <angle>) -->
<!ENTITY % GlyphOrientationHorizontalValue.datatype "CDATA" >

<!-- 'glyph-orientation-vertical' property/attribute value (e.g., 'auto', <angle>) -->
<!ENTITY % GlyphOrientationVerticalValue.datatype "CDATA" >

<!-- 'kerning' property/attribute value (e.g., 'auto', <length>) -->
<!ENTITY % KerningValue.datatype "CDATA" >

<!-- 'letter-spacing' or 'word-spacing' property/attribute value (e.g., 'normal', <length>) -->
<!ENTITY % SpacingValue.datatype "CDATA" >

<!-- 'text-decoration' property/attribute value (e.g., 'none', 'underline') -->
<!ENTITY % TextDecorationValue.datatype "CDATA" >

<!-- Qualified Names (Default) ......................... -->

<!ENTITY % SVG.text.qname "text" >
<!ENTITY % SVG.tspan.qname "tspan" >
<!ENTITY % SVG.tref.qname "tref" >
<!ENTITY % SVG.textPath.qname "textPath" >
<!ENTITY % SVG.altGlyph.qname "altGlyph" >
<!ENTITY % SVG.altGlyphDef.qname "altGlyphDef" >
<!ENTITY % SVG.altGlyphItem.qname "altGlyphItem" >
<!ENTITY % SVG.glyphRef.qname "glyphRef" >

<!-- Attribute Collections (Default) ................... -->

<!ENTITY % SVG.Core.attrib "" >
<!ENTITY % SVG.Conditional.attrib "" >
<!ENTITY % SVG.Style.attrib "" >
<!ENTITY % SVG.Paint.attrib "" >
<!ENTITY % SVG.Color.attrib "" >
<!ENTITY % SVG.Opacity.attrib "" >
<!ENTITY % SVG.Graphics.attrib "" >
<!ENTITY % SVG.Clip.attrib "" >
<!ENTITY % SVG.Mask.attrib "" >
<!ENTITY % SVG.Filter.attrib "" >
<!ENTITY % SVG.GraphicalEvents.attrib "" >
<!ENTITY % SVG.Cursor.attrib "" >
<!ENTITY % SVG.XLink.attrib "" >
<!ENTITY % SVG.XLinkRequired.attrib "" >
<!ENTITY % SVG.External.attrib "" >

<!-- SVG.Text.class .................................... -->

<!ENTITY % SVG.Text.extra.class "" >

<!ENTITY % SVG.Text.class
    "| %SVG.text.qname; | %SVG.altGlyphDef.qname; %SVG.Text.extra.class;"
>

<!-- SVG.TextContent.class ............................. -->

<!ENTITY % SVG.TextContent.extra.class "" >

<!ENTITY % SVG.TextContent.class
    "| %SVG.tspan.qname; | %SVG.tref.qname; | %SVG.textPath.qname;
     | %SVG.altGlyph.qname; %SVG.TextContent.extra.class;"
>

<!-- SVG.Text.attrib ................................... -->

<!ENTITY % SVG.Text.extra.attrib "" >

<!ENTITY % SVG.Text.attrib
    "writing-mode ( lr-tb | rl-tb | tb-rl | lr | rl | tb | inherit ) #IMPLIED
     %SVG.Text.extra.attrib;"
>

<!-- SVG.TextContent.attrib ............................ -->

<!ENTITY % SVG.TextContent.extra.attrib "" >

<!ENTITY % SVG.TextContent.attrib
    "alignment-baseline ( auto | baseline | before-edge | text-before-edge |
                          middle | central | after-edge | text-after-edge |
                          ideographic | alphabetic | hanging | mathematical |
                          inherit ) #IMPLIED
     baseline-shift %BaselineShiftValue.datatype; #IMPLIED
     direction ( ltr | rtl | inherit ) #IMPLIED
     dominant-baseline ( auto | use-script | no-change | reset-size |
                         ideographic | alphabetic | hanging | mathematical |
                         central | middle | text-after-edge | text-before-edge |
                         inherit ) #IMPLIED
     glyph-orientation-horizontal %GlyphOrientationHorizontalValue.datatype;
                                  #IMPLIED
     glyph-orientation-vertical %GlyphOrientationVerticalValue.datatype;
                                #IMPLIED
     kerning %KerningValue.datatype; #IMPLIED
     letter-spacing %SpacingValue.datatype; #IMPLIED
     text-anchor ( start | middle | end | inherit ) #IMPLIED
     text-decoration %TextDecorationValue.datatype; #IMPLIED
     unicode-bidi ( normal | embed | bidi-override | inherit ) #IMPLIED
     word-spacing %SpacingValue.datatype; #IMPLIED
     %SVG.TextContent.extra.attrib;"
>

<!-- SVG.Font.attrib ................................... -->

<!ENTITY % SVG.Font.extra.attrib "" >

<!ENTITY % SVG.Font.attrib
    "font-family %FontFamilyValue.datatype; #IMPLIED
     font-size %FontSizeValue.datatype; #IMPLIED
     font-size-adjust %FontSizeAdjustValue.datatype; #IMPLIED
     font-stretch ( normal | wider | narrower | ultra-condensed |
                    extra-condensed | condensed | semi-condensed |
                    semi-expanded | expanded | extra-expanded |
                    ultra-expanded | inherit ) #IMPLIED
     font-style ( normal | italic | oblique | inherit ) #IMPLIED
     font-variant ( normal | small-caps | inherit ) #IMPLIED
     font-weight ( normal | bold | bolder | lighter | 100 | 200 | 300 | 400 |
                   500 | 600 | 700 | 800 | 900 | inherit ) #IMPLIED
     %SVG.Font.extra.attrib;"
>

<!-- text: Text Element ................................ -->

<!ENTITY % SVG.text.extra.content "" >

<!ENTITY % SVG.text.element "INCLUDE" >
<![%SVG.text.element;[
<!ENTITY % SVG.text.content
    "( #PCDATA | %SVG.Description.class; | %SVG.Animation.class;
       %SVG.TextContent.class; %SVG.Hyperlink.class;
       %SVG.text.extra.content; )*"
>
<!ELEMENT %SVG.text.qname; %SVG.text.content; >
<!-- end of SVG.text.element -->]]>

<!ENTITY % SVG.text.attlist "INCLUDE" >
<![%SVG.text.attlist;[
<!ATTLIST %SVG.text.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.Style.attrib;
    %SVG.Text.attrib;
    %SVG.TextContent.attrib;
    %SVG.Font.attrib;
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
    x %Coordinates.datatype; #IMPLIED
    y %Coordinates.datatype; #IMPLIED
    dx %Lengths.datatype; #IMPLIED
    dy %Lengths.datatype; #IMPLIED
    rotate %Numbers.datatype; #IMPLIED
    textLength %Length.datatype; #IMPLIED
    lengthAdjust ( spacing | spacingAndGlyphs ) #IMPLIED
    transform %TransformList.datatype; #IMPLIED
>
<!-- end of SVG.text.attlist -->]]>

<!-- tspan: Text Span Element .......................... -->

<!ENTITY % SVG.tspan.extra.content "" >

<!ENTITY % SVG.tspan.element "INCLUDE" >
<![%SVG.tspan.element;[
<!ENTITY % SVG.tspan.content
    "( #PCDATA | %SVG.tspan.qname; | %SVG.tref.qname; | %SVG.altGlyph.qname;
     | %SVG.animate.qname; | %SVG.set.qname; | %SVG.animateColor.qname;
     | %SVG.Description.class; %SVG.Hyperlink.class;
       %SVG.tspan.extra.content; )*"
>
<!ELEMENT %SVG.tspan.qname; %SVG.tspan.content; >
<!-- end of SVG.tspan.element -->]]>

<!ENTITY % SVG.tspan.attlist "INCLUDE" >
<![%SVG.tspan.attlist;[
<!ATTLIST %SVG.tspan.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.Style.attrib;
    %SVG.TextContent.attrib;
    %SVG.Font.attrib;
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
    x %Coordinates.datatype; #IMPLIED
    y %Coordinates.datatype; #IMPLIED
    dx %Lengths.datatype; #IMPLIED
    dy %Lengths.datatype; #IMPLIED
    rotate %Numbers.datatype; #IMPLIED
    textLength %Length.datatype; #IMPLIED
    lengthAdjust ( spacing | spacingAndGlyphs ) #IMPLIED
>
<!-- end of SVG.tspan.attlist -->]]>

<!-- tref: Text Reference Element ...................... -->

<!ENTITY % SVG.tref.extra.content "" >

<!ENTITY % SVG.tref.element "INCLUDE" >
<![%SVG.tref.element;[
<!ENTITY % SVG.tref.content
    "( %SVG.animate.qname; | %SVG.set.qname; | %SVG.animateColor.qname;
     | %SVG.Description.class; %SVG.tref.extra.content; )*"
>
<!ELEMENT %SVG.tref.qname; %SVG.tref.content; >
<!-- end of SVG.tref.element -->]]>

<!ENTITY % SVG.tref.attlist "INCLUDE" >
<![%SVG.tref.attlist;[
<!ATTLIST %SVG.tref.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.Style.attrib;
    %SVG.TextContent.attrib;
    %SVG.Font.attrib;
    %SVG.Paint.attrib;
    %SVG.Color.attrib;
    %SVG.Opacity.attrib;
    %SVG.Graphics.attrib;
    %SVG.Clip.attrib;
    %SVG.Mask.attrib;
    %SVG.Filter.attrib;
    %SVG.GraphicalEvents.attrib;
    %SVG.Cursor.attrib;
    %SVG.XLinkRequired.attrib;
    %SVG.External.attrib;
    x %Coordinates.datatype; #IMPLIED
    y %Coordinates.datatype; #IMPLIED
    dx %Lengths.datatype; #IMPLIED
    dy %Lengths.datatype; #IMPLIED
    rotate %Numbers.datatype; #IMPLIED
    textLength %Length.datatype; #IMPLIED
    lengthAdjust ( spacing | spacingAndGlyphs ) #IMPLIED
>
<!-- end of SVG.tref.attlist -->]]>

<!-- textPath: Text Path Element ....................... -->

<!ENTITY % SVG.textPath.extra.content "" >

<!ENTITY % SVG.textPath.element "INCLUDE" >
<![%SVG.textPath.element;[
<!ENTITY % SVG.textPath.content
    "( #PCDATA | %SVG.tspan.qname; | %SVG.tref.qname; | %SVG.altGlyph.qname;
     | %SVG.animate.qname; | %SVG.set.qname; | %SVG.animateColor.qname;
     | %SVG.Description.class; %SVG.Hyperlink.class;
       %SVG.textPath.extra.content; )*"
>
<!ELEMENT %SVG.textPath.qname; %SVG.textPath.content; >
<!-- end of SVG.textPath.element -->]]>

<!ENTITY % SVG.textPath.attlist "INCLUDE" >
<![%SVG.textPath.attlist;[
<!ATTLIST %SVG.textPath.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.Style.attrib;
    %SVG.TextContent.attrib;
    %SVG.Font.attrib;
    %SVG.Paint.attrib;
    %SVG.Color.attrib;
    %SVG.Opacity.attrib;
    %SVG.Graphics.attrib;
    %SVG.Clip.attrib;
    %SVG.Mask.attrib;
    %SVG.Filter.attrib;
    %SVG.GraphicalEvents.attrib;
    %SVG.Cursor.attrib;
    %SVG.XLinkRequired.attrib;
    %SVG.External.attrib;
    startOffset %Length.datatype; #IMPLIED
    textLength %Length.datatype; #IMPLIED
    lengthAdjust ( spacing | spacingAndGlyphs ) #IMPLIED
    method ( align | stretch ) #IMPLIED
    spacing ( auto | exact ) #IMPLIED
>
<!-- end of SVG.textPath.attlist -->]]>

<!-- altGlyph: Alternate Glyph Element ................. -->

<!ENTITY % SVG.altGlyph.extra.content "" >

<!ENTITY % SVG.altGlyph.element "INCLUDE" >
<![%SVG.altGlyph.element;[
<!ENTITY % SVG.altGlyph.content
    "( #PCDATA %SVG.altGlyph.extra.content; )*"
>
<!ELEMENT %SVG.altGlyph.qname; %SVG.altGlyph.content; >
<!-- end of SVG.altGlyph.element -->]]>

<!ENTITY % SVG.altGlyph.attlist "INCLUDE" >
<![%SVG.altGlyph.attlist;[
<!ATTLIST %SVG.altGlyph.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.Style.attrib;
    %SVG.TextContent.attrib;
    %SVG.Font.attrib;
    %SVG.Paint.attrib;
    %SVG.Color.attrib;
    %SVG.Opacity.attrib;
    %SVG.Graphics.attrib;
    %SVG.Clip.attrib;
    %SVG.Mask.attrib;
    %SVG.Filter.attrib;
    %SVG.GraphicalEvents.attrib;
    %SVG.Cursor.attrib;
    %SVG.XLink.attrib;
    %SVG.External.attrib;
    x %Coordinates.datatype; #IMPLIED
    y %Coordinates.datatype; #IMPLIED
    dx %Lengths.datatype; #IMPLIED
    dy %Lengths.datatype; #IMPLIED
    glyphRef CDATA #IMPLIED
    format CDATA #IMPLIED
    rotate %Numbers.datatype; #IMPLIED
>
<!-- end of SVG.altGlyph.attlist -->]]>

<!-- altGlyphDef: Alternate Glyph Definition Element ... -->

<!ENTITY % SVG.altGlyphDef.extra.content "" >

<!ENTITY % SVG.altGlyphDef.element "INCLUDE" >
<![%SVG.altGlyphDef.element;[
<!ENTITY % SVG.altGlyphDef.content
    "(( %SVG.glyphRef.qname;+ | %SVG.altGlyphItem.qname;+ )
        %SVG.altGlyphDef.extra.content; )"
>
<!ELEMENT %SVG.altGlyphDef.qname; %SVG.altGlyphDef.content; >
<!-- end of SVG.altGlyphDef.element -->]]>

<!ENTITY % SVG.altGlyphDef.attlist "INCLUDE" >
<![%SVG.altGlyphDef.attlist;[
<!ATTLIST %SVG.altGlyphDef.qname;
    %SVG.Core.attrib;
>
<!-- end of SVG.altGlyphDef.attlist -->]]>

<!-- altGlyphItem: Alternate Glyph Item Element ........ -->

<!ENTITY % SVG.altGlyphItem.extra.content "" >

<!ENTITY % SVG.altGlyphItem.element "INCLUDE" >
<![%SVG.altGlyphItem.element;[
<!ENTITY % SVG.altGlyphItem.content
    "( %SVG.glyphRef.qname;+ %SVG.altGlyphItem.extra.content; )"
>
<!ELEMENT %SVG.altGlyphItem.qname; %SVG.altGlyphItem.content; >
<!-- end of SVG.altGlyphItem.element -->]]>

<!ENTITY % SVG.altGlyphItem.attlist "INCLUDE" >
<![%SVG.altGlyphItem.attlist;[
<!ATTLIST %SVG.altGlyphItem.qname;
    %SVG.Core.attrib;
>
<!-- end of SVG.altGlyphItem.attlist -->]]>

<!-- glyphRef: Glyph Reference Element ................. -->

<!ENTITY % SVG.glyphRef.element "INCLUDE" >
<![%SVG.glyphRef.element;[
<!ENTITY % SVG.glyphRef.content "EMPTY" >
<!ELEMENT %SVG.glyphRef.qname; %SVG.glyphRef.content; >
<!-- end of SVG.glyphRef.element -->]]>

<!ENTITY % SVG.glyphRef.attlist "INCLUDE" >
<![%SVG.glyphRef.attlist;[
<!ATTLIST %SVG.glyphRef.qname;
    %SVG.Core.attrib;
    %SVG.Style.attrib;
    %SVG.Font.attrib;
    %SVG.XLink.attrib;
    x %Number.datatype; #IMPLIED
    y %Number.datatype; #IMPLIED
    dx %Number.datatype; #IMPLIED
    dy %Number.datatype; #IMPLIED
    glyphRef CDATA #IMPLIED
    format CDATA #IMPLIED
>
<!-- end of SVG.glyphRef.attlist -->]]>

<!-- end of svg-text.mod -->

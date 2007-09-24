<!-- ....................................................................... -->
<!-- SVG 1.1 Datatypes Module .............................................. -->
<!-- file: svg-datatypes.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-datatypes.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ENTITIES SVG 1.1 Datatypes//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-datatypes.mod"

     ....................................................................... -->

<!-- Datatypes

     This module declares common data types for properties and attributes.
-->

<!-- feature specification -->
<!ENTITY % Boolean.datatype "( false | true )" >

<!-- 'clip-rule' or 'fill-rule' property/attribute value -->
<!ENTITY % ClipFillRule.datatype "( nonzero | evenodd | inherit )" >

<!-- media type, as per [RFC2045] -->
<!ENTITY % ContentType.datatype "CDATA" >

<!-- a <coordinate> -->
<!ENTITY % Coordinate.datatype "CDATA" >

<!-- a list of <coordinate>s -->
<!ENTITY % Coordinates.datatype "CDATA" >

<!-- a <color> value -->
<!ENTITY % Color.datatype "CDATA" >

<!-- a <integer> -->
<!ENTITY % Integer.datatype "CDATA" >

<!-- a language code, as per [RFC3066] -->
<!ENTITY % LanguageCode.datatype "NMTOKEN" >

<!-- comma-separated list of language codes, as per [RFC3066] -->
<!ENTITY % LanguageCodes.datatype "CDATA" >

<!-- a <length> -->
<!ENTITY % Length.datatype "CDATA" >

<!-- a list of <length>s -->
<!ENTITY % Lengths.datatype "CDATA" >

<!-- a <number> -->
<!ENTITY % Number.datatype "CDATA" >

<!-- a list of <number>s -->
<!ENTITY % Numbers.datatype "CDATA" >

<!-- opacity value (e.g., <number>) -->
<!ENTITY % OpacityValue.datatype "CDATA" >

<!-- a path data specification -->
<!ENTITY % PathData.datatype "CDATA" >

<!-- 'preserveAspectRatio' attribute specification -->
<!ENTITY % PreserveAspectRatioSpec.datatype "CDATA" >

<!-- script expression -->
<!ENTITY % Script.datatype "CDATA" >

<!-- An SVG color value (RGB plus optional ICC) -->
<!ENTITY % SVGColor.datatype "CDATA" >

<!-- arbitrary text string -->
<!ENTITY % Text.datatype "CDATA" >

<!-- list of transforms -->
<!ENTITY % TransformList.datatype "CDATA" >

<!-- a Uniform Resource Identifier, see [URI] -->
<!ENTITY % URI.datatype "CDATA" >

<!-- 'viewBox' attribute specification -->
<!ENTITY % ViewBoxSpec.datatype "CDATA" >

<!-- end of svg-datatypes.mod -->

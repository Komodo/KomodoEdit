<!-- ....................................................................... -->
<!-- SVG 1.1 Core Attribute Module ......................................... -->
<!-- file: svg-core-attrib.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-core-attrib.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ENTITIES SVG 1.1 Core Attribute//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-core-attrib.mod"

     ....................................................................... -->

<!-- Core Attribute

        id, xml:base, xml:lang, xml:space

     This module defines the core set of attributes that can be present on
     any element.
-->

<!ENTITY % SVG.id.attrib
    "id ID #IMPLIED"
>

<!ENTITY % SVG.base.attrib
    "xml:base %URI.datatype; #IMPLIED"
>

<!ENTITY % SVG.lang.attrib
    "xml:lang %LanguageCode.datatype; #IMPLIED"
>

<!ENTITY % SVG.space.attrib
    "xml:space ( default | preserve ) #IMPLIED"
>

<!ENTITY % SVG.Core.extra.attrib "" >

<!ENTITY % SVG.Core.attrib
    "%SVG.id.attrib;
     %SVG.base.attrib;
     %SVG.lang.attrib;
     %SVG.space.attrib;
     %SVG.Core.extra.attrib;"
>

<!-- end of svg-core-attrib.mod -->

<!-- ....................................................................... -->
<!-- SVG 1.1 External Resources Attribute Module ........................... -->
<!-- file: svg-extresources-attrib.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-extresources-attrib.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ENTITIES SVG 1.1 External Resources Attribute//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-extresources-attrib.mod"

     ....................................................................... -->

<!-- External Resources Attribute

        externalResourcesRequired

     This module defines the External attribute set.
-->

<!ENTITY % SVG.externalResourcesRequired.attrib
    "externalResourcesRequired %Boolean.datatype; #IMPLIED"
>

<!ENTITY % SVG.External.extra.attrib "" >

<!ENTITY % SVG.External.attrib
    "%SVG.externalResourcesRequired.attrib;
     %SVG.External.extra.attrib;"
>

<!-- end of svg-extresources-attrib.mod -->

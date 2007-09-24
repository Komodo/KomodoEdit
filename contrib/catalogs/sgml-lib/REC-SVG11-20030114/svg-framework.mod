<!-- ....................................................................... -->
<!-- SVG 1.1 Modular Framework Module ...................................... -->
<!-- file: svg-framework.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-framework.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ENTITIES SVG 1.1 Modular Framework//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-framework.mod"

     ....................................................................... -->

<!-- Modular Framework

     This module instantiates the modules needed o support the SVG
     modularization model, including:

        + Datatypes
        + Qualified Name
        + Document Model
        + Attribute Collection
-->

<!ENTITY % svg-datatypes.module "INCLUDE" >
<![%svg-datatypes.module;[
<!ENTITY % svg-datatypes.mod
    PUBLIC "-//W3C//ENTITIES SVG 1.1 Datatypes//EN"
           "svg-datatypes.mod" >
%svg-datatypes.mod;]]>

<!ENTITY % svg-qname.module "INCLUDE" >
<![%svg-qname.module;[
<!ENTITY % svg-qname.mod
    PUBLIC "-//W3C//ENTITIES SVG 1.1 Qualified Name//EN"
           "svg-qname.mod" >
%svg-qname.mod;]]>

<!ENTITY % svg-model.module "INCLUDE" >
<![%svg-model.module;[
<!-- instantiate the Document Model declared in the DTD driver -->
%svg-model.mod;]]>

<!ENTITY % svg-attribs.module "INCLUDE" >
<![%svg-attribs.module;[
<!-- instantiate the Attribute Collection declared in the DTD driver -->
%svg-attribs.mod;]]>

<!-- end of svg-framework.mod -->

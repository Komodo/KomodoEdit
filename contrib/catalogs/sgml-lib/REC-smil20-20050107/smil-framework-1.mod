<!-- ...................................................................... -->
<!-- SMIL 2.0 Modular Framework Module  ................................... -->
<!-- file: smil-framework-1.mod

     This is SMIL 2.0.

    	Copyright: 1998-2004 W3C (MIT, ERCIM, Keio), All Rights Reserved.
    	See http://www.w3.org/Consortium/Legal/.

	Author:     Jacco van Ossenbruggen
        Revision:   2001/07/31  Thierry Michel  

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

     PUBLIC "-//W3C//ENTITIES SMIL 2.0 Modular Framework 1.0//EN"
     SYSTEM "http://www.w3.org/2001/SMIL20/smil-framework-1.mod"

         ....................................................................... -->

<!-- Modular Framework

     This required module instantiates the modules needed
     to support the SMIL 2.0 modularization model, including:

        +  datatypes
        +  namespace-qualified names
        +  common attributes
        +  document model
-->

<!ENTITY % smil-datatypes.module "INCLUDE" >
<![%smil-datatypes.module;[
<!ENTITY % smil-datatypes.mod
     PUBLIC "-//W3C//ENTITIES SMIL 2.0 Datatypes 1.0//EN"
            "smil-datatypes-1.mod" >
%smil-datatypes.mod;]]>

<!ENTITY % smil-qname.module "INCLUDE" >
<![%smil-qname.module;[
<!ENTITY % smil-qname.mod
     PUBLIC "-//W3C//ENTITIES SMIL 2.0 Qualified Names 1.0//EN"
            "smil-qname-1.mod" >
%smil-qname.mod;]]>

<!ENTITY % smil-attribs.module "INCLUDE" >
<![%smil-attribs.module;[
<!ENTITY % smil-attribs.mod
     PUBLIC "-//W3C//ENTITIES SMIL 2.0 Common Attributes 1.0//EN"
            "smil-attribs-1.mod" >
%smil-attribs.mod;]]>

<!ENTITY % smil-model.module "INCLUDE" >
<![%smil-model.module;[
<!-- A content model MUST be defined by the driver file -->
%smil-model.mod;]]>

<!-- end of smil-framework-1.mod -->

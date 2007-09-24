<!-- ....................................................................... -->
<!-- SVG 1.1 Scripting Module .............................................. -->
<!-- file: svg-script.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-script.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ELEMENTS SVG 1.1 Scripting//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-script.mod"

     ....................................................................... -->

<!-- Scripting

        script

     This module declares markup to provide support for scripting.
-->

<!-- Qualified Names (Default) ......................... -->

<!ENTITY % SVG.script.qname "script" >

<!-- Attribute Collections (Default) ................... -->

<!ENTITY % SVG.Core.attrib "" >
<!ENTITY % SVG.XLink.attrib "" >
<!ENTITY % SVG.External.attrib "" >

<!-- SVG.Script.class .................................. -->

<!ENTITY % SVG.Script.extra.class "" >

<!ENTITY % SVG.Script.class
    "| %SVG.script.qname; %SVG.Script.extra.class;"
>

<!-- script: Script Element ............................ -->

<!ENTITY % SVG.script.extra.content "" >

<!ENTITY % SVG.script.element "INCLUDE" >
<![%SVG.script.element;[
<!ENTITY % SVG.script.content
    "( #PCDATA %SVG.script.extra.content; )*"
>
<!ELEMENT %SVG.script.qname; %SVG.script.content; >
<!-- end of SVG.script.element -->]]>

<!ENTITY % SVG.script.attlist "INCLUDE" >
<![%SVG.script.attlist;[
<!ATTLIST %SVG.script.qname;
    %SVG.Core.attrib;
    %SVG.XLink.attrib;
    %SVG.External.attrib;
    type %ContentType.datatype; #REQUIRED
>
<!-- end of SVG.script.attlist -->]]>

<!-- end of svg-script.mod -->

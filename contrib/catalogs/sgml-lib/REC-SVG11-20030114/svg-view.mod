<!-- ....................................................................... -->
<!-- SVG 1.1 View Module ................................................... -->
<!-- file: svg-view.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-view.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ELEMENTS SVG 1.1 View//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-view.mod"

     ....................................................................... -->

<!-- View

        view

     This module declares markup to provide support for view.
-->

<!-- Qualified Names (Default) ......................... -->

<!ENTITY % SVG.view.qname "view" >

<!-- Attribute Collections (Default) ................... -->

<!ENTITY % SVG.Core.attrib "" >
<!ENTITY % SVG.External.attrib "" >

<!-- SVG.View.class .................................... -->

<!ENTITY % SVG.View.extra.class "" >

<!ENTITY % SVG.View.class
    "| %SVG.view.qname; %SVG.View.extra.class;"
>

<!-- view: View Element ................................ -->

<!ENTITY % SVG.view.extra.content "" >

<!ENTITY % SVG.view.element "INCLUDE" >
<![%SVG.view.element;[
<!ENTITY % SVG.view.content
    "( %SVG.Description.class; %SVG.view.extra.content; )*"
>
<!ELEMENT %SVG.view.qname; %SVG.view.content; >
<!-- end of SVG.view.element -->]]>

<!ENTITY % SVG.view.attlist "INCLUDE" >
<![%SVG.view.attlist;[
<!ATTLIST %SVG.view.qname;
    %SVG.Core.attrib;
    %SVG.External.attrib;
    viewBox %ViewBoxSpec.datatype; #IMPLIED
    preserveAspectRatio %PreserveAspectRatioSpec.datatype; 'xMidYMid meet'
    zoomAndPan ( disable | magnify ) 'magnify'
    viewTarget CDATA #IMPLIED
>
<!-- end of SVG.view.attlist -->]]>

<!-- end of svg-view.mod -->

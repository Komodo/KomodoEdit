<!-- ....................................................................... -->
<!-- SVG 1.1 Animation Module .............................................. -->
<!-- file: svg-animation.mod

     This is SVG, a language for describing two-dimensional graphics in XML.
     Copyright 2001, 2002 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: $Id: svg-animation.mod,v 1.1.2.1 2003/06/08 20:19:47 link Exp $

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ELEMENTS SVG 1.1 Animation//EN"
        SYSTEM "http://www.w3.org/Graphics/SVG/1.1/DTD/svg-animation.mod"

     ....................................................................... -->

<!-- Animation

        animate, set, animateMotion, animateColor, animateTransform, mpath

     This module declares markup to provide support for animation.
-->

<!-- Qualified Names (Default) ......................... -->

<!ENTITY % SVG.animate.qname "animate" >
<!ENTITY % SVG.set.qname "set" >
<!ENTITY % SVG.animateMotion.qname "animateMotion" >
<!ENTITY % SVG.animateColor.qname "animateColor" >
<!ENTITY % SVG.animateTransform.qname "animateTransform" >
<!ENTITY % SVG.mpath.qname "mpath" >

<!-- Attribute Collections (Default) ................... -->

<!ENTITY % SVG.Core.attrib "" >
<!ENTITY % SVG.Conditional.attrib "" >
<!ENTITY % SVG.AnimationEvents.attrib "" >
<!ENTITY % SVG.XLink.attrib "" >
<!ENTITY % SVG.XLinkRequired.attrib "" >
<!ENTITY % SVG.External.attrib "" >

<!-- SVG.Animation.class ............................... -->

<!ENTITY % SVG.Animation.extra.class "" >

<!ENTITY % SVG.Animation.class
    "%SVG.animate.qname; | %SVG.set.qname; | %SVG.animateMotion.qname; |
     %SVG.animateColor.qname; | %SVG.animateTransform.qname;
     %SVG.Animation.extra.class;"
>

<!-- SVG.Animation.attrib .............................. -->

<!ENTITY % SVG.Animation.extra.attrib "" >

<!ENTITY % SVG.Animation.attrib
    "%SVG.XLink.attrib;
     %SVG.Animation.extra.attrib;"
>

<!-- SVG.AnimationAttribute.attrib ..................... -->

<!ENTITY % SVG.AnimationAttribute.extra.attrib "" >

<!ENTITY % SVG.AnimationAttribute.attrib
    "attributeName  CDATA  #REQUIRED
     attributeType  CDATA  #IMPLIED
     %SVG.AnimationAttribute.extra.attrib;"
>

<!-- SVG.AnimationTiming.attrib ........................ -->

<!ENTITY % SVG.AnimationTiming.extra.attrib "" >

<!ENTITY % SVG.AnimationTiming.attrib
    "begin CDATA #IMPLIED
     dur CDATA #IMPLIED
     end CDATA #IMPLIED
     min CDATA #IMPLIED
     max CDATA #IMPLIED
     restart ( always | never | whenNotActive ) 'always'
     repeatCount CDATA #IMPLIED
     repeatDur CDATA #IMPLIED
     fill ( remove | freeze ) 'remove'
     %SVG.AnimationTiming.extra.attrib;"
>

<!-- SVG.AnimationValue.attrib ......................... -->

<!ENTITY % SVG.AnimationValue.extra.attrib "" >

<!ENTITY % SVG.AnimationValue.attrib
    "calcMode ( discrete | linear | paced | spline ) 'linear'
     values CDATA #IMPLIED
     keyTimes CDATA #IMPLIED
     keySplines CDATA #IMPLIED
     from CDATA #IMPLIED
     to CDATA #IMPLIED
     by CDATA #IMPLIED
     %SVG.AnimationValue.extra.attrib;"
>

<!-- SVG.AnimationAddtion.attrib ....................... -->

<!ENTITY % SVG.AnimationAddtion.extra.attrib "" >

<!ENTITY % SVG.AnimationAddtion.attrib
    "additive ( replace | sum ) 'replace'
     accumulate ( none | sum ) 'none'
     %SVG.AnimationAddtion.extra.attrib;"
>

<!-- animate: Animate Element .......................... -->

<!ENTITY % SVG.animate.extra.content "" >

<!ENTITY % SVG.animate.element "INCLUDE" >
<![%SVG.animate.element;[
<!ENTITY % SVG.animate.content
    "( %SVG.Description.class; %SVG.animate.extra.content; )*"
>
<!ELEMENT %SVG.animate.qname; %SVG.animate.content; >
<!-- end of SVG.animate.element -->]]>

<!ENTITY % SVG.animate.attlist "INCLUDE" >
<![%SVG.animate.attlist;[
<!ATTLIST %SVG.animate.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.AnimationEvents.attrib;
    %SVG.External.attrib;
    %SVG.Animation.attrib;
    %SVG.AnimationAttribute.attrib;
    %SVG.AnimationTiming.attrib;
    %SVG.AnimationValue.attrib;
    %SVG.AnimationAddtion.attrib;
>
<!-- end of SVG.animate.attlist -->]]>

<!-- set: Set Element .................................. -->

<!ENTITY % SVG.set.extra.content "" >

<!ENTITY % SVG.set.element "INCLUDE" >
<![%SVG.set.element;[
<!ENTITY % SVG.set.content
    "( %SVG.Description.class; %SVG.set.extra.content; )*"
>
<!ELEMENT %SVG.set.qname; %SVG.set.content; >
<!-- end of SVG.set.element -->]]>

<!ENTITY % SVG.set.attlist "INCLUDE" >
<![%SVG.set.attlist;[
<!ATTLIST %SVG.set.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.AnimationEvents.attrib;
    %SVG.External.attrib;
    %SVG.Animation.attrib;
    %SVG.AnimationAttribute.attrib;
    %SVG.AnimationTiming.attrib;
    to CDATA #IMPLIED
>
<!-- end of SVG.set.attlist -->]]>

<!-- animateMotion: Animate Motion Element ............. -->

<!ENTITY % SVG.animateMotion.extra.content "" >

<!ENTITY % SVG.animateMotion.element "INCLUDE" >
<![%SVG.animateMotion.element;[
<!ENTITY % SVG.animateMotion.content
    "(( %SVG.Description.class; )*, %SVG.mpath.qname;?
        %SVG.animateMotion.extra.content; )"
>
<!ELEMENT %SVG.animateMotion.qname; %SVG.animateMotion.content; >
<!-- end of SVG.animateMotion.element -->]]>

<!ENTITY % SVG.animateMotion.attlist "INCLUDE" >
<![%SVG.animateMotion.attlist;[
<!ATTLIST %SVG.animateMotion.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.AnimationEvents.attrib;
    %SVG.External.attrib;
    %SVG.Animation.attrib;
    %SVG.AnimationTiming.attrib;
    %SVG.AnimationAddtion.attrib;
    calcMode ( discrete | linear | paced | spline ) 'paced'
    values CDATA #IMPLIED
    keyTimes CDATA #IMPLIED
    keySplines CDATA #IMPLIED
    from CDATA #IMPLIED
    to CDATA #IMPLIED
    by CDATA #IMPLIED
    path CDATA #IMPLIED
    keyPoints CDATA #IMPLIED
    rotate CDATA #IMPLIED
    origin CDATA #IMPLIED
>
<!-- end of SVG.animateMotion.attlist -->]]>

<!-- animateColor: Animate Color Element ............... -->

<!ENTITY % SVG.animateColor.extra.content "" >

<!ENTITY % SVG.animateColor.element "INCLUDE" >
<![%SVG.animateColor.element;[
<!ENTITY % SVG.animateColor.content
    "( %SVG.Description.class; %SVG.animateColor.extra.content; )*"
>
<!ELEMENT %SVG.animateColor.qname; %SVG.animateColor.content; >
<!-- end of SVG.animateColor.element -->]]>

<!ENTITY % SVG.animateColor.attlist "INCLUDE" >
<![%SVG.animateColor.attlist;[
<!ATTLIST %SVG.animateColor.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.AnimationEvents.attrib;
    %SVG.External.attrib;
    %SVG.Animation.attrib;
    %SVG.AnimationAttribute.attrib;
    %SVG.AnimationTiming.attrib;
    %SVG.AnimationValue.attrib;
    %SVG.AnimationAddtion.attrib;
>
<!-- end of SVG.animateColor.attlist -->]]>

<!-- animateTransform: Animate Transform Element ....... -->

<!ENTITY % SVG.animateTransform.extra.content "" >

<!ENTITY % SVG.animateTransform.element "INCLUDE" >
<![%SVG.animateTransform.element;[
<!ENTITY % SVG.animateTransform.content
    "( %SVG.Description.class; %SVG.animateTransform.extra.content; )*"
>
<!ELEMENT %SVG.animateTransform.qname; %SVG.animateTransform.content; >
<!-- end of SVG.animateTransform.element -->]]>

<!ENTITY % SVG.animateTransform.attlist "INCLUDE" >
<![%SVG.animateTransform.attlist;[
<!ATTLIST %SVG.animateTransform.qname;
    %SVG.Core.attrib;
    %SVG.Conditional.attrib;
    %SVG.AnimationEvents.attrib;
    %SVG.External.attrib;
    %SVG.Animation.attrib;
    %SVG.AnimationAttribute.attrib;
    %SVG.AnimationTiming.attrib;
    %SVG.AnimationValue.attrib;
    %SVG.AnimationAddtion.attrib;
    type ( translate | scale | rotate | skewX | skewY ) 'translate'
>
<!-- end of SVG.animateTransform.attlist -->]]>

<!-- mpath: Motion Path Element ........................ -->

<!ENTITY % SVG.mpath.extra.content "" >

<!ENTITY % SVG.mpath.element "INCLUDE" >
<![%SVG.mpath.element;[
<!ENTITY % SVG.mpath.content
    "( %SVG.Description.class; %SVG.mpath.extra.content; )*"
>
<!ELEMENT %SVG.mpath.qname; %SVG.mpath.content; >
<!-- end of SVG.mpath.element -->]]>

<!ENTITY % SVG.mpath.attlist "INCLUDE" >
<![%SVG.mpath.attlist;[
<!ATTLIST %SVG.mpath.qname;
    %SVG.Core.attrib;
    %SVG.XLinkRequired.attrib;
    %SVG.External.attrib;
>
<!-- end of SVG.mpath.attlist -->]]>

<!-- end of svg-animation.mod -->

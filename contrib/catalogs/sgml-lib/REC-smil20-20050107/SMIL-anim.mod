<!-- ======================================================================= -->
<!-- SMIL Animation Module  ================================================ -->
<!-- file: SMIL-anim.mod

  This is SMIL 2.0.

    	Copyright: 1998-2004 W3C (MIT, ERCIM, Keio), All Rights Reserved.
    	See http://www.w3.org/Consortium/Legal/.

	Author:     Jacco van Ossenbruggen
        Revision:   2001/07/31  Thierry Michel  

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

     PUBLIC "-//W3C//ELEMENTS SMIL 2.0 Animation//EN"
     SYSTEM "http://www.w3.org/2001/SMIL20/SMIL-anim.mod"

     ======================================================================= -->


<!-- ============================= Dependencies ============================ -->
<!-- The integrating profile is expected to define the following entities,
     Unless the defaults provided are sufficient.
 -->

<!-- SMIL.SplineAnimation.module entity:  Define as "INCLUDE" if the integrating
     profile includes the SMIL 2.0 SplineAnimation Module, "IGNORE" if not.
     The default is "IGNORE", i.e. by default SplineAnimation is not included
     in the integrating language profile.
 -->
<!ENTITY % SMIL.SplineAnimation.module "IGNORE">

<!-- Animation depends on SMIL Timing, importing the attributes listed
     in the SMIL.AnimationTime.attrib entity.  If the integrating profile does 
     include the SMIL.MinMaxTiming.module, its default value includes the 
     attributes defined in SMIL.BasicInlineTiming.attrib and 
	 SMIL.MinMaxTiming.attrib.  Otherwise, it is defaulted to 
	 SMIL.BasicInlineTiming.attrib, which is the minimum requirement.
     
     Note that the profile can override these defaults by redefining 
     SMIL.AnimationTime.attrib.  The profile is also expected to define 
     SMIL.fill.attrib and SMIL.fillDefault.attrib.
 -->
<!ENTITY % SMIL.MinMaxTiming.module "IGNORE">
<![%SMIL.MinMaxTiming.module;[
  <!ENTITY % SMIL.AnimationTime.attrib "
	%SMIL.BasicInlineTiming.attrib;
	%SMIL.BasicInlineTiming-deprecated.attrib;
	%SMIL.MinMaxTiming.attrib;
  ">
]]>
<!ENTITY % SMIL.AnimationTime.attrib "%SMIL.BasicInlineTiming.attrib;">
<!ENTITY % SMIL.fill.attrib "">

<!ENTITY % SMIL.animTimingAttrs "
  %SMIL.AnimationTime.attrib;             
  %SMIL.fill.attrib;            
  %SMIL.fillDefault.attrib;            
">

<!-- Language Designer chooses to integrate targetElement or xlink attributes.
     To integrate the targetElement attribute, define the entity
     animation-targetElement as "INCLUDE"; to integrate the XLink attributes,
     define animation-XLinkTarget as "INCLUDE".
     
     One or the other MUST be defined.  It is strongly recommended that only one
     of the two be defined.
-->

<!ENTITY % SMIL.animation-targetElement "IGNORE">
<![%SMIL.animation-targetElement;[
  <!ENTITY % SMIL.animTargetElementAttr
   "targetElement  IDREF  #IMPLIED"
  >
]]>
<!ENTITY % SMIL.animTargetElementAttr "">

<!ENTITY % SMIL.animation-XLinkTarget "IGNORE">
<![%SMIL.animation-XLinkTarget;[
  <!ENTITY % SMIL.animTargetElementXLink "
    actuate        (onRequest|onLoad)                  'onLoad' 
    href           %URI.datatype;                      #IMPLIED
    show           (new | embed | replace)             #FIXED 'embed'
    type           (simple | extended | locator | arc) #FIXED 'simple'
">
]]>
<!ENTITY % SMIL.animTargetElementXLink "">


<!-- ========================== Attribute Groups =========================== -->

<!-- All animation elements include these attributes -->
<!ENTITY % SMIL.animAttrsCommon
 "%Core.attrib;
  %I18n.attrib;
  %SMIL.Test.attrib;
  %SMIL.animTimingAttrs;
  %SMIL.animTargetElementAttr;
  %SMIL.animTargetElementXLink;"
>

<!-- All except animateMotion need an identified target attribute -->
<!ENTITY % SMIL.animAttrsNamedTarget
 "%SMIL.animAttrsCommon;
  attributeName  CDATA  #REQUIRED
  attributeType  CDATA  #IMPLIED"
>

<!-- All except set support the full animation-function specification,
     additive and cumulative animation.
     SplineAnimation adds the attributes keyTimes, keySplines and path,
	 and the calcMode value "spline", to those of BasicAnimation.
 -->
<![%SMIL.SplineAnimation.module;[
  <!ENTITY % SMIL.splineAnimCalcModeValues "| spline">
  <!ENTITY % SMIL.splineAnimValueAttrs
   "keyTimes CDATA #IMPLIED
    keySplines CDATA #IMPLIED"
  >
  <!ENTITY % SMIL.splineAnimPathAttr
   "path CDATA #IMPLIED"
  >
]]>
<!ENTITY % SMIL.splineAnimCalcModeValues "">
<!ENTITY % SMIL.splineAnimValueAttrs "">
<!ENTITY % SMIL.splineAnimPathAttr "">

<!ENTITY % SMIL.animValueAttrs "
  %SMIL.BasicAnimation.attrib;
  calcMode   (discrete|linear|paced %SMIL.splineAnimCalcModeValues;) 'linear'
  %SMIL.splineAnimValueAttrs;
  additive   (replace | sum) 'replace'
  accumulate (none | sum) 'none'"
>


<!-- ========================== Animation Elements ========================= -->

<!ENTITY % SMIL.animate.attrib  "">
<!ENTITY % SMIL.animate.content "EMPTY">
<!ENTITY % SMIL.animate.qname   "animate">
<!ELEMENT %SMIL.animate.qname; %SMIL.animate.content;>
<!ATTLIST %SMIL.animate.qname; %SMIL.animate.attrib;
  %SMIL.animAttrsNamedTarget;
  %SMIL.animValueAttrs;
>

<!ENTITY % SMIL.set.attrib  "">
<!ENTITY % SMIL.set.content "EMPTY">
<!ENTITY % SMIL.set.qname   "set">
<!ELEMENT %SMIL.set.qname; %SMIL.set.content;>
<!ATTLIST %SMIL.set.qname; %SMIL.set.attrib;
  %SMIL.animAttrsNamedTarget;
  to  CDATA  #IMPLIED
>

<!ENTITY % SMIL.animateMotion.attrib  "">
<!ENTITY % SMIL.animateMotion.content "EMPTY">
<!ENTITY % SMIL.animateMotion.qname   "animateMotion">
<!ELEMENT %SMIL.animateMotion.qname; %SMIL.animateMotion.content;>
<!ATTLIST %SMIL.animateMotion.qname; %SMIL.animateMotion.attrib;
  %SMIL.animAttrsCommon;
  %SMIL.animValueAttrs;
  %SMIL.splineAnimPathAttr;
  origin  (default)  "default"
>


<!ENTITY % SMIL.animateColor.attrib  "">
<!ENTITY % SMIL.animateColor.content "EMPTY">
<!ENTITY % SMIL.animateColor.qname   "animateColor">
<!ELEMENT %SMIL.animateColor.qname; %SMIL.animateColor.content;>
<!ATTLIST %SMIL.animateColor.qname; %SMIL.animateColor.attrib;
  %SMIL.animAttrsNamedTarget;
  %SMIL.animValueAttrs;
>

<!-- ========================== End Animation ============================= -->
<!-- end of SMIL-anim.mod -->

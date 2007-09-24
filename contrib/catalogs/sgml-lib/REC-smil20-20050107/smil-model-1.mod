<!-- ======================================================================  -->
<!-- SMIL 2.0 Document Model Module =======================================  -->
<!-- file: smil-model-1.mod

     This is SMIL 2.0.

    	Copyright: 1998-2004 W3C (MIT, ERCIM, Keio), All Rights Reserved.
    	See http://www.w3.org/Consortium/Legal/.

	Author: Warner ten Kate, Jacco van Ossenbruggen, Aaron Cohen
        Revision:   2001/07/31  Thierry Michel  

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

     PUBLIC "-//W3C//ENTITIES SMIL 2.0 Document Model 1.0//EN"
     SYSTEM "http://www.w3.org/2001/SMIL20/smil-model-1.mod"

     ======================================================================= -->

<!--
        This file defines the SMIL 2.0 Language Document Model.
        All attributes and content models are defined in the second
        half of this file.  We first start with some utility definitions.
        These are mainly used to simplify the use of Modules in the
        second part of the file.

-->

<!-- ================== Util: Head ========================================= -->
<!ENTITY % SMIL.head-meta.content       "%SMIL.metadata.qname;">
<!ENTITY % SMIL.head-layout.content     "%SMIL.layout.qname; 
                                       | %SMIL.switch.qname;">
<!ENTITY % SMIL.head-control.content    "%SMIL.customAttributes.qname;">
<!ENTITY % SMIL.head-transition.content "%SMIL.transition.qname;+">

<!--=================== Util: Body - Content Control ======================= -->
<!ENTITY % SMIL.content-control "%SMIL.switch.qname; | %SMIL.prefetch.qname;">
<!ENTITY % SMIL.content-control-attrs "%SMIL.Test.attrib; 
                                       %SMIL.customTestAttr.attrib; 
				       %SMIL.skip-content.attrib;">

<!--=================== Util: Body - Animation ========================= -->
<!ENTITY % SMIL.animation.elements "%SMIL.animate.qname; 
                                    | %SMIL.set.qname; 
                                    | %SMIL.animateMotion.qname; 
                                    | %SMIL.animateColor.qname;">

<!--=================== Util: Body - Media ========================= -->

<!ENTITY % SMIL.media-object "%SMIL.audio.qname; 
                              | %SMIL.video.qname; 
                              | %SMIL.animation.qname;
                              | %SMIL.text.qname;
                              | %SMIL.img.qname;
                              | %SMIL.textstream.qname;
                              | %SMIL.ref.qname;
                              | %SMIL.brush.qname;
                              | %SMIL.animation.elements;">

<!--=================== Util: Body - Timing ================================ -->
<!ENTITY % SMIL.BasicTimeContainers.class "%SMIL.par.qname; 
                                         | %SMIL.seq.qname;">

<!ENTITY % SMIL.ExclTimeContainers.class "%SMIL.excl.qname;">

<!ENTITY % SMIL.timecontainer.class   "%SMIL.BasicTimeContainers.class;
                                       |%SMIL.ExclTimeContainers.class;">

<!ENTITY % SMIL.timecontainer.content "%SMIL.timecontainer.class; 
                                     | %SMIL.media-object;
                                     | %SMIL.content-control;
                                     | %SMIL.a.qname;">

<!ENTITY % SMIL.smil-basictime.attrib "
 %SMIL.BasicInlineTiming.attrib;
 %SMIL.BasicInlineTiming-deprecated.attrib;
 %SMIL.MinMaxTiming.attrib;
">

<!ENTITY % SMIL.timecontainer.attrib "
 %SMIL.BasicInlineTiming.attrib;
 %SMIL.BasicInlineTiming-deprecated.attrib;
 %SMIL.MinMaxTiming.attrib;
 %SMIL.RestartTiming.attrib;
 %SMIL.RestartDefaultTiming.attrib;
 %SMIL.SyncBehavior.attrib;
 %SMIL.SyncBehaviorDefault.attrib;
 %SMIL.fillDefault.attrib;
">

<!-- ====================================================================== -->
<!-- ====================================================================== -->
<!-- ====================================================================== -->

<!-- 
     The actual content model and attribute definitions for each module 
     sections follow below.
-->

<!-- ================== Content Control =================================== -->
<!ENTITY % SMIL.BasicContentControl.module  "INCLUDE">
<!ENTITY % SMIL.CustomTestAttributes.module "INCLUDE">
<!ENTITY % SMIL.PrefetchControl.module      "INCLUDE">
<!ENTITY % SMIL.skip-contentControl.module   "INCLUDE">

<!ENTITY % SMIL.switch.content "((%SMIL.timecontainer.class;
                                | %SMIL.media-object;
                                | %SMIL.content-control;
                                | %SMIL.a.qname; 
                                | %SMIL.area.qname; 
                                | %SMIL.anchor.qname;)*
                                | %SMIL.layout.qname;*)">

<!ENTITY % SMIL.switch.attrib "%SMIL.Test.attrib; %SMIL.customTestAttr.attrib;">
<!ENTITY % SMIL.prefetch.attrib "
 %SMIL.timecontainer.attrib; 
 %SMIL.MediaClip.attrib; 
 %SMIL.MediaClip.attrib.deprecated; 
 %SMIL.Test.attrib; 
 %SMIL.customTestAttr.attrib; 
 %SMIL.skip-content.attrib; 
">

<!ENTITY % SMIL.customAttributes.attrib  "%SMIL.Test.attrib; %SMIL.skip-content.attrib;">
<!ENTITY % SMIL.customTest.attrib    "%SMIL.skip-content.attrib;">

<!-- ================== Animation ========================================= -->
<!ENTITY % SMIL.BasicAnimation.module "INCLUDE">

<!-- choose targetElement or XLink: -->
<!ENTITY % SMIL.animation-targetElement "INCLUDE">
<!ENTITY % SMIL.animation-XLinkTarget   "IGNORE">

<!ENTITY % SMIL.animate.content "EMPTY">
<!ENTITY % SMIL.animateColor.content "EMPTY">
<!ENTITY % SMIL.animateMotion.content "EMPTY">
<!ENTITY % SMIL.set.content "EMPTY">

<!ENTITY % SMIL.animate.attrib        "%SMIL.skip-content.attrib; %SMIL.customTestAttr.attrib;">
<!ENTITY % SMIL.animateColor.attrib   "%SMIL.skip-content.attrib; %SMIL.customTestAttr.attrib;">
<!ENTITY % SMIL.animateMotion.attrib  "%SMIL.skip-content.attrib; %SMIL.customTestAttr.attrib;">
<!ENTITY % SMIL.set.attrib            "%SMIL.skip-content.attrib; %SMIL.customTestAttr.attrib;">

<!-- ================== Layout ============================================ -->
<!ENTITY % SMIL.BasicLayout.module        "INCLUDE">
<!ENTITY % SMIL.AudioLayout.module        "INCLUDE">
<!ENTITY % SMIL.MultiWindowLayout.module  "INCLUDE">
<!ENTITY % SMIL.HierarchicalLayout.module "INCLUDE">

<!ENTITY % SMIL.layout.content "(%SMIL.region.qname;
                               | %SMIL.topLayout.qname;
			       | %SMIL.root-layout.qname; 
			       | %SMIL.regPoint.qname;)*">
<!ENTITY % SMIL.region.content "(%SMIL.region.qname;)*">
<!ENTITY % SMIL.topLayout.content "(%SMIL.region.qname;)*">
<!ENTITY % SMIL.rootlayout.content "EMPTY">
<!ENTITY % SMIL.regPoint.content "EMPTY">

<!ENTITY % SMIL.layout.attrib          "%SMIL.Test.attrib; %SMIL.customTestAttr.attrib;">
<!ENTITY % SMIL.rootlayout.attrib      "%SMIL.content-control-attrs;">
<!ENTITY % SMIL.topLayout.attrib       "%SMIL.content-control-attrs;">
<!ENTITY % SMIL.region.attrib          "%SMIL.content-control-attrs;">
<!ENTITY % SMIL.regPoint.attrib        "%SMIL.content-control-attrs;">

<!-- ================== Linking =========================================== -->
<!ENTITY % SMIL.LinkingAttributes.module "INCLUDE">
<!ENTITY % SMIL.BasicLinking.module      "INCLUDE">
<!ENTITY % SMIL.ObjectLinking.module   "INCLUDE">

<!ENTITY % SMIL.a.content      "(%SMIL.timecontainer.class;|%SMIL.media-object;|
                                 %SMIL.content-control;)*">
<!ENTITY % SMIL.area.content   "(%SMIL.animate.qname;| %SMIL.set.qname;)*">
<!ENTITY % SMIL.anchor.content "(%SMIL.animate.qname; | %SMIL.set.qname;)*">

<!ENTITY % SMIL.a.attrib      "%SMIL.smil-basictime.attrib; %SMIL.Test.attrib; %SMIL.customTestAttr.attrib;">
<!ENTITY % SMIL.area.attrib   "%SMIL.smil-basictime.attrib; %SMIL.content-control-attrs;"> 
<!ENTITY % SMIL.anchor.attrib "%SMIL.smil-basictime.attrib; %SMIL.content-control-attrs;"> 

<!-- ================== Media  ============================================ -->
<!ENTITY % SMIL.BasicMedia.module                     "INCLUDE">
<!ENTITY % SMIL.MediaClipping.module                  "INCLUDE">
<!ENTITY % SMIL.MediaClipping.deprecated.module       "INCLUDE">
<!ENTITY % SMIL.MediaClipMarkers.module               "INCLUDE">
<!ENTITY % SMIL.MediaParam.module                     "INCLUDE">
<!ENTITY % SMIL.BrushMedia.module                     "INCLUDE">
<!ENTITY % SMIL.MediaAccessibility.module             "INCLUDE">

<!ENTITY % SMIL.media-object.content "(%SMIL.animation.elements;
                                     | %SMIL.switch.qname;
                                     | %SMIL.anchor.qname;
                                     | %SMIL.area.qname;
                                     | %SMIL.param.qname;)*">
<!ENTITY % SMIL.media-object.attrib "
  %SMIL.BasicInlineTiming.attrib;
  %SMIL.BasicInlineTiming-deprecated.attrib;
  %SMIL.MinMaxTiming.attrib;
  %SMIL.RestartTiming.attrib;
  %SMIL.RestartDefaultTiming.attrib;
  %SMIL.SyncBehavior.attrib;
  %SMIL.SyncBehaviorDefault.attrib;
  %SMIL.endsync.media.attrib;
  %SMIL.fill.attrib;
  %SMIL.fillDefault.attrib;
  %SMIL.Test.attrib;
  %SMIL.customTestAttr.attrib;
  %SMIL.regionAttr.attrib;
  %SMIL.Transition.attrib;
  %SMIL.backgroundColor.attrib;
  %SMIL.backgroundColor-deprecated.attrib;
  %SMIL.Sub-region.attrib;
  %SMIL.RegistrationPoint.attrib;
  %SMIL.fit.attrib;
  %SMIL.tabindex.attrib;
">

<!ENTITY % SMIL.brush.attrib        "%SMIL.skip-content.attrib;">
<!ENTITY % SMIL.param.attrib        "%SMIL.content-control-attrs;">

<!-- ================== Metadata ========================================== -->
<!ENTITY % SMIL.meta.content     "EMPTY">
<!ENTITY % SMIL.meta.attrib      "%SMIL.skip-content.attrib;">

<!ENTITY % SMIL.metadata.content "EMPTY">
<!ENTITY % SMIL.metadata.attrib  "%SMIL.skip-content.attrib;">

<!-- ================== Structure ========================================= -->
<!ENTITY % SMIL.Structure.module "INCLUDE">
<!ENTITY % SMIL.smil.content "(%SMIL.head.qname;?,%SMIL.body.qname;?)">
<!ENTITY % SMIL.head.content "(
	 %SMIL.meta.qname;*,
	 ((%SMIL.head-control.content;),   %SMIL.meta.qname;*)?,
	 ((%SMIL.head-meta.content;),      %SMIL.meta.qname;*)?,
	 ((%SMIL.head-layout.content;),    %SMIL.meta.qname;*)?,
	 ((%SMIL.head-transition.content;),%SMIL.meta.qname;*)?
)">
<!ENTITY % SMIL.body.content "(%SMIL.timecontainer.class;|%SMIL.media-object;|
                          %SMIL.content-control;|a)*">

<!ENTITY % SMIL.smil.attrib "%SMIL.Test.attrib;">
<!ENTITY % SMIL.body.attrib "
	%SMIL.timecontainer.attrib; 
	%SMIL.Description.attrib;
	%SMIL.fill.attrib;
">

<!-- ================== Transitions ======================================= -->
<!ENTITY % SMIL.BasicTransitions.module        "INCLUDE">
<!ENTITY % SMIL.TransitionModifiers.module     "INCLUDE">
<!ENTITY % SMIL.InlineTransitions.module       "IGNORE">

<!ENTITY % SMIL.transition.content "EMPTY">
<!ENTITY % SMIL.transition.attrib "%SMIL.content-control-attrs;">

<!-- ================== Timing ============================================ -->
<!ENTITY % SMIL.BasicInlineTiming.module      "INCLUDE">
<!ENTITY % SMIL.SyncbaseTiming.module         "INCLUDE">
<!ENTITY % SMIL.EventTiming.module            "INCLUDE">
<!ENTITY % SMIL.WallclockTiming.module        "INCLUDE">
<!ENTITY % SMIL.MultiSyncArcTiming.module     "INCLUDE">
<!ENTITY % SMIL.MediaMarkerTiming.module      "INCLUDE">
<!ENTITY % SMIL.MinMaxTiming.module           "INCLUDE">
<!ENTITY % SMIL.BasicTimeContainers.module    "INCLUDE">
<!ENTITY % SMIL.ExclTimeContainers.module     "INCLUDE">
<!ENTITY % SMIL.PrevTiming.module             "INCLUDE">
<!ENTITY % SMIL.RestartTiming.module          "INCLUDE">
<!ENTITY % SMIL.SyncBehavior.module           "INCLUDE">
<!ENTITY % SMIL.SyncBehaviorDefault.module    "INCLUDE">
<!ENTITY % SMIL.RestartDefault.module         "INCLUDE">
<!ENTITY % SMIL.fillDefault.module            "INCLUDE">

<!ENTITY % SMIL.par.attrib "
	%SMIL.endsync.attrib; 
        %SMIL.fill.attrib;
	%SMIL.timecontainer.attrib; 
	%SMIL.Test.attrib; 
	%SMIL.customTestAttr.attrib; 
	%SMIL.regionAttr.attrib;
">
<!ENTITY % SMIL.seq.attrib "
        %SMIL.fill.attrib;
	%SMIL.timecontainer.attrib; 
	%SMIL.Test.attrib; 
	%SMIL.customTestAttr.attrib; 
	%SMIL.regionAttr.attrib;
">
<!ENTITY % SMIL.excl.attrib "
	%SMIL.endsync.attrib; 
        %SMIL.fill.attrib;
	%SMIL.timecontainer.attrib; 
	%SMIL.Test.attrib; 
	%SMIL.customTestAttr.attrib; 
	%SMIL.regionAttr.attrib; 
        %SMIL.skip-content.attrib;
">
<!ENTITY % SMIL.par.content "(%SMIL.timecontainer.content;)*">
<!ENTITY % SMIL.seq.content "(%SMIL.timecontainer.content;)*">
<!ENTITY % SMIL.excl.content "((%SMIL.timecontainer.content;)*
                              | %SMIL.priorityClass.qname;+)">

<!ENTITY % SMIL.priorityClass.attrib  "%SMIL.content-control-attrs;">
<!ENTITY % SMIL.priorityClass.content "(%SMIL.timecontainer.content;)*">

<!-- end of smil-model-1.mod -->

<!-- ======================================================================= -->
<!-- SMIL 2.0 Layout Modules =============================================== -->
<!-- file: SMIL-layout.mod

        This is SMIL 2.0.

    	Copyright: 1998-2004 W3C (MIT, ERCIM, Keio), All Rights Reserved.
    	See http://www.w3.org/Consortium/Legal/.

	Author:     Jacco van Ossenbruggen, Aaron Cohen
        Revision:   2001/07/31  Thierry Michel

        This DTD module is identified by the PUBLIC and SYSTEM identifiers:

        PUBLIC "-//W3C//ELEMENTS SMIL 2.0 Layout//EN"
        SYSTEM "http://www.w3.org/2001/SMIL20/SMIL-layout.mod"

        ==================================================================== -->

<!-- ================== BasicLayout ======================================== -->
<!-- ================== BasicLayout Profiling Entities ===================== -->
<!ENTITY % SMIL.layout.attrib       "">
<!ENTITY % SMIL.region.attrib       "">
<!ENTITY % SMIL.rootlayout.attrib   "">
<!ENTITY % SMIL.layout.content     "EMPTY">
<!ENTITY % SMIL.region.content     "EMPTY">
<!ENTITY % SMIL.rootlayout.content "EMPTY">

<!-- ================== BasicLayout Entities =============================== -->
<!ENTITY % SMIL.common-layout-attrs "
        height              CDATA    'auto'
        width               CDATA    'auto'
        %SMIL.backgroundColor.attrib;
">

<!ENTITY % SMIL.region-attrs "
        bottom              CDATA    'auto'
        left                CDATA    'auto'
        right               CDATA    'auto'
        top                 CDATA    'auto'
        z-index             CDATA    #IMPLIED
	showBackground      (always|whenActive) 'always'
	%SMIL.fit.attrib;
">

<!-- ================== BasicLayout Elements =============================== -->
<!--
     Layout contains the region and root-layout elements defined by
     smil-basic-layout or other elements defined by an external layout
     mechanism.
-->

<!ENTITY % SMIL.layout.qname "layout">
<!ELEMENT %SMIL.layout.qname; %SMIL.layout.content;>
<!ATTLIST %SMIL.layout.qname; %SMIL.layout.attrib;
	%Core.attrib;
	%I18n.attrib;
        type CDATA 'text/smil-basic-layout'
>

<!-- ================== Region Element ======================================-->
<!ENTITY % SMIL.region.qname "region">
<!ELEMENT %SMIL.region.qname; %SMIL.region.content;>
<!ATTLIST %SMIL.region.qname; %SMIL.region.attrib;
	%Core.attrib;
	%I18n.attrib;
        %SMIL.backgroundColor-deprecated.attrib;
        %SMIL.common-layout-attrs;
        %SMIL.region-attrs;
        regionName CDATA #IMPLIED
>

<!-- ================== Root-layout Element =================================-->
<!ENTITY % SMIL.root-layout.qname "root-layout">
<!ELEMENT %SMIL.root-layout.qname; %SMIL.rootlayout.content; >
<!ATTLIST %SMIL.root-layout.qname; %SMIL.rootlayout.attrib;
	%Core.attrib;
	%I18n.attrib;
        %SMIL.backgroundColor-deprecated.attrib;
        %SMIL.common-layout-attrs;
>


<!-- ================== AudioLayout ======================================== -->
<!ENTITY % SMIL.AudioLayout.module "IGNORE">
<![%SMIL.AudioLayout.module;[
  <!-- ================== AudioLayout Entities ============================= -->
  <!ENTITY % SMIL.audio-attrs "
        soundLevel                        CDATA    '100&#37;'
  ">

  <!-- ================ AudioLayout Elements =============================== -->
  <!-- ================ Add soundLevel to region element =================== -->
  <!ATTLIST %SMIL.region.qname; %SMIL.audio-attrs;>
]]> <!-- end AudioLayout.module -->


<!-- ================ MultiWindowLayout ==================================== -->
<!ENTITY % SMIL.MultiWindowLayout.module "IGNORE">
<![%SMIL.MultiWindowLayout.module;[
  <!-- ============== MultiWindowLayout Profiling Entities ================= -->
  <!ENTITY % SMIL.topLayout.attrib    "">
  <!ENTITY % SMIL.topLayout.content   "EMPTY">
  
  <!-- ============== MultiWindowLayout Elements =========================== -->
  <!--================= topLayout element ================================== -->
  <!ENTITY % SMIL.topLayout.qname "topLayout">
  <!ELEMENT %SMIL.topLayout.qname; %SMIL.topLayout.content;>
  <!ATTLIST %SMIL.topLayout.qname; %SMIL.topLayout.attrib;
	%Core.attrib;
	%I18n.attrib;
        %SMIL.common-layout-attrs;
        close               (onRequest|whenNotActive) 'onRequest'
        open                (onStart|whenActive)      'onStart'
  >
]]> <!-- end MultiWindowLayout.module -->


<!-- ====================== HierarchicalLayout ============================= -->
<!ENTITY % SMIL.HierarchicalLayout.module "IGNORE">
<![%SMIL.HierarchicalLayout.module;[
  <!-- ========== HierarchicalLayout Profiling Entities ==================== -->
  <!ENTITY % SMIL.regPoint.attrib     "">
  <!ENTITY % SMIL.regPoint.content   "EMPTY">

  <!-- ============ HierarchicalLayout Elements ============================ -->
  <!ENTITY % SMIL.regPoint.qname "regPoint">
  <!ELEMENT %SMIL.regPoint.qname; %SMIL.regPoint.content;>
  <!ATTLIST %SMIL.regPoint.qname; %SMIL.regPoint.attrib;
	%Core.attrib;
	%I18n.attrib;
        %SMIL.regAlign.attrib;
        bottom              CDATA    'auto'
        left                CDATA    'auto'
        right               CDATA    'auto'
        top                 CDATA    'auto'
  >
]]> <!-- end HierarchicalLayout.module -->


<!-- end of SMIL-layout.mod -->

<!-- ...................................................................... -->
<!-- SMIL 2.0 Common Attributes Module  ................................... -->
<!-- file: smil-attribs-1.mod

      This is SMIL 2.0.

    	Copyright: 1998-2004 W3C (MIT, ERCIM, Keio), All Rights Reserved.
    	See http://www.w3.org/Consortium/Legal/.

	Revision:   2001/06/03  Thierry Michel  
     The revision includes update of:           
     E45 Errata:      
     see (http://www.w3.org/2001/07/REC-SMIL20-20010731-errata#E45)
     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

     PUBLIC "-//W3C//ENTITIES SMIL 2.0 Common Attributes 1.0//EN"
     SYSTEM "http://www.w3.org/2001/SMIL20/smil-attribs-1.mod"

     ...................................................................... -->

<!-- Common Attributes

     This module declares the common attributes for the SMIL DTD Modules.
-->

<!ENTITY % SMIL.pfx "">

<!ENTITY % id.attrib
 "%SMIL.pfx;id           ID                       #IMPLIED"
>

<!ENTITY % class.attrib
 "%SMIL.pfx;class        CDATA                    #IMPLIED"
>

<!ENTITY % title.attrib
 "%SMIL.pfx;title        %Text.datatype;                   #IMPLIED"
>

<!ENTITY % longdesc.attrib
 "%SMIL.pfx;longdesc     %URI.datatype;                    #IMPLIED"
>

<!ENTITY % alt.attrib
 "%SMIL.pfx;alt          %Text.datatype;                   #IMPLIED"
>

<!ENTITY % SMIL.Accessibility.attrib "
 %longdesc.attrib;
 %alt.attrib;
">

<!ENTITY % Core.extra.attrib "" >
<!ENTITY % Core.attrib "
  xml:base %URI.datatype; #IMPLIED
  %id.attrib;
  %class.attrib;
  %title.attrib;
  %SMIL.Accessibility.attrib;
  %Core.extra.attrib;
">

<!ENTITY % I18n.extra.attrib "" >
<!ENTITY % I18n.attrib "
  xml:lang %LanguageCode.datatype; #IMPLIED
  %I18n.extra.attrib;"
>

<!ENTITY % SMIL.Description.attrib "
 %SMIL.pfx;abstract        %Text.datatype;   #IMPLIED
 %SMIL.pfx;author          %Text.datatype;   #IMPLIED
 %SMIL.pfx;copyright       %Text.datatype;   #IMPLIED
">

<!ENTITY % SMIL.tabindex.attrib "
 %SMIL.pfx;tabindex        %Number.datatype;   #IMPLIED
">

<!-- ================== BasicLayout ======================================= -->
<!ENTITY % SMIL.regionAttr.attrib "
 %SMIL.pfx;region         CDATA #IMPLIED
">

<!ENTITY % SMIL.fill.attrib "
 %SMIL.pfx;fill (remove|freeze|hold|transition|auto|default) 'default'
">

<!ENTITY % SMIL.fillDefault.attrib "
 %SMIL.pfx;fillDefault (remove|freeze|hold|transition|auto|inherit) 'inherit'
">

<!-- ================== HierarchicalLayout ================================ -->
<!ENTITY % SMIL.backgroundColor.attrib "
 %SMIL.pfx;backgroundColor     CDATA    #IMPLIED
">
<!ENTITY % SMIL.backgroundColor-deprecated.attrib "
 %SMIL.pfx;background-color     CDATA    #IMPLIED
">

<!ENTITY % SMIL.Sub-region.attrib "
 %SMIL.pfx;top     CDATA    'auto'
 %SMIL.pfx;bottom  CDATA    'auto'
 %SMIL.pfx;left    CDATA    'auto'
 %SMIL.pfx;right   CDATA    'auto'
 %SMIL.pfx;height  CDATA    'auto'
 %SMIL.pfx;width   CDATA    'auto'
 %SMIL.pfx;z-index CDATA    #IMPLIED
">

<!ENTITY % SMIL.fit.attrib "
 %SMIL.pfx;fit            (hidden|fill|meet|scroll|slice)   #IMPLIED 
">

<!-- ================ Registration Point attribute for media elements ============ -->
<!-- integrating language using HierarchicalLayout must include regPoint   -->
<!-- attribute on media elements for regPoint elements to be useful        -->

<!ENTITY % SMIL.regPointAttr.attrib "
 %SMIL.pfx;regPoint  CDATA    #IMPLIED
">

<!ENTITY % SMIL.regAlign.attrib "
 %SMIL.pfx;regAlign  (topLeft|topMid|topRight|midLeft|center|
                     midRight|bottomLeft|bottomMid|bottomRight) #IMPLIED
">

<!ENTITY % SMIL.RegistrationPoint.attrib "
 %SMIL.regPointAttr.attrib;
 %SMIL.regAlign.attrib;
">

<!--=================== Content Control =======================-->
<!-- customTest Attribute, do not confuse with customTest element! -->
<!ENTITY % SMIL.customTestAttr.attrib "
        %SMIL.pfx;customTest              CDATA          #IMPLIED
">

<!-- ========================= SkipContentControl Module ========================= -->
<!ENTITY % SMIL.skip-content.attrib "
	%SMIL.pfx;skip-content		(true|false)	'true'
">

<!-- Content Control Test Attributes --> 

<!ENTITY % SMIL.Test.attrib "
        %SMIL.pfx;systemBitrate                	CDATA		#IMPLIED
	%SMIL.pfx;systemCaptions		(on|off)	#IMPLIED
	%SMIL.pfx;systemLanguage		CDATA		#IMPLIED
	%SMIL.pfx;systemOverdubOrSubtitle	(overdub|subtitle) #IMPLIED
	%SMIL.pfx;systemRequired		CDATA		#IMPLIED
	%SMIL.pfx;systemScreenSize		CDATA		#IMPLIED
	%SMIL.pfx;systemScreenDepth		CDATA		#IMPLIED
	%SMIL.pfx;systemAudioDesc		(on|off)	#IMPLIED
	%SMIL.pfx;systemOperatingSystem		NMTOKEN		#IMPLIED
	%SMIL.pfx;systemCPU			NMTOKEN		#IMPLIED
	%SMIL.pfx;systemComponent		CDATA		#IMPLIED

	%SMIL.pfx;system-bitrate		CDATA		#IMPLIED
	%SMIL.pfx;system-captions		(on|off)	#IMPLIED
	%SMIL.pfx;system-language		CDATA		#IMPLIED
	%SMIL.pfx;system-overdub-or-caption	(overdub|caption) #IMPLIED
	%SMIL.pfx;system-required		CDATA		#IMPLIED
	%SMIL.pfx;system-screen-size		CDATA		#IMPLIED
	%SMIL.pfx;system-screen-depth		CDATA		#IMPLIED
">

<!-- SMIL Animation Module  ================================================ -->
<!ENTITY % SMIL.BasicAnimation.attrib "
  %SMIL.pfx;values     CDATA #IMPLIED
  %SMIL.pfx;from       CDATA #IMPLIED
  %SMIL.pfx;to         CDATA #IMPLIED
  %SMIL.pfx;by         CDATA #IMPLIED
">

<!-- SMIL Timing Module  =================================================== -->
<!ENTITY % SMIL.BasicInlineTiming.attrib "
  %SMIL.pfx;dur                       %TimeValue.datatype; #IMPLIED
  %SMIL.pfx;repeatCount               %TimeValue.datatype; #IMPLIED
  %SMIL.pfx;repeatDur                 %TimeValue.datatype; #IMPLIED
  %SMIL.pfx;begin                     %TimeValue.datatype; #IMPLIED
  %SMIL.pfx;end                       %TimeValue.datatype; #IMPLIED
">

<!ENTITY % SMIL.MinMaxTiming.attrib "
  %SMIL.pfx;min                       %TimeValue.datatype; '0'
  %SMIL.pfx;max                       %TimeValue.datatype; 'indefinite'
">

<!ENTITY % SMIL.BasicInlineTiming-deprecated.attrib "
  %SMIL.pfx;repeat                   %TimeValue.datatype; #IMPLIED
">

<!ENTITY % SMIL.endsync.attrib "
  %SMIL.pfx;endsync               CDATA 'last'
">

<!-- endsync has a different default when applied to media elements -->
<!ENTITY % SMIL.endsync.media.attrib "
  %SMIL.pfx;endsync               CDATA 'media'
">

<!ENTITY % SMIL.TimeContainerAttributes.attrib "
  %SMIL.pfx;timeAction            CDATA #IMPLIED
  %SMIL.pfx;timeContainer         CDATA #IMPLIED
">

<!ENTITY % SMIL.RestartTiming.attrib "
  %SMIL.pfx;restart (always|whenNotActive|never|default) 'default'
">

<!ENTITY % SMIL.RestartDefaultTiming.attrib "
  %SMIL.pfx;restartDefault (inherit|always|never|whenNotActive) 'inherit'
">

<!ENTITY % SMIL.SyncBehavior.attrib "
  %SMIL.pfx;syncBehavior (canSlip|locked|independent|default) 'default'
  %SMIL.pfx;syncTolerance %TimeValue.datatype;                'default'
">

<!ENTITY % SMIL.SyncBehaviorDefault.attrib "
  %SMIL.pfx;syncBehaviorDefault (canSlip|locked|independent|inherit) 'inherit'
  %SMIL.pfx;syncToleranceDefault  %TimeValue.datatype;               'inherit'
">

<!ENTITY % SMIL.SyncMaster.attrib "
  %SMIL.pfx;syncMaster    (true|false)                 'false'
">

<!-- ================== Time Manipulations ================================= -->
<!ENTITY % SMIL.TimeManipulations.attrib "
  %SMIL.pfx;accelerate		%Number.datatype; '0'
  %SMIL.pfx;decelerate		%Number.datatype; '0'
  %SMIL.pfx;speed		%Number.datatype; '1.0'
  %SMIL.pfx;autoReverse         (true|false)      'false'
">

<!-- ================== Media Objects ====================================== -->
<!ENTITY % SMIL.MediaClip.attrib "
  %SMIL.pfx;clipBegin      CDATA   #IMPLIED
  %SMIL.pfx;clipEnd        CDATA   #IMPLIED
">
<!ENTITY % SMIL.MediaClip.attrib.deprecated "
  %SMIL.pfx;clip-begin     CDATA   #IMPLIED
  %SMIL.pfx;clip-end       CDATA   #IMPLIED
">

<!-- ================== Streaming Media ==================================== -->
<!ENTITY % SMIL.Streaming-media.attrib "
  %SMIL.pfx;port                  CDATA   #IMPLIED
  %SMIL.pfx;rtpformat             CDATA   #IMPLIED
  %SMIL.pfx;transport             CDATA   #IMPLIED
">

<!ENTITY % SMIL.Streaming-timecontainer.attrib "
  %SMIL.pfx;control               CDATA   #IMPLIED
">

<!-- ================== Transitions Media ================================== -->
<!ENTITY % SMIL.Transition.attrib "
 %SMIL.pfx;transIn                CDATA        #IMPLIED
 %SMIL.pfx;transOut               CDATA        #IMPLIED
">

<!-- end of smil-attribs-1.mod -->

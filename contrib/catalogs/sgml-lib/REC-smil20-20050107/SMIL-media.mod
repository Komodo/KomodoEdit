<!-- ======================================================================= -->
<!-- SMIL 2.0 Media Objects Modules ======================================== -->
<!-- file: SMIL-media.mod

     This is SMIL 2.0.

    	Copyright: 1998-2004 W3C (MIT, ERCIM, Keio), All Rights Reserved.
    	See http://www.w3.org/Consortium/Legal/.

	Author:     Rob Lanphier, Jacco van Ossenbruggen
     Revision:   2004/06/03  by Thierry Michel

     The revision includes update of:      
     E37 Errata: 
     see (http://www.w3.org/2001/07/REC-SMIL20-20010731-errata#E37)


     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

     PUBLIC "-//W3C//ELEMENTS SMIL 2.0 Media Objects//EN"
     SYSTEM "http://www.w3.org/2001/SMIL20/SMIL-media.mod"

     ======================================================================= -->

<!-- ================== Profiling Entities ================================= -->

<!ENTITY % SMIL.MediaClipping.module "IGNORE">
<![%SMIL.MediaClipping.module;[
  <!ENTITY % SMIL.mo-attributes-MediaClipping "
	%SMIL.MediaClip.attrib;
  ">
]]>
<!ENTITY % SMIL.mo-attributes-MediaClipping "">

<!ENTITY % SMIL.MediaClipping.deprecated.module "IGNORE">
<![%SMIL.MediaClipping.module;[
  <!ENTITY % SMIL.mo-attributes-MediaClipping-deprecated "
	%SMIL.MediaClip.attrib.deprecated;
  ">
  ]]>
<!ENTITY % SMIL.mo-attributes-MediaClipping-deprecated "">

<!ENTITY % SMIL.MediaParam.module "IGNORE">
<![%SMIL.MediaParam.module;[
  <!ENTITY % SMIL.mo-attributes-MediaParam "
        erase        (whenDone|never)	'whenDone'
        mediaRepeat  (preserve|strip)	'preserve'
        sensitivity   CDATA             'opaque'
  ">
  <!ENTITY % SMIL.param.qname "param">
  <!ELEMENT %SMIL.param.qname; EMPTY>

  <!ATTLIST %SMIL.param.qname; %SMIL.param.attrib;
    %Core.attrib;
    %I18n.attrib;
    name        CDATA          #IMPLIED
    value       CDATA          #IMPLIED
    valuetype   (data|ref|object) "data"
    type        %ContentType.datatype;  #IMPLIED
  >
]]>
<!ENTITY % SMIL.mo-attributes-MediaParam "">

<!ENTITY % SMIL.MediaAccessibility.module "IGNORE">
<![%SMIL.MediaAccessibility.module;[
  <!ENTITY % SMIL.mo-attributes-MediaAccessibility "
        readIndex    CDATA           #IMPLIED
  ">
]]>
<!ENTITY % SMIL.mo-attributes-MediaAccessibility "">

<!ENTITY % SMIL.BasicMedia.module "INCLUDE">
<![%SMIL.BasicMedia.module;[
  <!ENTITY % SMIL.media-object.content "EMPTY">
  <!ENTITY % SMIL.media-object.attrib "">

  <!-- ================ Media Objects Entities ============================= -->

  <!ENTITY % SMIL.mo-attributes-BasicMedia "
        src             CDATA   #IMPLIED
        type            CDATA   #IMPLIED
  ">

  <!ENTITY % SMIL.mo-attributes "
        %Core.attrib;
        %I18n.attrib;
        %SMIL.Description.attrib;
        %SMIL.mo-attributes-BasicMedia;
        %SMIL.mo-attributes-MediaParam;
        %SMIL.mo-attributes-MediaAccessibility;
        %SMIL.media-object.attrib;
  ">

  <!--
     Most info is in the attributes, media objects are empty or
     have children defined at the language integration level:
  -->

  <!ENTITY % SMIL.mo-content "%SMIL.media-object.content;">

  <!-- ================ Media Objects Elements ============================= -->
  <!ENTITY % SMIL.ref.qname        "ref">
  <!ENTITY % SMIL.audio.qname      "audio">
  <!ENTITY % SMIL.img.qname        "img">
  <!ENTITY % SMIL.video.qname      "video">
  <!ENTITY % SMIL.text.qname       "text">
  <!ENTITY % SMIL.textstream.qname "textstream">
  <!ENTITY % SMIL.animation.qname  "animation">

  <!ENTITY % SMIL.ref.content        "%SMIL.mo-content;">
  <!ENTITY % SMIL.audio.content      "%SMIL.mo-content;">
  <!ENTITY % SMIL.img.content        "%SMIL.mo-content;">
  <!ENTITY % SMIL.video.content      "%SMIL.mo-content;">
  <!ENTITY % SMIL.text.content       "%SMIL.mo-content;">
  <!ENTITY % SMIL.textstream.content "%SMIL.mo-content;">
  <!ENTITY % SMIL.animation.content  "%SMIL.mo-content;">

  <!ELEMENT %SMIL.ref.qname;           %SMIL.ref.content;>
  <!ELEMENT %SMIL.audio.qname;         %SMIL.audio.content;>
  <!ELEMENT %SMIL.img.qname;           %SMIL.img.content;>
  <!ELEMENT %SMIL.video.qname;         %SMIL.video.content;>
  <!ELEMENT %SMIL.text.qname;          %SMIL.text.content;>
  <!ELEMENT %SMIL.textstream.qname;    %SMIL.textstream.content;>
  <!ELEMENT %SMIL.animation.qname;     %SMIL.animation.content;>

  <!ATTLIST %SMIL.img.qname;           
	  %SMIL.mo-attributes;
  >
  <!ATTLIST %SMIL.text.qname;          
	  %SMIL.mo-attributes;
  >
  <!ATTLIST %SMIL.ref.qname;           
          %SMIL.mo-attributes-MediaClipping;
          %SMIL.mo-attributes-MediaClipping-deprecated;
	  %SMIL.mo-attributes;
  >
  <!ATTLIST %SMIL.audio.qname;         
          %SMIL.mo-attributes-MediaClipping;
          %SMIL.mo-attributes-MediaClipping-deprecated;
	  %SMIL.mo-attributes;
  >
  <!ATTLIST %SMIL.video.qname;         
          %SMIL.mo-attributes-MediaClipping;
          %SMIL.mo-attributes-MediaClipping-deprecated;
	  %SMIL.mo-attributes;
  >
  <!ATTLIST %SMIL.textstream.qname;    
          %SMIL.mo-attributes-MediaClipping;
          %SMIL.mo-attributes-MediaClipping-deprecated;
	  %SMIL.mo-attributes;
  >
  <!ATTLIST %SMIL.animation.qname;     
          %SMIL.mo-attributes-MediaClipping;
          %SMIL.mo-attributes-MediaClipping-deprecated;
	  %SMIL.mo-attributes;
  >
]]>
<!ENTITY % SMIL.mo-attributes-BasicMedia "">

<!-- BrushMedia -->
<!ENTITY % SMIL.BrushMedia.module "IGNORE">
<![%SMIL.BrushMedia.module;[
  <!ENTITY % SMIL.brush.attrib "">
  <!ENTITY % SMIL.brush.content "%SMIL.mo-content;">
  <!ENTITY % SMIL.brush.qname "brush">
  <!ELEMENT %SMIL.brush.qname; %SMIL.brush.content;>
  <!ATTLIST %SMIL.brush.qname; %SMIL.brush.attrib; 
        %Core.attrib;
        %I18n.attrib;
        %SMIL.Description.attrib;
        %SMIL.mo-attributes-MediaAccessibility;
        %SMIL.mo-attributes-MediaParam;
        %SMIL.media-object.attrib;
        color        CDATA            #IMPLIED
  >
]]>

<!-- end of SMIL-media.mod -->

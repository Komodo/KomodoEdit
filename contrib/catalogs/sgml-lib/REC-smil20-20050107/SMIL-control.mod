<!-- ================================================================= -->
<!-- SMIL Content Control Module  ==================================== -->
<!-- file: SMIL-control.mod

      This is SMIL 2.0.

    	Copyright: 1998-2004 W3C (MIT, ERCIM, Keio), All Rights Reserved.
    	See http://www.w3.org/Consortium/Legal/.

	Author:     Jacco van Ossenbruggen, Aaron Cohen
        Revision:   2001/07/31  Thierry Michel  

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

     PUBLIC "-//W3C//ELEMENTS SMIL 2.0 Content Control//EN"
     SYSTEM "http://www.w3.org/2001/SMIL20/SMIL-control.mod"

     ================================================================= -->

<!ENTITY % SMIL.BasicContentControl.module "INCLUDE">
<![%SMIL.BasicContentControl.module;[
  <!ENTITY % SMIL.switch.attrib "">
  <!ENTITY % SMIL.switch.content "EMPTY">
  <!ENTITY % SMIL.switch.qname "switch">
  
  <!ELEMENT %SMIL.switch.qname; %SMIL.switch.content;>
  <!ATTLIST %SMIL.switch.qname; %SMIL.switch.attrib;
        %Core.attrib;
        %I18n.attrib;
  >
]]>

<!-- ========================= CustomTest Elements ========================= -->
<!ENTITY % SMIL.CustomTestAttributes.module "IGNORE">
<![%SMIL.CustomTestAttributes.module;[

  <!ENTITY % SMIL.customTest.attrib "">
  <!ENTITY % SMIL.customTest.qname "customTest">
  <!ENTITY % SMIL.customTest.content "EMPTY">
  <!ELEMENT %SMIL.customTest.qname; %SMIL.customTest.content;>
  <!ATTLIST %SMIL.customTest.qname; %SMIL.customTest.attrib;
	defaultState (true|false)                   'false'
	override     (visible|hidden) 		    'hidden'
	uid          %URI.datatype;                 #IMPLIED
        %Core.attrib;
        %I18n.attrib;
  >
  <!ENTITY % SMIL.customAttributes.attrib "">
  <!ENTITY % SMIL.customAttributes.qname "customAttributes">
  <!ENTITY % SMIL.customAttributes.content "(customTest+)">
  <!ELEMENT %SMIL.customAttributes.qname; %SMIL.customAttributes.content;>
  <!ATTLIST %SMIL.customAttributes.qname; %SMIL.customAttributes.attrib;
        %Core.attrib;
        %I18n.attrib;
  >

]]> <!-- end of CustomTestAttributes -->

<!-- ========================= PrefetchControl Elements ==================== -->
<!ENTITY % SMIL.PrefetchControl.module "IGNORE">
<![%SMIL.PrefetchControl.module;[
  <!ENTITY % SMIL.prefetch.attrib "">
  <!ENTITY % SMIL.prefetch.qname "prefetch">
  <!ENTITY % SMIL.prefetch.content "EMPTY">
  <!ELEMENT %SMIL.prefetch.qname; %SMIL.prefetch.content;>
  <!ATTLIST %SMIL.prefetch.qname; %SMIL.prefetch.attrib;
	src           %URI.datatype;    #IMPLIED
	mediaSize     CDATA		#IMPLIED
	mediaTime     CDATA		#IMPLIED
	bandwidth     CDATA		#IMPLIED
        %Core.attrib;
        %I18n.attrib;
  >
]]>

<!-- end of SMIL-control.mod -->

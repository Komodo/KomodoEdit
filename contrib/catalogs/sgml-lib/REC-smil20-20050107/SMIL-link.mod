<!-- ======================================================================= -->
<!-- SMIL Linking Module  ================================================== -->
<!-- file: SMIL-link.mod

     This is SMIL 2.0.

    	Copyright: 1998-2004 W3C (MIT, ERCIM, Keio), All Rights Reserved.
    	See http://www.w3.org/Consortium/Legal/.

	Author: Jacco van Ossenbruggen, Lloyd Rutledge, Aaron Cohen
     Revision:   2004/06/03  by Thierry Michel

     The revision includes update of: 
     E10 Errata: 
     see (http://www.w3.org/2001/07/REC-SMIL20-20010731-errata#E10)   
     E36 Errata: 
     see (http://www.w3.org/2001/07/REC-SMIL20-20010731-errata#E36)


     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

     PUBLIC "-//W3C//ELEMENTS SMIL 2.0 Linking//EN"
     SYSTEM "http://www.w3.org/2001/SMIL20/SMIL-link.mod"

     ======================================================================= -->

<!-- ======================== LinkingAttributes Entities =================== -->
<!ENTITY % SMIL.linking-attrs "
	sourceLevel             CDATA               '100&#37;'
	destinationLevel        CDATA               '100&#37;'
	sourcePlaystate         (play|pause|stop)   #IMPLIED
	destinationPlaystate    (play|pause)        'play'
	show                    (new|pause|replace) 'replace'
	accesskey               %Character.datatype; #IMPLIED
	target                  CDATA                #IMPLIED
	external                (true|false)        'false'
	actuate                 (onRequest|onLoad)  'onRequest'
	%SMIL.tabindex.attrib;
">



<!-- ========================= BasicLinking Elements ======================= -->
<!ENTITY % SMIL.BasicLinking.module "IGNORE">
<![%SMIL.BasicLinking.module;[

  <!-- ======================= BasicLinking Entities ======================= -->
  <!ENTITY % SMIL.Shape "(rect|circle|poly|default)">
  <!ENTITY % SMIL.Coords "CDATA">
    <!-- comma separated list of lengths -->

  <!ENTITY % SMIL.a.attrib  "">
  <!ENTITY % SMIL.a.content "EMPTY">
  <!ENTITY % SMIL.a.qname   "a">
  <!ELEMENT %SMIL.a.qname; %SMIL.a.content;>
  <!ATTLIST %SMIL.a.qname; %SMIL.a.attrib;
    %SMIL.linking-attrs;
    href                      %URI.datatype;      #REQUIRED
    %Core.attrib;
    %I18n.attrib;
  >

  <!ENTITY % SMIL.area.attrib  "">
  <!ENTITY % SMIL.area.content "EMPTY">
  <!ENTITY % SMIL.area.qname   "area">
  <!ELEMENT %SMIL.area.qname; %SMIL.area.content;>
  <!ATTLIST %SMIL.area.qname; %SMIL.area.attrib;
    %SMIL.linking-attrs;
    shape                     %SMIL.Shape;             'rect'
    coords                    %SMIL.Coords;            #IMPLIED
    href                      %URI.datatype;      #IMPLIED
    nohref                    (nohref)            #IMPLIED
    %Core.attrib;
    %I18n.attrib;
  >

  <!ENTITY % SMIL.anchor.attrib  "">
  <!ENTITY % SMIL.anchor.content "EMPTY">
  <!ENTITY % SMIL.anchor.qname  "anchor">
  <!ELEMENT %SMIL.anchor.qname; %SMIL.anchor.content;>
  <!ATTLIST %SMIL.anchor.qname; %SMIL.anchor.attrib;
    %SMIL.linking-attrs;
    shape                     %SMIL.Shape;             'rect'
    coords                    %SMIL.Coords;            #IMPLIED
    href                      %URI.datatype;               #IMPLIED
    nohref                    (nohref)            #IMPLIED
    %Core.attrib;
    %I18n.attrib;
  >
]]> <!-- end of BasicLinking -->

<!-- ======================== ObjectLinking ================================ -->
<!ENTITY % SMIL.ObjectLinking.module "IGNORE">
<![%SMIL.ObjectLinking.module;[

  <!ENTITY % SMIL.Fragment "
    fragment                  CDATA               #IMPLIED
  ">

  <!-- ====================== ObjectLinking Elements ======================= -->
  <!-- add fragment attribute to area, and anchor elements -->
  <!ATTLIST %SMIL.area.qname;
      %SMIL.Fragment;
  >

  <!ATTLIST %SMIL.anchor.qname;
      %SMIL.Fragment;
  >
]]>
<!-- ======================== End ObjectLinking ============================ -->

<!-- end of SMIL-link.mod -->

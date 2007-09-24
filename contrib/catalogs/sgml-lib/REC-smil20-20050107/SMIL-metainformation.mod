<!-- ================================================================ -->
<!-- SMIL Metainformation Module  =================================== -->
<!-- file: SMIL-metainformation.mod

     This is SMIL 2.0.

    	Copyright: 1998-2004 W3C (MIT, ERCIM, Keio), All Rights Reserved.
    	See http://www.w3.org/Consortium/Legal/.

	Author: Thierry Michel, Jacco van Ossenbruggen
     Revision:   2004/06/03  Thierry Michel

     The revision includes update of the E09 Errata 
     see (http://www.w3.org/2001/07/REC-SMIL20-20010731-errata#E09)

     This module declares the meta and metadata elements types and 
     its attributes, used to provide declarative document metainformation.
   
     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

     PUBLIC "-//W3C//ELEMENTS SMIL 2.0 Document Metadata//EN"
     SYSTEM "http://www.w3.org/2001/SMIL20/SMIL-metainformation.mod"

     ================================================================ -->


<!-- ================== Profiling Entities ========================== -->

<!ENTITY % SMIL.meta.content     "EMPTY">
<!ENTITY % SMIL.meta.attrib      "">
<!ENTITY % SMIL.meta.qname       "meta">

<!ENTITY % SMIL.metadata.content "EMPTY">
<!ENTITY % SMIL.metadata.attrib  "">
<!ENTITY % SMIL.metadata.qname   "metadata">

<!-- ================== meta element ================================ -->

<!ELEMENT %SMIL.meta.qname; %SMIL.meta.content;>
<!ATTLIST %SMIL.meta.qname; %SMIL.meta.attrib;
  %Core.attrib;
  %I18n.attrib;
  content CDATA #REQUIRED
  name CDATA #REQUIRED        
  >

<!-- ================== metadata element ============================ -->

<!ELEMENT %SMIL.metadata.qname; %SMIL.metadata.content;>
<!ATTLIST %SMIL.metadata.qname; %SMIL.metadata.attrib;
  %Core.attrib;
  %I18n.attrib;
>

<!-- end of SMIL-metadata.mod -->

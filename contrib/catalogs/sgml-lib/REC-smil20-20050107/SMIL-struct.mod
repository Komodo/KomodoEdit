<!-- ====================================================================== -->
<!-- SMIL Structure Module  =============================================== -->
<!-- file: SMIL-struct.mod

     This is SMIL 2.0.

    	Copyright: 1998-2004 W3C (MIT, ERCIM, Keio), All Rights Reserved.
    	See http://www.w3.org/Consortium/Legal/.

	Author: Warner ten Kate, Jacco van Ossenbruggen
        Revision:   2001/07/31  Thierry Michel

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

     PUBLIC "-//W3C//ELEMENTS SMIL 2.0 Document Structure//EN"
     SYSTEM "http://www.w3.org/2001/SMIL20/SMIL-struct.mod"

     ===================================================================== -->

<!-- ================== SMIL Document Root =============================== -->
<!ENTITY % SMIL.smil.attrib  "" >
<!ENTITY % SMIL.smil.content "EMPTY" >
<!ENTITY % SMIL.smil.qname   "smil" >

<!ELEMENT %SMIL.smil.qname; %SMIL.smil.content;>
<!ATTLIST %SMIL.smil.qname; %SMIL.smil.attrib;
        %Core.attrib;
        %I18n.attrib;
        xmlns %URI.datatype; #REQUIRED 
>

<!-- ================== The Document Head ================================ -->
<!ENTITY % SMIL.head.content "EMPTY" >
<!ENTITY % SMIL.head.attrib  "" >
<!ENTITY % SMIL.head.qname   "head" >

<!ELEMENT %SMIL.head.qname; %SMIL.head.content;>
<!ATTLIST %SMIL.head.qname; %SMIL.head.attrib;
        %Core.attrib;
        %I18n.attrib;
>

<!--=================== The Document Body - Timing Root ================== -->
<!ENTITY % SMIL.body.content "EMPTY" >
<!ENTITY % SMIL.body.attrib  "" >
<!ENTITY % SMIL.body.qname   "body" >

<!ELEMENT %SMIL.body.qname; %SMIL.body.content;>
<!ATTLIST %SMIL.body.qname; %SMIL.body.attrib;
        %Core.attrib;
        %I18n.attrib;
>
<!-- end of SMIL-struct.mod -->

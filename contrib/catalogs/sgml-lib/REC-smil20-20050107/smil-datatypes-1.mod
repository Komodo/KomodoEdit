<!-- ...................................................................... -->
<!-- SMIL 2.0 Datatypes Module  ........................................... -->
<!-- file: smil-datatypes-1.mod

     This is SMIL 2.0.

    	Copyright: 1998-2001 W3C (MIT, INRIA, Keio), All Rights Reserved.
    	See http://www.w3.org/Consortium/Legal/.

	    Author:     Jacco van Ossenbruggen
         Revision:   2004/08/02  by Thierry Michel

     The revision includes update of 52 Errata: 
     see (http://www.w3.org/2001/07/REC-SMIL20-20010731-errata#E52)   

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

     PUBLIC "-//W3C//ENTITIES SMIL 2.0 Datatypes 1.0//EN"
     SYSTEM "http://www.w3.org/2001/SMIL20/smil-datatypes-1.mod"

     ....................................................................... -->

<!-- Datatypes

     defines containers for the following datatypes, many of
     these imported from other specifications and standards.
-->

<!ENTITY % Character.datatype "CDATA">
    <!-- a single character from [ISO10646] -->
<!ENTITY % ContentType.datatype "CDATA">
    <!-- media type, as per [RFC2045] -->
<!ENTITY % LanguageCode.datatype "CDATA">
    <!-- a language code, as per [RFC3066] -->
<!ENTITY % LanguageCodes.datatype "CDATA">
    <!-- comma-separated list of language codes, as per [RFC1766] -->
<!ENTITY % Number.datatype "CDATA">
    <!-- one or more digits -->
<!ENTITY % Script.datatype "CDATA">
    <!-- script expression -->
<!ENTITY % Text.datatype "CDATA">
    <!-- used for titles etc. -->
<!ENTITY % TimeValue.datatype "CDATA">
    <!-- a Number, possibly with its dimension, or a reserved 
         word like 'indefinite' -->
<!ENTITY % URI.datatype "CDATA" >
    <!-- used for URI references -->

<!-- end of smil-datatypes-1.mod -->

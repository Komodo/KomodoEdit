<!-- ....................................................................... -->
<!-- SMIL Qualified Names Module  .......................................... -->
<!-- file: smil-qname-1.mod

     This is SMIL 2.0.

    	Copyright: 1998-2004 W3C (MIT, ERCIM, Keio), All Rights Reserved.
    	See http://www.w3.org/Consortium/Legal/.
	
        Revision:   2001/07/31  Thierry Michel  

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

       PUBLIC "-//W3C//ENTITIES SMIL Qualified Names 1.0//EN"
       SYSTEM "http://www.w3.org/2001/SMIL20/smil-qname-1.mod"

     ....................................................................... -->

<!-- SMIL Qualified Names

     This module is contained in two parts, labeled Section 'A' and 'B':

       Section A declares parameter entities to support namespace-
       qualified names, namespace declarations, and name prefixing 
       for SMIL and extensions.
    
       Section B declares parameter entities used to provide
       namespace-qualified names for all SMIL element types:

         %animation.qname; the xmlns-qualified name for <animation>
         %video.qname;     the xmlns-qualified name for <video>
         ...

     SMIL extensions would create a module similar to this one, 
     using the '%smil-qname-extra.mod;' parameter entity to insert 
     it within Section A.  A template module suitable for this purpose 
     ('template-qname-1.mod') is included in the XHTML distribution.
-->

<!-- Section A: SMIL XML Namespace Framework :::::::::::::::::::: -->

<!-- 1. Declare the two parameter entities used to support XLink,
        first the parameter entity container for the URI used to
        identify the XLink namespace:
-->
<!ENTITY % XLINK.xmlns "http://www.w3.org/1999/xlink" >

<!-- This contains the XLink namespace declaration attribute.
-->
<!ENTITY % XLINK.xmlns.attrib
     "xmlns:xlink  %URI.datatype;           #FIXED '%XLINK.xmlns;'"
>

<!-- 2. Declare parameter entities (e.g., %SMIL.xmlns;) containing 
        the namespace URI for the SMIL namespace, and any namespaces
        included by SMIL:
-->

<!ENTITY % SMIL.xmlns  "http://www.w3.org/2001/SMIL20/" >

<!-- 3. Declare parameter entities (e.g., %SMIL.prefix;) containing
        the default namespace prefix string(s) to use when prefixing 
        is enabled. This may be overridden in the DTD driver or the
        internal subset of a document instance.

     NOTE: As specified in [XMLNAMES], the namespace prefix serves 
     as a proxy for the URI reference, and is not in itself significant.
-->
<!ENTITY % SMIL.prefix  "" >

<!-- 4. Declare a %SMIL.prefixed; conditional section keyword, used
        to activate namespace prefixing. The default value should 
        inherit '%NS.prefixed;' from the DTD driver, so that unless 
        overridden, the default behaviour follows the overall DTD 
        prefixing scheme.
-->
<!ENTITY % NS.prefixed "IGNORE" >
<!ENTITY % SMIL.prefixed "%NS.prefixed;" >

<!-- 5. Declare parameter entities (e.g., %SMIL.pfx;) containing the 
        colonized prefix(es) (e.g., '%SMIL.prefix;:') used when 
        prefixing is active, an empty string when it is not.
-->
<![%SMIL.prefixed;[
<!ENTITY % SMIL.pfx  "%SMIL.prefix;:" >
<!ENTITY % SMIL.xmlns.extra.attrib
	"xmlns:%SMIL.prefix;	%URI.datatype;	#FIXED	'%SMIL.xmlns;'" >

]]>
<!ENTITY % SMIL.pfx  "" >
<!ENTITY % SMIL.xmlns.extra.attrib "" >


<!-- declare qualified name extensions here -->
<!ENTITY % smil-qname-extra.mod "" >
%smil-qname-extra.mod;

<!-- 6. The parameter entity %SMIL.xmlns.extra.attrib; may be
        redeclared to contain any non-SMIL namespace declaration 
        attributes for namespaces embedded in SMIL. The default 
        is an empty string.  XLink should be included here if used 
        in the DTD and not already included by a previously-declared 
        %*.xmlns.extra.attrib;.
-->

<!-- 7. The parameter entity %NS.prefixed.attrib; is defined to be
        the prefix for SMIL elements if any and whatever is in
		SMIL.xmlns.extra.attrib.
-->
<!ENTITY % XHTML.xmlns.extra.attrib "%SMIL.xmlns.extra.attrib;" >


<!-- Section B: SMIL Qualified Names ::::::::::::::::::::::::::::: -->

<!-- This section declares parameter entities used to provide
     namespace-qualified names for all SMIL element types.
-->

<!ENTITY % SMIL.animate.qname "%SMIL.pfx;animate" >
<!ENTITY % SMIL.set.qname "%SMIL.pfx;set" >
<!ENTITY % SMIL.animateMotion.qname "%SMIL.pfx;animateMotion" >
<!ENTITY % SMIL.animateColor.qname "%SMIL.pfx;animateColor" >

<!ENTITY % SMIL.switch.qname "%SMIL.pfx;switch" >
<!ENTITY % SMIL.customTest.qname "%SMIL.pfx;customTest" >
<!ENTITY % SMIL.customAttributes.qname "%SMIL.pfx;customAttributes" >
<!ENTITY % SMIL.prefetch.qname "%SMIL.pfx;prefetch" >

<!ENTITY % SMIL.layout.qname "%SMIL.pfx;layout" >
<!ENTITY % SMIL.region.qname "%SMIL.pfx;region" >
<!ENTITY % SMIL.root-layout.qname "%SMIL.pfx;root-layout" >
<!ENTITY % SMIL.topLayout.qname "%SMIL.pfx;topLayout" >
<!ENTITY % SMIL.regPoint.qname "%SMIL.pfx;regPoint" >

<!ENTITY % SMIL.a.qname "%SMIL.pfx;a" >
<!ENTITY % SMIL.area.qname "%SMIL.pfx;area" >
<!ENTITY % SMIL.anchor.qname "%SMIL.pfx;anchor" >

<!ENTITY % SMIL.ref.qname "%SMIL.pfx;ref" >
<!ENTITY % SMIL.audio.qname "%SMIL.pfx;audio" >
<!ENTITY % SMIL.img.qname "%SMIL.pfx;img" >
<!ENTITY % SMIL.video.qname "%SMIL.pfx;video" >
<!ENTITY % SMIL.text.qname "%SMIL.pfx;text" >
<!ENTITY % SMIL.textstream.qname "%SMIL.pfx;textstream" >
<!ENTITY % SMIL.animation.qname "%SMIL.pfx;animation" >
<!ENTITY % SMIL.param.qname "%SMIL.pfx;param" >
<!ENTITY % SMIL.brush.qname "%SMIL.pfx;brush" >

<!ENTITY % SMIL.meta.qname "%SMIL.pfx;meta" >
<!ENTITY % SMIL.metadata.qname "%SMIL.pfx;metadata" >

<!ENTITY % SMIL.smil.qname "%SMIL.pfx;smil" >
<!ENTITY % SMIL.head.qname "%SMIL.pfx;head" >
<!ENTITY % SMIL.body.qname "%SMIL.pfx;body" >

<!ENTITY % SMIL.seq.qname "%SMIL.pfx;seq" >
<!ENTITY % SMIL.par.qname "%SMIL.pfx;par" >
<!ENTITY % SMIL.excl.qname "%SMIL.pfx;excl" >
<!ENTITY % SMIL.priorityClass.qname   "%SMIL.pfx;priorityClass">

<!ENTITY % SMIL.transition.qname "%SMIL.pfx;transition" >
<!ENTITY % SMIL.transitionFilter.qname "%SMIL.pfx;transitionFilter" >

<!-- end of smil-qname-1.mod -->

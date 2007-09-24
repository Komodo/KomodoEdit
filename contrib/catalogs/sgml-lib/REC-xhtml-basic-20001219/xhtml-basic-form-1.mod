<!-- ...................................................................... -->
<!-- XHTML Simplified Forms Module  ....................................... -->
<!-- file: xhtml-basic-form-1.mod

     This is XHTML Basic, a proper subset of XHTML.
     Copyright 1998-2000 W3C (MIT, INRIA, Keio), All Rights Reserved.
     Revision: xhtml-basic-form-1.mod,v 1.1 2001/05/10 08:41:58 gerald Exp SMI

     This DTD module is identified by the PUBLIC and SYSTEM identifiers:

       PUBLIC "-//W3C//ELEMENTS XHTML Basic Forms 1.0//EN"  
       SYSTEM "http://www.w3.org/TR/xhtml-modulatization/DTD/xhtml-basic-form-1.mod"

     Revisions:
     (none)
     ....................................................................... -->

<!-- Basic Forms

     This forms module is based on the HTML 3.2 forms model, with
     the WAI-requested addition of the label element. While this 
     module essentially mimics the content model and attributes of 
     HTML 3.2 forms, the element types declared herein also include
     all HTML 4 common attributes.

        form, label, input, select, option, textarea
-->

<!-- declare qualified element type names:
-->
<!ENTITY % form.qname  "form" >
<!ENTITY % label.qname  "label" >
<!ENTITY % input.qname  "input" >
<!ENTITY % select.qname  "select" >
<!ENTITY % option.qname  "option" >
<!ENTITY % textarea.qname  "textarea" >

<!-- %BlkNoForm.mix; includes all non-form block elements,
     plus %Misc.class;
-->
<!ENTITY % BlkNoForm.mix
     "%Heading.class;
      | %List.class;
      | %BlkStruct.class;
      %BlkPhras.class;
      %BlkPres.class;
      | %table.qname; 
      %Block.extra;
      %Misc.class;"
>

<!-- form: Form Element ................................ -->

<!ENTITY % form.element  "INCLUDE" >
<![%form.element;[
<!ENTITY % form.content
     "( %BlkNoForm.mix; )+"
>
<!ELEMENT %form.qname;  %form.content; >
<!-- end of form.element -->]]>

<!ENTITY % form.attlist  "INCLUDE" >
<![%form.attlist;[
<!ATTLIST %form.qname;
      %Common.attrib;
      action       %URI.datatype;           #REQUIRED
      method       ( get | post )           'get'
      enctype      %ContentType.datatype;   'application/x-www-form-urlencoded'
>
<!-- end of form.attlist -->]]>

<!-- label: Form Field Label Text ...................... -->

<!ENTITY % label.element  "INCLUDE" >
<![%label.element;[
<!-- Each label must not contain more than ONE field
-->
<!ENTITY % label.content
     "( #PCDATA 
      | %input.qname; | %select.qname; | %textarea.qname;
      | %InlStruct.class;
      %InlPhras.class;
      %I18n.class;
      %InlPres.class;
      %InlSpecial.class;
      %Misc.class; )*"
>
<!ELEMENT %label.qname;  %label.content; >
<!-- end of label.element -->]]>

<!ENTITY % label.attlist  "INCLUDE" >
<![%label.attlist;[
<!ATTLIST %label.qname;
      %Common.attrib;
      for          IDREF                    #IMPLIED
      accesskey    %Character.datatype;     #IMPLIED
>
<!-- end of label.attlist -->]]>

<!-- input: Form Control ............................... -->

<!ENTITY % input.element  "INCLUDE" >
<![%input.element;[
<!ENTITY % input.content  "EMPTY" >
<!ELEMENT %input.qname;  %input.content; >
<!-- end of input.element -->]]>

<!-- Basic Forms removes 'image' and 'file' input types.
-->
<!ENTITY % input.attlist  "INCLUDE" >
<![%input.attlist;[
<!ENTITY % InputType.class
     "( text | password | checkbox | radio 
      | submit | reset | hidden )"
>
<!-- attribute name required for all but submit & reset
-->
<!ATTLIST %input.qname;
      %Common.attrib;
      type         %InputType.class;        'text'
      name         CDATA                    #IMPLIED
      value        CDATA                    #IMPLIED
      checked      ( checked )              #IMPLIED
      size         CDATA                    #IMPLIED
      maxlength    %Number.datatype;        #IMPLIED
      src          %URI.datatype;           #IMPLIED
      accesskey    %Character.datatype;     #IMPLIED
>
<!-- end of input.attlist -->]]>

<!-- select: Option Selector ........................... -->

<!ENTITY % select.element  "INCLUDE" >
<![%select.element;[
<!ENTITY % select.content  "( %option.qname; )+" >
<!ELEMENT %select.qname;  %select.content; >
<!-- end of select.element -->]]>

<!ENTITY % select.attlist  "INCLUDE" >
<![%select.attlist;[
<!ATTLIST %select.qname;
      %Common.attrib;
      name         CDATA                    #IMPLIED
      size         %Number.datatype;        #IMPLIED
      multiple     ( multiple )             #IMPLIED
>
<!-- end of select.attlist -->]]>

<!-- option: Selectable Choice ......................... -->

<!ENTITY % option.element  "INCLUDE" >
<![%option.element;[
<!ENTITY % option.content  "( #PCDATA )" >
<!ELEMENT %option.qname;  %option.content; >
<!-- end of option.element -->]]>

<!ENTITY % option.attlist  "INCLUDE" >
<![%option.attlist;[
<!ATTLIST %option.qname;
      %Common.attrib;
      selected     ( selected )             #IMPLIED
      value        CDATA                    #IMPLIED
>
<!-- end of option.attlist -->]]>

<!-- textarea: Multi-Line Text Field ................... -->

<!ENTITY % textarea.element  "INCLUDE" >
<![%textarea.element;[
<!ENTITY % textarea.content  "( #PCDATA )" >
<!ELEMENT %textarea.qname;  %textarea.content; >
<!-- end of textarea.element -->]]>

<!ENTITY % textarea.attlist  "INCLUDE" >
<![%textarea.attlist;[
<!ATTLIST %textarea.qname;
      %Common.attrib;
      name         CDATA                    #IMPLIED
      rows         %Number.datatype;        #REQUIRED
      cols         %Number.datatype;        #REQUIRED
      accesskey    %Character.datatype;     #IMPLIED
>
<!-- end of textarea.attlist -->]]>

<!-- end of xhtml-basic-form-1.mod -->

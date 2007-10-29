<?xml version="1.0" encoding="UTF-8"?>

<!-- ***** BEGIN LICENSE BLOCK *****
 Version: MPL 1.1/GPL 2.0/LGPL 2.1
 
 The contents of this file are subject to the Mozilla Public License
 Version 1.1 (the "License"); you may not use this file except in
 compliance with the License. You may obtain a copy of the License at
 http://www.mozilla.org/MPL/
 
 Software distributed under the License is distributed on an "AS IS"
 basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 License for the specific language governing rights and limitations
 under the License.
 
 The Original Code is Komodo code.
 
 The Initial Developer of the Original Code is ActiveState Software Inc.
 Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
 ActiveState Software Inc. All Rights Reserved.
 
 Contributor(s):
   ActiveState Software Inc
 
 Alternatively, the contents of this file may be used under the terms of
 either the GNU General Public License Version 2 or later (the "GPL"), or
 the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 in which case the provisions of the GPL or the LGPL are applicable instead
 of those above. If you wish to allow use of your version of this file only
 under the terms of either the GPL or the LGPL, and not to allow others to
 use your version of this file under the terms of the MPL, indicate your
 decision by deleting the provisions above and replace them with the notice
 and other provisions required by the GPL or the LGPL. If you do not delete
 the provisions above, a recipient may use your version of this file under
 the terms of any one of the MPL, the GPL or the LGPL.
 
 ***** END LICENSE BLOCK ***** -->

<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
    <xsl:output indent="yes" method="xml"/>

    <!--<xsl:variable name="func_signature"/>-->

    <!-- Setup the basic codeintel skeleton -->
    <xsl:template match="/">
        <codeintel version="0.1">
            <file generator="StdCIX" language="JavaScript" md5="*" mtime="1102379523" path="javascript.cix">
                <xsl:apply-templates/>
            </file>
        </codeintel>
    </xsl:template>

    <!-- Process the group --> 
    <xsl:template match="group">
        <xsl:choose>
            <xsl:when test="@name='Global'">
                <module name="*">
                    <xsl:apply-templates select="element"/>
                </module>
            </xsl:when>
            <xsl:when test="@name='Infinity'">
                <!--Ignore this field-->
            </xsl:when>
            <xsl:when test="@name='NaN'">
                <!--Ignore this field-->
            </xsl:when>
            <xsl:when test="@name='undefined'">
                <!--Ignore this field-->
            </xsl:when>
            <xsl:otherwise>
                <module>
                    <xsl:attribute name="name">
                        <xsl:value-of select="@name"/>
                    </xsl:attribute>
                    <xsl:apply-templates select="element"/>
                </module>
            </xsl:otherwise>
        </xsl:choose>

    </xsl:template>

    <!-- Process the element. -->
    <!-- <element kind="function" name="Global_eval()"> -->
    <xsl:template match="element">
        <xsl:choose>
            <xsl:when test="@kind='var'">
                <variable>
                    <xsl:attribute name="name">
                        <xsl:value-of select="substring(substring-after(@name,../@name), 2)"/>
                    </xsl:attribute>
                    <!--<xsl:apply-templates select="note"/>-->
                </variable>
            </xsl:when>
            <xsl:when test="@kind='function'">
                <function>
                    <xsl:attribute name="name">
                        <xsl:value-of select="substring(substring-after(@name,../@name), 2)"/>
                    </xsl:attribute>
                    <xsl:apply-templates select="note"/>
                    <xsl:apply-templates select="properties"/>
                </function>
            </xsl:when>
        </xsl:choose>
    </xsl:template>

    <!-- Add doc tag -->
    <!-- <note title="overview">Evaluate the supplied string as ECMAScript code.</note> -->
    <xsl:template match="note">
        <doc>
            <xsl:value-of select="."/>
        </doc>
    </xsl:template>

    <!-- Add argument tags for functions -->
    <xsl:template match="properties">
        <xsl:apply-templates select="property"/>
    </xsl:template>

    <!-- Add argument tags for functions -->
    <xsl:template match="property">
        <xsl:if test="@kind='parameter'">
            <argument>
                <xsl:attribute name="name">
                    <xsl:value-of select="@name"/>
                </xsl:attribute>
                <xsl:apply-templates select="description"/>
            </argument>
        </xsl:if>
    </xsl:template>

    <!-- Add argument types -->
    <!-- Example: <description>String The string to evaluate.</description> -->
    <xsl:template match="description">
        <type score="1">
            <xsl:attribute name="type">
                <!-- Just grab the first word -->
                <xsl:value-of select="substring-before(., ' ')"/>
            </xsl:attribute>
        </type>
    </xsl:template>

</xsl:stylesheet>

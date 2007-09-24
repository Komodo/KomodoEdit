<?xml version="1.0" encoding="UTF-8"?>
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

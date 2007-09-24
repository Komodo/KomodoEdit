<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
    <xsl:output indent="yes" method="xml"/>

    <xsl:variable name="func_signature"/>

    <!-- Setup the basic codeintel skeleton -->
    <xsl:template match="/">
        <codeintel version="2.0">
            <file lang="JavaScript" mtime="1102379523" path="javascript.cix">
                <scope ilk="blob" lang="JavaScript" name="*">
                    <xsl:apply-templates/>
                </scope>
            </file>
        </codeintel>
    </xsl:template>

    <!-- Process the group --> 
    <xsl:template match="group">
        <xsl:choose>
            <xsl:when test="@name='Global'">
                <xsl:apply-templates select="element"/>
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
                <scope ilk="class">
                    <xsl:attribute name="name">
                        <xsl:value-of select="@name"/>
                    </xsl:attribute>
                    <xsl:apply-templates select="element"/>
                </scope>
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
                <scope ilk="function">
                    <xsl:attribute name="name">
                        <xsl:value-of select="substring(substring-after(@name,../@name), 2)"/>
                    </xsl:attribute>
                    <xsl:apply-templates select="note"/>
                    <xsl:apply-templates select="properties"/>
                </scope>
            </xsl:when>
        </xsl:choose>
    </xsl:template>

    <!-- Add doc tag -->
    <!-- <note title="overview">Evaluate the supplied string as ECMAScript code.</note> -->
    <xsl:template match="note">
        <xsl:attribute name="doc">
            <xsl:value-of select="."/>
        </xsl:attribute>
    </xsl:template>

    <!-- Add argument tags for functions -->
    <xsl:template match="properties">
        <xsl:apply-templates select="property"/>
    </xsl:template>

    <!-- Add argument tags for functions -->
    <xsl:template match="property">
        <xsl:if test="@kind='parameter'">
            <variable ilk="argument">
                <xsl:attribute name="name">
                    <xsl:value-of select="@name"/>
                </xsl:attribute>
                <xsl:apply-templates select="description"/>
            </variable>
        </xsl:if>
    </xsl:template>

    <!-- Add argument types -->
    <!-- Example: <description>String The string to evaluate.</description> -->
    <xsl:template match="description">
        <xsl:attribute name="citdl">
            <!-- Just grab the first word -->
            <xsl:value-of select="substring-before(., ' ')"/>
        </xsl:attribute>
    </xsl:template>

</xsl:stylesheet>

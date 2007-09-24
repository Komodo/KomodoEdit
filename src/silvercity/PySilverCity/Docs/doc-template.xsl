<xsl:stylesheet 
	version="1.0"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform">	

<xsl:template match="subsection/title" mode="title"><a href="#{generate-id()}"><xsl:value-of select="."/></a>
</xsl:template>

<xsl:template match="subsection" mode="index">
	<li><xsl:apply-templates select="title" mode="title"/></li>
	<ul><xsl:apply-templates select="child::subsection" mode="index"/></ul>
</xsl:template>

<xsl:template match="br">
    <br/>
</xsl:template>

<xsl:template match="/">
	<html>
		<head>
                <!-- XXX hard coded title -->
			<title>SilverCity</title>
			<link rel="STYLESHEET" href="http://www.python.org/doc/current/lib/lib.css"/>
		</head>
		<body>
			<xsl:apply-templates/>
		</body>
	</html>
</xsl:template>

<xsl:template match="declarepackage"/>

<xsl:template match="xxx">
	XXX - <em><xsl:apply-templates/></em>
</xsl:template>

<xsl:template match="contents">
	<strong>Subsections</strong>
	<ul><xsl:apply-templates select="//subsection" mode="index"/></ul>
</xsl:template>

<xsl:template match="heading">
	<h1><xsl:apply-templates/></h1>
</xsl:template>

<xsl:template match="var">
	<var><xsl:apply-templates/></var>
</xsl:template>

<xsl:template match="example">
	<dl>
		<dd><dt/><pre class="verbatim"><xsl:apply-templates/></pre></dd>
	</dl>
</xsl:template>

<xsl:template match="module|package|function|exception|class|code">
	<tt><xsl:apply-templates/></tt>
</xsl:template>

<xsl:template match="p">
	<p><xsl:apply-templates/></p>
</xsl:template>

<xsl:template match="see">
	<dl compact="true" class="seetitle">
		<dt>
		<em class="citetitle">
		<a>
			<xsl:attribute name="href"><xsl:value-of select="ref/attribute::href"/></xsl:attribute>
			<xsl:value-of select="title"/>
		</a>
		</em>
		</dt>
		<dd>
			<xsl:apply-templates select="description"/>
		</dd>
	</dl>
</xsl:template>

<xsl:template match="seealso">
	<div class="seealso">
		<p class="heading"><b>See Also:</b></p>
		<xsl:apply-templates select="see"/>
	</div>
</xsl:template>

<xsl:template match="funcdesc|methoddesc">
	<dl>
		<dt>
			<b><a name=""><tt class="function"><xsl:value-of select="name"/></tt></a></b>
			<xsl:apply-templates select="arguments"/>
		</dt>
		<dd><xsl:apply-templates select="description"/></dd>
	</dl>
</xsl:template>

<xsl:template match="classconstructor">
	<dl>
		<dt>
			<b><a name=""><span class="typelabel">class </span><tt class="class"><xsl:value-of select="name"/></tt></a></b>
			<xsl:apply-templates select="arguments"/>
		</dt>
		<dd><xsl:apply-templates select="description"/></dd>
	</dl>
</xsl:template>

<xsl:template match="arguments">
	(<xsl:for-each select="argument">
		<xsl:if test="attribute::default='yes'"><big>[</big></xsl:if>
		<xsl:if test="position() > 1">, </xsl:if>
		<var><xsl:apply-templates/></var>
		<xsl:if test="count(attribute::default)"><big>]</big></xsl:if>
	</xsl:for-each>)
</xsl:template>

<xsl:template match="table">
	<table border="yes" align="center" style="border-collapse: collapse">
		<xsl:apply-templates/>
	</table>
</xsl:template>

<xsl:template match="subsection/title">
	<a name="{generate-id()}"><h2><xsl:apply-templates/></h2></a>
</xsl:template>

<xsl:template match="tr">
	<tr><xsl:apply-templates/></tr>
</xsl:template>

<xsl:template match="thead">
	<thead><tr class="tableheader"><xsl:apply-templates/></tr></thead>
</xsl:template>

<xsl:template match="tbody">
	<tbody valign="baseline"><xsl:apply-templates/></tbody>
</xsl:template>

<xsl:template match="th">
	<th align="left"><b><xsl:apply-templates/></b></th>
</xsl:template>

<xsl:template match="td">
	<td align="left" valign="baseline"><xsl:apply-templates/></td>
</xsl:template>
</xsl:stylesheet>
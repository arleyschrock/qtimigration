#! /usr/bin/env python
"""This module implements the QTI 2.1 specification defined by IMS GLC
"""

import pyslet.xml20081126 as xml
import pyslet.xmlnames20091208 as xmlns
import pyslet.xsdatatypes20041028 as xsdatatypes
import pyslet.html40_19991224 as html

xsi=xsdatatypes

import string
import os.path, urllib, urlparse
from types import StringTypes

IMSQTI_NAMESPACE="http://www.imsglobal.org/xsd/imsqti_v2p1"
IMSQTI_SCHEMALOCATION="http://www.imsglobal.org/xsd/imsqti_v2p1.xsd"
IMSQTI_ITEM_RESOURCETYPE="imsqti_item_xmlv2p1"


class QTIError(Exception): pass
class QTIDeclarationError(QTIError): pass
class QTIValidityError(QTIError): pass

QTI_HTMLProfile=[
	'abbr','acronym','address','blockquote','br','cite','code','dfn','div',
	'em','h1','h2','h3','h4','h5','h6','kbd','p','pre','q','samp','span',
	'strong','var','dl','dt','dd','ol','ul','li','object','param','b','big',
	'hr','i','small','sub','sup','tt','caption','col','colgroup','table',
	'tbody','tfoot','thead','td','th','tr','img','a']

def FixHTMLNamespace(e):
	"""Fixes e and all children to be in the QTINamespace"""
	if e.ns==html.XHTML_NAMESPACE:
		name=(IMSQTI_NAMESPACE,e.xmlname.lower())
		if QTIDocument.classMap.has_key(name):
			e.SetXMLName(name)
	children=e.GetChildren()
	for e in children:
		if type(e) in StringTypes:
			continue
		FixHTMLNamespace(e)


#
# Definitions for basic types
#
class QTIBaseType:
	"""baseType enumeration.
	
	<xsd:simpleType name="baseType.Type">
		<xsd:restriction base="xsd:NMTOKEN">
			<xsd:enumeration value="boolean"/>
			<xsd:enumeration value="directedPair"/>
			<xsd:enumeration value="duration"/>
			<xsd:enumeration value="file"/>
			<xsd:enumeration value="float"/>
			<xsd:enumeration value="identifier"/>
			<xsd:enumeration value="integer"/>
			<xsd:enumeration value="pair"/>
			<xsd:enumeration value="point"/>
			<xsd:enumeration value="string"/>
			<xsd:enumeration value="uri"/>
		</xsd:restriction>
	</xsd:simpleType>"""
	decode={
		'boolean':1,
		'directedPair':2,
		'duration':3,
		'file':4,
		'float':5,
		'identifier':5,
		'integer':6,
		'pair':7,
		'point':8,
		'string':9,
		'uri':10
		}
xsi.MakeEnumeration(QTIBaseType)

def DecodeBaseType(value):
	"""Decodes a baseType value from a string."""
	try:
		return QTIBaseType.decode[value.lower()]
	except KeyError:
		raise ValueError("Can't decode baseType from %s"%value)

def EncodeBaseType(value):
	return QTIBaseType.encode.get(value,'')


class QTICardinality:
	"""Cardinality enumeration.

	<xsd:simpleType name="cardinality.Type">
		<xsd:restriction base="xsd:NMTOKEN">
			<xsd:enumeration value="multiple"/>
			<xsd:enumeration value="ordered"/>
			<xsd:enumeration value="record"/>
			<xsd:enumeration value="single"/>
		</xsd:restriction>
	</xsd:simpleType>"""
	decode={
		'multiple':1,
		'ordered':2,
		'record':3,
		'single':4
		}
xsi.MakeEnumeration(QTICardinality)

def DecodeCardinality(value):
	"""Decodes a cardinality value from a string."""
	try:
		return QTICardinality.decode[value.lower()]
	except KeyError:
		raise ValueError("Can't decode cardinality from %s"%value)

def EncodeCardinality(value):
	return QTICardinality.encode.get(value,'')


def ValidateIdentifier(value):
	"""Decodes an identifier from a string.

	<xsd:simpleType name="identifier.Type">
		<xsd:restriction base="xsd:NCName"/>
	</xsd:simpleType>
	
	This function takes a string that is supposed to match the production for
	NCName in XML and forces to to comply by replacing illegal characters with
	'_', except the ':' which is replaced with a hyphen for compatibility with
	previous versions of the QTI migraiton script.  If name starts with a valid
	name character but not a valid name start character, it is prefixed with '_'
	too."""
	if value:
		goodName=[]
		if not xmlns.IsNameStartChar(value[0]):
			goodName.append('_')
		elif value[0]==':':
			# Previous versions of the migrate script didn't catch this problem
			# as a result, we deviate from its broken behaviour or using '-'
			goodName.append('_')			
		for c in value:
			if c==':':
				goodName.append('-')
			elif xmlns.IsNameChar(c):
				goodName.append(c)
			else:
				goodName.append('_')
		return string.join(goodName,'')
	else:
		return '_'

MakeValidNCName=ValidateIdentifier


class QTIShowHide:
	decode={
		'show':1,
		'hide':2
		}
xsi.MakeEnumeration(QTIShowHide)
		
def DecodeShowHide(value):
	"""Decodes a showHide value from a string.

	<xsd:simpleType name="showHide.Type">
		<xsd:restriction base="xsd:NMTOKEN">
			<xsd:enumeration value="hide"/>
			<xsd:enumeration value="show"/>
		</xsd:restriction>
	</xsd:simpleType>
	"""
	try:
		return QTIShowHide.decode[value.lower()]
	except KeyError:
		raise ValueError("Can't decode show/hide from %s"%value)

def EncodeShowHide(value):
	return QTIShowHide.encode.get(value,'')


class QTIView:
	fixups={
		'testconstructor':'testConstructor'
		}
	decode={
		'author':1,
		'candidate':2,
		'proctor':3,
		'scorer':4,
		'testConstructor':5,
		'tutor':6
		}
xsi.MakeEnumeration(QTIView)

def DecodeView(value):
	try:
		return QTIView.decode[value]
	except KeyError:
		value=value.lower()
		value=QTIView.fixups.get(value,value)
	try:
		return QTIView.decode[value]
	except KeyError:
		raise ValueError("Can't decode view from %s"%value)

def EncodeView(value):
	return QTIView.encode.get(value,'')
		

class QTIElement(xmlns.XMLNSElement):
	"""Basic element to represent all QTI elements""" 
	
	def AddToCPResource(self,cp,resource,baseURI):
		"""Adds any linked files that exist on the local file system to the content package."""
		for child in self.GetChildren():
			if isinstance(child,QTIElement):
				child.AddToCPResource(cp,resource,baseURI)

	def GetAssessmentItem(self):
		iParent=self
		while iParent is not None:
			if isinstance(iParent,QTIAssessmentItem):
				return iParent
			else:
				iParent=iParent.parent


class QTIAssessmentItem(QTIElement):
	"""
	<xsd:attributeGroup name="assessmentItem.AttrGroup">
		<xsd:attribute name="identifier" type="string.Type" use="required"/>
		<xsd:attribute name="title" type="string.Type" use="required"/>
		<xsd:attribute name="label" type="string256.Type" use="optional"/>
		<xsd:attribute ref="xml:lang"/>
		<xsd:attribute name="adaptive" type="boolean.Type" use="required"/>
		<xsd:attribute name="timeDependent" type="boolean.Type" use="required"/>
		<xsd:attribute name="toolName" type="string256.Type" use="optional"/>
		<xsd:attribute name="toolVersion" type="string256.Type" use="optional"/>
	</xsd:attributeGroup>
	
	<xsd:group name="assessmentItem.ContentGroup">
		<xsd:sequence>
			<xsd:element ref="responseDeclaration" minOccurs="0" maxOccurs="unbounded"/>
			<xsd:element ref="outcomeDeclaration" minOccurs="0" maxOccurs="unbounded"/>
			<xsd:element ref="templateDeclaration" minOccurs="0" maxOccurs="unbounded"/>
			<xsd:element ref="templateProcessing" minOccurs="0" maxOccurs="1"/>
			<xsd:element ref="stylesheet" minOccurs="0" maxOccurs="unbounded"/>
			<xsd:element ref="itemBody" minOccurs="0" maxOccurs="1"/>
			<xsd:element ref="responseProcessing" minOccurs="0" maxOccurs="1"/>
			<xsd:element ref="modalFeedback" minOccurs="0" maxOccurs="unbounded"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'assessmentItem')
	XMLATTR_adaptive=('adaptive',xsi.DecodeBoolean,xsi.EncodeBoolean)
	XMLATTR_identifier='identifier'		
	XMLATTR_label='label'
	XMLATTR_timeDependent=('timeDependent',xsi.DecodeBoolean,xsi.EncodeBoolean)
	XMLATTR_title='title'	
	XMLCONTENT=xmlns.XMLElementContent
	
	def __init__(self,parent):
		QTIElement.__init__(self,parent)
		self.metadata=QTIMetadata(None)
		self.identifier=None
		self.title=None
		self.label=None
		self.adaptive=False
		self.timeDependent=False
		self.declarations={}
		self.QTIItemBody=None
				
	def GetChildren(self):
		children=[]
		vars=self.declarations.keys()
		vars.sort()
		for v in vars:
			children.append(self.declarations[v])
		xmlns.OptionalAppend(children,self.QTIItemBody)
		return children+QTIElement.GetChildren(self)
	
	def QTIResponseDeclaration(self):
		# Not linked properly to us until it is finished.
		return QTIResponseDeclaration(self)
	
	def QTIOutcomeDeclaration(self):
		# Not linked properly to us until it is finished.
		return QTIOutcomeDeclaration(self)
		
	def RegisterDeclaration(self,declaration):
		if self.declarations.has_key(declaration.identifier):
			raise QTIDeclarationError
		else:
			self.declarations[declaration.identifier]=declaration
		
	def AddToContentPackage(self,cp,lom,dName=None):
		"""Adds a resource and associated files to the content package."""
		resourceID=cp.manifest.GetUniqueID(self.identifier)
		resource=cp.manifest.root.resources.CPResource()
		resource.SetID(resourceID)
		resource.Set_type(IMSQTI_ITEM_RESOURCETYPE)
		resourceMetadata=resource.CPMetadata()
		resourceMetadata.AdoptChild(lom)
		resourceMetadata.AdoptChild(self.metadata.Copy())
		# Security alert: we're leaning heavily on MakeValidNCName assuming it returns a good file name
		fPath=MakeValidNCName(resourceID).encode('utf-8')+'.xml'
		if dName:
			fPath=os.path.join(dName,fPath)
		fPath=cp.GetUniqueFile(fPath)
		# This will be the path to the file in the package
		fullPath=os.path.join(cp.dPath,fPath)
		uri='file://'+urllib.pathname2url(fullPath)
		# Turn this file path into a relative URL in the context of the new resource
		href=resource.RelativeURI(uri)
		f=cp.CPFile(resource,href)
		resource.SetEntryPoint(f)
		for child in self.GetChildren():
			if isinstance(child,QTIElement):
				child.AddToCPResource(cp,resource,uri)
		return uri
	
		
class QTIVariableDeclaration(QTIElement):
	"""Abstract class for all variable declarations.

	<xsd:attributeGroup name="variableDeclaration.AttrGroup">
		<xsd:attribute name="identifier" type="identifier.Type" use="required"/>
		<xsd:attribute name="cardinality" type="cardinality.Type" use="required"/>
		<xsd:attribute name="baseType" type="baseType.Type" use="optional"/>
	</xsd:attributeGroup>
	
	<xsd:group name="variableDeclaration.ContentGroup">
		<xsd:sequence>
			<xsd:element ref="defaultValue" minOccurs="0" maxOccurs="1"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLATTR_baseType=('baseType',DecodeBaseType,EncodeBaseType)	
	XMLATTR_cardinality=('cardinality',DecodeCardinality,EncodeCardinality)	
	XMLATTR_identifier=('identifier',ValidateIdentifier,lambda x:x)

	def __init__(self,parent):
		QTIElement.__init__(self,parent)
		self.identifier=''
		self.cardinality=0
		self.baseType=None
		self.QTIDefaultValue=None
	
	def GetChildren(self):
		children=[]
		xml.OptionalAppend(children,self.QTIDefaultValue)
		return children+QTIElement.GetChildren(self)


class QTIValue(QTIElement):
	"""Represents the value element.
	
	<xsd:attributeGroup name="value.AttrGroup">
		<xsd:attribute name="fieldIdentifier" type="identifier.Type" use="optional"/>
		<xsd:attribute name="baseType" type="baseType.Type" use="optional"/>
	</xsd:attributeGroup>
	
	<xsd:complexType name="value.Type">
		<xsd:simpleContent>
			<xsd:extension base="xsd:string">
				<xsd:attributeGroup ref="value.AttrGroup"/>
			</xsd:extension>
		</xsd:simpleContent>
	</xsd:complexType>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'value')
	XMLATTR_baseType=('baseType',DecodeBaseType,EncodeBaseType)
	XMLATTR_fieldIdentifier=('fieldIdentifier',ValidateIdentifier,lambda x:x)
	XMLCONTENT=xml.XMLMixedContent
	
	def __init__(self,parent):
		QTIElement.__init__(self,parent)
		self.fieldIdentifier=None
		self.baseType=None


class QTIDefaultValue(QTIElement):
	"""Represents the defaultValue element.
		
	<xsd:attributeGroup name="defaultValue.AttrGroup">
		<xsd:attribute name="interpretation" type="string.Type" use="optional"/>
	</xsd:attributeGroup>
	
	<xsd:group name="defaultValue.ContentGroup">
		<xsd:sequence>
			<xsd:element ref="value" minOccurs="1" maxOccurs="unbounded"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'defaultValue')
	XMLATTR_interpretation='interpretation'
	XMLCONTENT=xml.XMLElementContent
	
	def __init__(self,parent):
		QTIElement.__init__(self,parent)
		self.interpretation=None
		self.QTIValue=[]
	
	def GetChildren(self):
		return self.QTIValue+QTIElement.GetChildren(self)

		
class QTIResponseDeclaration(QTIVariableDeclaration):
	"""Represents a responseDeclaration.
	
	<xsd:group name="responseDeclaration.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="variableDeclaration.ContentGroup"/>
			<xsd:element ref="correctResponse" minOccurs="0" maxOccurs="1"/>
			<xsd:element ref="mapping" minOccurs="0" maxOccurs="1"/>
			<xsd:element ref="areaMapping" minOccurs="0" maxOccurs="1"/>
		</xsd:sequence>
	</xsd:group>"""
	XMLNAME=(IMSQTI_NAMESPACE,'responseDeclaration')
	XMLCONTENT=xml.XMLElementContent
	
	def __init__(self,parent):
		QTIVariableDeclaration.__init__(self,parent)
		self.QTICorrectResponse=None
		self.QTIMapping=None
		self.QTIAreaMapping=None
	
	def GetChildren(self):
		children=QTIVariableDeclaration.GetChildren(self)
		xml.OptionalAppend(children,self.QTICorrectResponse)
		xml.OptionalAppend(children,self.QTIMapping)
		xml.OptionalAppend(children,self.QTIAreaMapping)
		return children
		
	def GotChildren(self):
		self.parent.RegisterDeclaration(self)


class QTIOutcomeDeclaration(QTIVariableDeclaration):
	"""Represents an outcomeDeclaration.

	<xsd:attributeGroup name="outcomeDeclaration.AttrGroup">
		<xsd:attributeGroup ref="variableDeclaration.AttrGroup"/>
		<xsd:attribute name="view" use="optional">
			<xsd:simpleType>
				<xsd:list itemType="view.Type"/>
			</xsd:simpleType>
		</xsd:attribute>
		<xsd:attribute name="interpretation" type="string.Type" use="optional"/>
		<xsd:attribute name="longInterpretation" type="uri.Type" use="optional"/>
		<xsd:attribute name="normalMaximum" type="float.Type" use="optional"/>
		<xsd:attribute name="normalMinimum" type="float.Type" use="optional"/>
		<xsd:attribute name="masteryValue" type="float.Type" use="optional"/>
	</xsd:attributeGroup>
	
	<xsd:group name="outcomeDeclaration.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="variableDeclaration.ContentGroup"/>
			<xsd:group ref="lookupTable.ElementGroup" minOccurs="0" maxOccurs="1"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'outcomeDeclaration')
	XMLATTR_view=('view',DecodeView,EncodeView)
	XMLATTR_interpretation='interpretation'
	XMLATTR_longInterpretation='longInterpretation'
	XMLATTR_normalMaximum=('normalMaximum',xsi.DecodeFloat,xsi.EncodeFloat)
	XMLATTR_normalMinimum=('normalMinimum',xsi.DecodeFloat,xsi.EncodeFloat)
	XMLATTR_masteryValue=('masteryValue',xsi.DecodeFloat,xsi.EncodeFloat)
	XMLCONTENT=xml.XMLElementContent

	def __init__(self,parent):
		QTIVariableDeclaration.__init__(self,parent)
		self.view={}
		self.interpretation=None
		self.longInterpretation=None
		self.normalMaximum=None
		self.normalMinimum=None
		self.masteryValue=None
		self.lookupTable=None
	
	def QTIMatchTable(self):
		child=QTIMatchTable(self)
		self.lookupTable=child
		return child
	
	def QTIInterpolationTable(self):
		child=QTIInterpolationTable(self)
		self.lookupTable=child
		return child
	
	def GetChildren(self):
		children=QTIVariableDeclaration.GetChildren(self)
		xml.OptionalAppend(children,self.lookupTable)
		return children
	
	def GotChildren(self):
		self.parent.RegisterDeclaration(self)

	
			
class QTIBodyElement(QTIElement):
	"""Abstract class to represent elements within content.
	
	<xsd:attributeGroup name="bodyElement.AttrGroup">
		<xsd:attribute name="id" type="identifier.Type" use="optional"/>
		<xsd:attribute name="class" use="optional">
			<xsd:simpleType>
				<xsd:list itemType="styleclass.Type"/>
			</xsd:simpleType>
		</xsd:attribute>
		<xsd:attribute ref="xml:lang"/>
		<xsd:attribute name="label" type="string256.Type" use="optional"/>
	</xsd:attributeGroup>
	"""
	XMLATTR_id=('id',ValidateIdentifier,lambda x:x)		
	XMLATTR_label='label'
	XMLATTR_class='styleClass'

	def __init__(self,parent):
		QTIElement.__init__(self,parent)
		self.id=None
		self.styleClass=None
		self.label=None
	
		

class QTIObjectFlowMixin: pass

QTIBlockMixin=html.XHTMLBlockMixin
QTIFlowMixin=html.XHTMLFlowMixin		# xml:base is handled automatically for all elements

class QTISimpleInline(html.XHTMLInlineMixin,QTIBodyElement):
	# need to constrain content to html.XHTMLInlineMixin
	def ChildElement(self,childClass,name=None):
		if issubclass(childClass,html.XHTMLInlineMixin):
			return QTIBodyElement.ChildElement(self,childClass,name)
		else:
			# This child cannot go in here
			raise QTIValidityError("%s in %s"%(childClass.__name__,self.__class__.__name__))		

class QTISimpleBlock(QTIBlockMixin,QTIBodyElement):
	# need to constrain content to QTIBlockMixin
	def ChildElement(self,childClass,name=None):
		if issubclass(childClass,QTIBlockMixin):
			return QTIBodyElement.ChildElement(self,childClass,name)
		else:
			# This child cannot go in here
			raise QTIValidityError("%s in %s"%(repr(name),self.__class__.__name__))		

class QTIAtomicInline(html.XHTMLInlineMixin,QTIBodyElement): pass

class QTIAtomicBlock(QTIBlockMixin,QTIBodyElement):
	# need to constrain content to html.XHTMLInlineMixin
	def ChildElement(self,childClass,name=None):
		if issubclass(childClass,html.XHTMLInlineMixin):
			return QTIBodyElement.ChildElement(self,childClass,name)
		else:
			# This child cannot go in here
			raise QTIValidityError("%s in %s"%(childClass.__name__,self.__class__.__name__))

	
class QTIItemBody(QTIBodyElement):
	"""Represents the itemBody element.
	
	<xsd:attributeGroup name="itemBody.AttrGroup">
		<xsd:attributeGroup ref="bodyElement.AttrGroup"/>
	</xsd:attributeGroup>
	
	<xsd:group name="itemBody.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="block.ElementGroup" minOccurs="0" maxOccurs="unbounded"/>
		</xsd:sequence>
	</xsd:group>
	"""	
	XMLNAME=(IMSQTI_NAMESPACE,'itemBody')
	XMLCONTENT=xmlns.XMLElementContent	


class QTIRubricBlock(QTISimpleBlock):
	"""Represent the rubricBlock element.

	<xsd:attributeGroup name="rubricBlock.AttrGroup">
		<xsd:attributeGroup ref="simpleBlock.AttrGroup"/>
		<xsd:attribute name="view" use="required">
			<xsd:simpleType>
				<xsd:list itemType="view.Type"/>
			</xsd:simpleType>
		</xsd:attribute>
	</xsd:attributeGroup>
	
	<xsd:group name="rubricBlock.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="simpleBlock.ContentGroup"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'rubricBlock')
	XMLATTR_view=('view',DecodeView,EncodeView)
	XMLCONTENT=xmlns.XMLElementContent

	def __init__(self,parent):
		QTISimpleBlock.__init__(self,parent)
		self.view={}
	
	def AddView(self,view):
		if type(view) in StringTypes:
			view=QTIView.DecodeView(view.strip())
		viewValue=QTIView.EncodeView(view)
		if viewValue:	
			self.view[view]=viewValue
		else:
			raise ValueError("illegal value for view: %s"%view)


#
#	INTERACTIONS
#
class QTIInteraction(QTIBodyElement):
	"""Abstract class to act as a base for all interactions.

	<xsd:attributeGroup name="interaction.AttrGroup">
		<xsd:attributeGroup ref="bodyElement.AttrGroup"/>
		<xsd:attribute name="responseIdentifier" type="identifier.Type" use="required"/>
	</xsd:attributeGroup>
	"""
	XMLATTR_responseIdentifier=('responseIdentifier',ValidateIdentifier,lambda x:x)

	def __init__(self,parent):
		QTIBodyElement.__init__(self,parent)
		self.responseIdentifier=''
	

class QTIInlineInteration(QTIInteraction,html.XHTMLInlineMixin):
	"""Abstract class for interactions that are treated as inline."""
	pass


class QTIBlockInteraction(QTIInteraction,html.XHTMLBlockMixin):
	"""Abstract class for interactions that are treated as blocks.
	
	<xsd:group name="blockInteraction.ContentGroup">
		<xsd:sequence>
			<xsd:element ref="prompt" minOccurs="0" maxOccurs="1"/>
		</xsd:sequence>
	</xsd:group>
	"""
	def __init__(self,parent):
		QTIInteraction.__init__(self,parent)
		self.QTIPrompt=None
	

class QTIPrompt(QTIBodyElement):
	"""The prompt used in block interactions.

	<xsd:group name="prompt.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="inlineStatic.ElementGroup" minOccurs="0" maxOccurs="unbounded"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'prompt')
	XMLCONTENT=xmlns.XMLMixedContent

	def __init__(self,parent):
		QTIBodyElement.__init__(self,parent)

	def ChildElement(self,childClass,name=None):
		if issubclass(childClass,html.XHTMLInlineMixin):
			return QTIBodyElement.ChildElement(self,childClass,name)
		else:
			# This child cannot go in here
			raise QTIValidityError("%s in %s"%(childClass.__name__,self.__class__.__name__))		


class QTIChoice(QTIBodyElement):		
	"""The base class used for all choices.

	<xsd:attributeGroup name="choice.AttrGroup">
		<xsd:attributeGroup ref="bodyElement.AttrGroup"/>
		<xsd:attribute name="identifier" type="identifier.Type" use="required"/>
		<xsd:attribute name="fixed" type="boolean.Type" use="optional"/>
		<xsd:attribute name="templateIdentifier" type="identifier.Type" use="optional"/>
		<xsd:attribute name="showHide" type="showHide.Type" use="optional"/>
	</xsd:attributeGroup>
	"""
	XMLATTR_fixed=('fixed',xsi.DecodeBoolean,xsi.EncodeBoolean)
	XMLATTR_identifier=('identifier',ValidateIdentifier,lambda x:x)
	XMLATTR_showHide=('showHide',DecodeShowHide,EncodeShowHide)
	XMLATTR_templateIdentifier=('templateIdentifier',ValidateIdentifier,lambda x:x)
	
	def __init__(self,parent):
		QTIBodyElement.__init__(self,parent)
		self.identifier=''
		self.fixed=None
		self.templateIdentifier=None
		self.showHide=None


class QTIAssociableChoice(QTIChoice):
	"""The base class used for choices used in associations.
	
	<xsd:attributeGroup name="associableChoice.AttrGroup">
		<xsd:attributeGroup ref="choice.AttrGroup"/>
		<xsd:attribute name="matchGroup" use="optional">
			<xsd:simpleType>
				<xsd:list itemType="identifier.Type"/>
			</xsd:simpleType>
		</xsd:attribute>
	</xsd:attributeGroup>
	"""
	XMLATTR_matchGroup=('matchGroup',ValidateIdentifier,lambda x:x)
	
	def __init__(self,parent):
		QTIChoice.__init__(self,parent)
		self.matchGroup=[]
	

#
#		SIMPLE INTERACTIONS
#

class QTIChoiceInteraction(QTIBlockInteraction):
	"""Represents the choiceInteraction element.
	
	<xsd:attributeGroup name="choiceInteraction.AttrGroup">
		<xsd:attributeGroup ref="blockInteraction.AttrGroup"/>
		<xsd:attribute name="shuffle" type="boolean.Type" use="required"/>
		<xsd:attribute name="maxChoices" type="integer.Type" use="required"/>
		<xsd:attribute name="minChoices" type="integer.Type" use="optional"/>
	</xsd:attributeGroup>
	
	<xsd:group name="choiceInteraction.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="blockInteraction.ContentGroup"/>
			<xsd:element ref="simpleChoice" minOccurs="1" maxOccurs="unbounded"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'choiceInteraction')
	XMLATTR_maxChoices=('maxChoices',xsi.DecodeInteger,xsi.EncodeInteger)	
	XMLATTR_minChoices=('minChoices',xsi.DecodeInteger,xsi.EncodeInteger)
	XMLATTR_shuffle=('shuffle',xsi.DecodeBoolean,xsi.EncodeBoolean)
	XMLCONTENT=xmlns.XMLElementContent

	def __init__(self,parent):
		QTIBlockInteraction.__init__(self,parent)
		self.shuffle=False
		self.maxChoices=1
		self.minChoices=None
		self.QTISimpleChoice=[]
		
	def GetChildren(self):
		return QTIBlockInteraction.GetChildren(self)+self.QTISimpleChoice
		

class QTISimpleChoice(QTIChoice):
	"""Represents the simpleChoice element.

	<xsd:group name="simpleChoice.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="flowStatic.ElementGroup" minOccurs="0" maxOccurs="unbounded"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'simpleChoice')
	XMLCONTENT=xmlns.XMLMixedContent

	def ChildElement(self,childClass,name=None):
		if issubclass(childClass,html.XHTMLFlowMixin):
			return QTIChoice.ChildElement(self,childClass,name)
		else:
			# This child cannot go in here
			raise QTIValidityError("%s in %s"%(repr(name),self.__class__.__name__))		

#
#	RESPONSE PROCESSING
#

#
#		Generalized Response Processing
#
class QTIResponseProcessing(QTIElement):
	"""Represents the responseProcessing element.

	<xsd:attributeGroup name="responseProcessing.AttrGroup">
		<xsd:attribute name="template" type="uri.Type" use="optional"/>
		<xsd:attribute name="templateLocation" type="uri.Type" use="optional"/>
	</xsd:attributeGroup>
	
	<xsd:group name="responseProcessing.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="responseRule.ElementGroup" minOccurs="0" maxOccurs="unbounded"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'responseProcessing')
	XMLATTR_template='template'
	XMLATTR_templateLocation='templateLocation'
	XMLCONTENT=xmlns.XMLElementContent

	def __init__(self,parent):
		QTIElement.__init__(self,parent)
		self.template=None
		self.templateLocation=None
		self.QTIResponseRule=[]
		
	def GetChildren(self):
		return self.QTIResponseRule+QTIElement.GetChildren(self)


class QTIResponseRule(QTIElement):
	"""Abstract class to represent response rules."""
	pass


class QTIResponseCondition(QTIResponseRule):
	"""Represents responseRule element.

	<xsd:group name="responseCondition.ContentGroup">
		<xsd:sequence>
			<xsd:element ref="responseIf" minOccurs="1" maxOccurs="1"/>
			<xsd:element ref="responseElseIf" minOccurs="0" maxOccurs="unbounded"/>
			<xsd:element ref="responseElse" minOccurs="0" maxOccurs="1"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'responseCondition')
	XMLCONTENT=xmlns.XMLElementContent

	def __init__(self,parent):
		QTIResponseRule.__init__(self,parent)
		self.QTIResponseIf=QTIResponseIf(self)
		self.QTIResponseElseIf=[]
		self.QTIResponseElse=None
	
	def GetChildren(self):
		children=[self.QTIResponseIf]+self.QTIResponseElseIf
		xml.OptionalAppend(children,self.QTIResponseElse)
		return children
	

class QTIResponseIf(QTIElement):
	"""Represents the responseIf element.

	<xsd:group name="responseIf.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="expression.ElementGroup" minOccurs="1" maxOccurs="1"/>
			<xsd:group ref="responseRule.ElementGroup" minOccurs="0" maxOccurs="unbounded"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'responseIf')
	XMLCONTENT=xmlns.XMLElementContent
	
	def __init__(self,parent):
		QTIElement.__init__(self,parent)
		self.QTIExpression=None
		self.QTIResponseRule=[]
	
	def GetChildren(self):
		children=[]
		xml.OptionalAppend(children,self.QTIExpression)
		return children+self.QTIResponseRule


class QTIResponseElse(QTIElement):
	"""Represents the responseElse element.

	<xsd:group name="responseElse.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="responseRule.ElementGroup" minOccurs="0" maxOccurs="unbounded"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'responseElse')
	XMLCONTENT=xmlns.XMLElementContent
	
	def __init__(self,parent):
		QTIElement.__init__(self,parent)
		self.QTIResponseRule=[]
	
	def GetChildren(self):
		return self.QTIResponseRule


class QTIResponseElseIf(QTIResponseIf):
	"""Represents the responseElseIf element.

	<xsd:group name="responseElseIf.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="expression.ElementGroup" minOccurs="1" maxOccurs="1"/>
			<xsd:group ref="responseRule.ElementGroup" minOccurs="0" maxOccurs="unbounded"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'responseElseIf')



class QTISetOutcomeValue(QTIResponseRule):
	"""Represents the setOutcomeValue element.

	<xsd:attributeGroup name="setOutcomeValue.AttrGroup">
		<xsd:attribute name="identifier" type="identifier.Type" use="required"/>
	</xsd:attributeGroup>
	
	<xsd:group name="setOutcomeValue.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="expression.ElementGroup" minOccurs="1" maxOccurs="1"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'setOutcomeValue')
	XMLATTR_identifier='identifier'
	XMLCONTENT=xmlns.XMLElementContent

	def __init__(self,parent):
		QTIResponseRule.__init__(self,parent)
		self.identifier=''
		self.QTIExpression=None
	
	def GetChildren(self):
		children=[]
		xml.OptionalAppend(children,self.QTIExpression)
		return children	

	
#
#	EXPRESSIONS
#
class QTIExpression(QTIElement):
	pass
	

#
#		Built-in General Expressions
#
class QTIBaseValue(QTIExpression):
	"""Represents the baseValue element.

	<xsd:attributeGroup name="baseValue.AttrGroup">
		<xsd:attribute name="baseType" type="baseType.Type" use="required"/>
	</xsd:attributeGroup>
	
	<xsd:complexType name="baseValue.Type">
		<xsd:simpleContent>
			<xsd:extension base="xsd:string">
				<xsd:attributeGroup ref="baseValue.AttrGroup"/>
			</xsd:extension>
		</xsd:simpleContent>
	</xsd:complexType>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'baseValue')
	XMLATTR_baseType=('baseType',DecodeBaseType,EncodeBaseType)
	XMLCONTENT=xmlns.XMLMixedContent

	def __init__(self,parent):
		QTIExpression.__init__(self,parent)
		self.baseType=QTIBaseType.string


class QTIVariable(QTIExpression):
	"""Represents a variable value look-up.

	<xsd:attributeGroup name="variable.AttrGroup">
		<xsd:attribute name="identifier" type="identifier.Type" use="required"/>
		<xsd:attribute name="weightIdentifier" type="identifier.Type" use="optional"/>
	</xsd:attributeGroup>
	
	<xsd:complexType name="variable.Type" mixed="false">
		<xsd:attributeGroup ref="variable.AttrGroup"/>
	</xsd:complexType>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'variable')
	XMLATTR_identifier='identifier'
	XMLATTR_weightIdentifier='weightIdentifier'
	XMLCONTENT=xmlns.XMLEmpty
	
	def __init__(self,parent):
		QTIExpression.__init__(self,parent)
		self.identifier=''
		self.weightIdentifier=''

#
#		Expressions Used only in Outcomes Processing
#


#
#		Operators
#
class QTIExpressionList(QTIExpression):
	"""An abstract class to help implement binary+ operators."""
	XMLCONTENT=xmlns.XMLElementContent
	
	def __init__(self,parent):
		QTIExpression.__init__(self,parent)
		self.QTIExpression=[]
	
	def GetChildren(self):
		return self.QTIExpression


class QTIUnaryExpression(QTIExpression):
	"""An abstract class to help implement unary operators."""
	XMLCONTENT=xmlns.XMLElementContent
	
	def __init__(self,parent):
		QTIExpression.__init__(self,parent)
		self.QTIExpression=None
	
	def GetChildren(self):
		if self.QTIExpression:
			return [self.QTIExpression]
		else:
			return []


class QTIMultiple(QTIExpressionList):
	"""Represents the multiple operator.

	<xsd:group name="multiple.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="expression.ElementGroup" minOccurs="0" maxOccurs="unbounded"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'multiple')

		
class QTIOrdered(QTIExpressionList):
	"""Represents the ordered operator.

	<xsd:group name="ordered.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="expression.ElementGroup" minOccurs="0" maxOccurs="unbounded"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'ordered')

			
class QTIContainerSize(QTIUnaryExpression):
	"""Represents the containerSize operator.

	<xsd:group name="containerSize.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="expression.ElementGroup" minOccurs="1" maxOccurs="1"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'containerSize')

			
class QTIIsNull(QTIUnaryExpression):
	"""Represents the isNull operator.

	<xsd:group name="isNull.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="expression.ElementGroup" minOccurs="1" maxOccurs="1"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'isNull')

			
class QTIIndex(QTIUnaryExpression):
	"""Represents the index operator.

	<xsd:attributeGroup name="index.AttrGroup">
		<xsd:attribute name="n" type="integer.Type" use="required"/>
	</xsd:attributeGroup>
	
	<xsd:group name="index.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="expression.ElementGroup" minOccurs="1" maxOccurs="1"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'index')
	XMLATTR_n=('n',xsi.DecodeInteger,xsi.EncodeInteger)

	def __init__(self,parent):
		QTIUnaryExpression.__init__(self,parent)
		self.n=None

	
class QTIFieldValue(QTIUnaryExpression):
	"""Represents the fieldValue operator.

	<xsd:attributeGroup name="fieldValue.AttrGroup">
		<xsd:attribute name="fieldIdentifier" type="identifier.Type" use="required"/>
	</xsd:attributeGroup>
	
	<xsd:group name="fieldValue.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="expression.ElementGroup" minOccurs="1" maxOccurs="1"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'fieldValue')
	XMLATTR_fieldIdentifier=('fieldIdentifier',ValidateIdentifier,lambda x:x)

	def __init__(self,parent):
		QTIUnaryExpression.__init__(self,parent)
		self.fieldIdentifier=''


class QTIRandom(QTIUnaryExpression):
	"""Represents the random operator.

	<xsd:group name="random.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="expression.ElementGroup" minOccurs="1" maxOccurs="1"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'random')

				
class QTIMember(QTIExpressionList):
	"""Represents the member operator.

	<xsd:group name="member.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="expression.ElementGroup" minOccurs="2" maxOccurs="2"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'member')

	
class QTIDelete(QTIExpressionList):
	"""Represents the delete operator.

	<xsd:group name="delete.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="expression.ElementGroup" minOccurs="2" maxOccurs="2"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'delete')


class QTIContains(QTIExpressionList):
	"""Represents the contains operator.

	<xsd:group name="contains.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="expression.ElementGroup" minOccurs="2" maxOccurs="2"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'contains')


class QTISubstring(QTIExpressionList):
	"""Represents the substring operator.

	<xsd:attributeGroup name="substring.AttrGroup">
		<xsd:attribute name="caseSensitive" type="boolean.Type" use="required"/>
	</xsd:attributeGroup>
	
	<xsd:group name="substring.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="expression.ElementGroup" minOccurs="2" maxOccurs="2"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'substring')
	XMLATTR_caseSensitive=('caseSensitive',xsi.DecodeBoolean,xsi.EncodeBoolean)

	def __init__(self,parent):
		QTIExpressionList.__init__(self,parent)
		self.caseSensitive=True


class QTINot(QTIUnaryExpression):
	"""Represents the not operator.

	<xsd:group name="not.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="expression.ElementGroup" minOccurs="1" maxOccurs="1"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'not')

				
class QTIAnd(QTIExpressionList):
	"""Represents the and operator.

	<xsd:group name="and.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="expression.ElementGroup" minOccurs="1" maxOccurs="unbounded"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'and')


class QTIOr(QTIExpressionList):
	"""Represents the or operator.

	<xsd:group name="or.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="expression.ElementGroup" minOccurs="1" maxOccurs="unbounded"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'or')


class QTIAnyN(QTIExpressionList):
	"""Represents the anyN operator.

	<xsd:attributeGroup name="anyN.AttrGroup">
		<xsd:attribute name="min" type="integerOrTemplateRef.Type" use="required"/>
		<xsd:attribute name="max" type="integerOrTemplateRef.Type" use="required"/>
	</xsd:attributeGroup>
	
	<xsd:group name="anyN.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="expression.ElementGroup" minOccurs="1" maxOccurs="unbounded"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'anyN')
	XMLATTR_min='min'
	XMLATTR_max='max'

	def __init__(self,parent):
		QTIExpressionList.__init__(self,parent)
		self.min=''
		self.max=''


class QTIMatch(QTIExpressionList):
	"""Represents the match operator.

	<xsd:group name="match.ContentGroup">
		<xsd:sequence>
			<xsd:group ref="expression.ElementGroup" minOccurs="2" maxOccurs="2"/>
		</xsd:sequence>
	</xsd:group>
	"""
	XMLNAME=(IMSQTI_NAMESPACE,'match')

	
#
#	METADATA
#
class QTIMetadata(QTIElement):
	"""Represents the qtiMetadata element used in content packages.
	
	<xsd:group name="qtiMetadata.ContentGroup">
		<xsd:sequence>
			<xsd:element ref="itemTemplate" minOccurs="0" maxOccurs="1"/>
			<xsd:element ref="timeDependent" minOccurs="0" maxOccurs="1"/>
			<xsd:element ref="composite" minOccurs="0" maxOccurs="1"/>
			<xsd:element ref="interactionType" minOccurs="0" maxOccurs="unbounded"/>
			<xsd:element ref="feedbackType" minOccurs="0" maxOccurs="1"/>
			<xsd:element ref="solutionAvailable" minOccurs="0" maxOccurs="1"/>
			<xsd:element ref="toolName" minOccurs="0" maxOccurs="1"/>
			<xsd:element ref="toolVersion" minOccurs="0" maxOccurs="1"/>
			<xsd:element ref="toolVendor" minOccurs="0" maxOccurs="1"/>
		</xsd:sequence>
	</xsd:group>
	"""	
	XMLNAME=(IMSQTI_NAMESPACE,'qtiMetadata')
	XMLCONTENT=xmlns.XMLElementContent
	
	def __init__(self,parent):
		QTIElement.__init__(self,parent)
		self.QMDItemTemplate=None
		self.QMDTimeDependent=None
		self.QMDComposite=None
		self.QMDInteractionType=[]
		self.QMDFeedbackType=None
		self.QMDSolutionAvailable=None
		self.QMDToolName=None
		self.QMDToolVersion=None
		self.QMDToolVendor=None
	
	def GetChildren(self):
		children=[]
		xmlns.OptionalAppend(children,self.QMDItemTemplate)
		xmlns.OptionalAppend(children,self.QMDTimeDependent)
		xmlns.OptionalAppend(children,self.QMDComposite)
		children=children+self.QMDInteractionType
		xmlns.OptionalAppend(children,self.QMDFeedbackType)
		xmlns.OptionalAppend(children,self.QMDSolutionAvailable)
		xmlns.OptionalAppend(children,self.QMDToolName)
		xmlns.OptionalAppend(children,self.QMDToolVersion)
		xmlns.OptionalAppend(children,self.QMDToolVendor)
		return children+QTIElement.GetChildren(self)

class QMDItemTemplate(QTIElement):
	XMLNAME=(IMSQTI_NAMESPACE,'itemTemplate')

class QMDTimeDependent(QTIElement):
	XMLNAME=(IMSQTI_NAMESPACE,'timeDependent')

class QMDComposite(QTIElement):
	XMLNAME=(IMSQTI_NAMESPACE,'composite')

class QMDInteractionType(QTIElement):
	XMLNAME=(IMSQTI_NAMESPACE,'interactionType')

class QMDFeedbackType(QTIElement):
	XMLNAME=(IMSQTI_NAMESPACE,'feedbackType')

class QMDSolutionAvailable(QTIElement):
	XMLNAME=(IMSQTI_NAMESPACE,'solutionAvailable')

class QMDToolName(QTIElement):
	XMLNAME=(IMSQTI_NAMESPACE,'toolName')

class QMDToolVersion(QTIElement):
	XMLNAME=(IMSQTI_NAMESPACE,'toolVersion')

class QMDToolVendor(QTIElement):
	XMLNAME=(IMSQTI_NAMESPACE,'toolVendor')

		
class QTIDocument(xmlns.XMLNSDocument):
	classMap={}
	
	def __init__(self,**args):
		""""""
		xmlns.XMLNSDocument.__init__(self,defaultNS=IMSQTI_NAMESPACE,**args)
		self.SetNSPrefix(xsi.XMLSCHEMA_NAMESPACE,'xsi')
		if isinstance(self.root,QTIElement):
			self.root.SetAttribute((xsi.XMLSCHEMA_NAMESPACE,'schemaLocation'),IMSQTI_NAMESPACE+' '+IMSQTI_SCHEMALOCATION)
			
	def GetElementClass(self,name):
		return QTIDocument.classMap.get(name,QTIDocument.classMap.get((name[0],None),xmlns.XMLNSElement))

	def AddToContentPackage(self,cp,metadata,dName=None):
		"""Copies this QTI document into a content package and returns the resource ID used.
		
		An optional directory name can be specified in which to put the resource files."""
		if not isinstance(self.root,QTIAssessmentItem):
			print self.root
			raise TypeError
		# We call the elemement's AddToContentPackage method which returns the new base URI
		# of the document.
		baseURI=self.root.AddToContentPackage(cp,metadata,dName)
		self.SetBase(baseURI)
		# Finish by writing out the document to the new baseURI
		self.Create()

xmlns.MapClassElements(QTIDocument.classMap,globals())
# also add in the profile of HTML but with the namespace rewritten to ours
for name in QTI_HTMLProfile:
	eClass=html.XHTMLDocument.classMap.get((html.XHTML_NAMESPACE,name),None)
	if eClass:
		QTIDocument.classMap[(IMSQTI_NAMESPACE,name)]=eClass

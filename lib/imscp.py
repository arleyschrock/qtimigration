"""Copyright (c) 2004-2008, University of Cambridge.

All rights reserved.

Redistribution and use of this software in source and binary forms
(where applicable), with or without modification, are permitted
provided that the following conditions are met:

 *  Redistributions of source code must retain the above copyright
    notice, this list of conditions, and the following disclaimer.

 *  Redistributions in binary form must reproduce the above
    copyright notice, this list of conditions, and the following
    disclaimer in the documentation and/or other materials provided with
    the distribution.
    
 *  Neither the name of the University of Cambridge, nor the names of
    any other contributors to the software, may be used to endorse or
    promote products derived from this software without specific prior
    written permission.

THIS SOFTWARE IS PROVIDED ``AS IS'', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE."""

from lom import *
from imsqti import QTIMetadata
import StringIO
import os
from shutil import copyfile

IMSCP_NAMESPACE="http://www.imsglobal.org/xsd/imscp_v1p1"
IMSMD_NAMESPACE="http://www.imsglobal.org/xsd/imsmd_v1p2"
IMSQTI_NAMESPACE="http://www.imsglobal.org/xsd/imsqti_v2p1"

SCHEMA_LOCATION="""http://www.imsglobal.org/xsd/imscp_v1p1 http://www.imsglobal.org/xsd/imscp_v1p2.xsd 
http://www.imsglobal.org/xsd/imsmd_v1p2 http://www.imsglobal.org/xsd/imsmd_v1p2p4.xsd 
http://www.imsglobal.org/xsd/imsqti_v2p1 http://www.imsglobal.org/xsd/imsqti_v2p1.xsd"""

class ContentPackage:
	def __init__ (self):
		self.id=None
		self.idSpace={}
		self.fileSpace={}
		self.resources=[]
		self.lom=None

	def GetUniqueID (self,baseStr):
		idStr=baseStr
		idExtra=1
		while self.idSpace.has_key(idStr):
			idStr=baseStr+'-'+str(idExtra)
			idExtra=idExtra+1
		return idStr
	
	def GetUniqueFileName (self,fName,dataHash=None):
		nameParts=fName.split(".")
		stem=nameParts[0]
		if not stem:
			stem="file"
		i=0
		while 1:
			nameParts[0]=stem
			if i:
				nameParts[0]='%s-%i'%(stem,i)
			else:
				nameParts[0]=stem
			fName=string.join(nameParts,'.')
			if self.fileSpace.has_key(fName):
				if dataHash and self.fileSpace[fName]==dataHash:
					break
				i+=1
				continue
			break
		self.fileSpace[fName]=dataHash
		return fName

	def AddResource (self,r):
		if not r.id or self.idSpace.has_key(r.id):
			r.AutoSetID(self)
		self.idSpace[r.id]=r
		self.resources.append(r)
			
	def GetLOM (self):
		if not self.lom:
			self.lom=LOM()
		return self.lom

	def DumpToDirectory (self,path):
		if not os.path.exists(path):
			os.mkdir(path)
		assert os.path.isdir(path)
		manifestPath=os.path.join(path,'imsmanifest.xml')
		f=open(manifestPath,'w')
		print "Writing manifest file: "+manifestPath
		self.WriteManifestXML(f)
		f.close()
		for r in self.resources:
			r.DumpToDirectory(path)

	def WriteManifestXML (self,f):
		f.write('<?xml version="1.0"?>')
		f.write('\n<manifest')
		if self.id:
			f.write(' identifier="'+XMLString(self.id)+'"')
		else:
			f.write(' identifier="'+self.GetUniqueID("manifest")+'"')
		f.write('\n\txmlns="%s"'%IMSCP_NAMESPACE)
		f.write('\n\txmlns:imsmd="%s"'%IMSMD_NAMESPACE)
		f.write('\n\txmlns:imsqti="%s"'%IMSQTI_NAMESPACE)
		f.write('\n\txmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"')
		f.write('\n\txsi:schemaLocation="%s">'%SCHEMA_LOCATION)
		if self.lom:
			f.write('\n<metadata>\n\t<schema>IMS Content</schema>\n\t<schemaversion>1.1.3</schemaversion>')
			self.lom.WriteIMSXML(f,"imsmd:")
			f.write('\n</metadata>')
		f.write('\n<organizations/>')
		if self.resources:
			f.write('\n<resources>')
			for r in self.resources:
				r.WriteManifestXML(f)
			f.write('\n</resources>')
		f.write('\n</manifest>')
		

class CPResource:
	def __init__ (self):
		self.id=None
		self.type='webcontent'
		self.lom=None
		self.qtiMD=None
		self.files=[]
		self.entryPoint=None
	
	def SetIdentifier (self,identifier):
		self.id=identifier
		self.FixIdentifier()
	
	def FixIdentifier (self):
		# Must match correct syntax
		newID=""
		for c in self.id:
			if not c in NMTOKEN_CHARS:
				c='_'
			if not newID and not (c in NMSTART_CHARS):
				newID="ID_"
			newID=newID+c
		self.id=newID
		
	def AutoSetID (self,cp):
		self.id=None
		if self.lom:
			self.id=self.lom.SuggestXMLID()
			self.FixIdentifier()
		else:
			self.id="resource"
		self.id=cp.GetUniqueID(self.id)
			
	def SetType (self,type):
		self.type=type
			
	def GetLOM (self):
		if not self.lom:
			self.lom=LOM()
		return self.lom

	def GetQTIMD (self):
		if not self.qtiMD:
			self.qtiMD=QTIMetadata()
		return self.qtiMD
		
	def AddFile (self,cpf,entryPoint=0):
		self.files.append(cpf)
		if entryPoint:
			self.entryPoint=cpf

	def DumpToDirectory (self,path):
		for f in self.files:
			f.DumpToDirectory(path)

	def WriteManifestXML (self,f):
		f.write('\n\t<resource identifier="'+self.id+'"')
		if self.type:
			f.write(' type="'+self.type+'"')
		if self.entryPoint:
			self.entryPoint.WriteResourceHREF(f)
		if self.files or self.lom:
			f.write('>')
			if self.lom or self.qtiMD:
				f.write('\n\t\t<metadata>')
				if self.lom:
					self.lom.WriteIMSXML(f,"imsmd:")
				if self.qtiMD:
					self.qtiMD.WriteXML(f,"imsqti:")
				f.write('\n\t\t</metadata>')
			for cpf in self.files:
				cpf.WriteManifestXML(f)
			f.write('\n\t</resource>')
		else:
			f.write('/>')				

class CPFile:
	def __init__ (self):
		self.href=None
		self.lom=None
		self.data=None
		self.dataPath=None
		
	def SetHREF (self,href):
		self.href=href
	
	def SetData (self,data):
		self.data=data

	def SetDataPath (self,dataPath):
		self.dataPath=dataPath
		
	def DumpToDirectory (self,path):
		if RelativeURL(self.href):
			filepath=ResolveCPURI(path,self.href)
			print "Writing file: "+filepath
			if self.dataPath is None:
				f=open(filepath,'w')
				f.write(self.data)
				f.close()
			else:
				try:
					copyfile(self.dataPath,filepath)
				except IOError:
					print 'Problem copying "%s" -> "%s"'%(self.dataPath,filepath)
					f=open(filepath,'w')
					f.write("Data Missing\n")
					f.close()

	def WriteResourceHREF (self,f):
		if self.href:
			f.write(' href="'+XMLString(self.href)+'"')
			
	def WriteManifestXML (self,f):
		f.write('\n\t\t<file')
		if self.href:
			f.write(' href="'+XMLString(self.href)+'"')
		if self.lom:
			f.write('>')
			if self.lom:
				f.write('\n\t\t\t<metadata>\n\t\t\t\t<schema>IMS Content</schema>\n\t\t\t\t<schemaversion>1.1.3</schemaversion>')
				self.lom.WriteIMSXML(f,"imsmd:")
				f.write('\n\t\t\t</metadata>')
			f.write('\n\t\t</file>')
		else:
			f.write('/>')

def ResolveCPURI (cpPath,uri):
	walk=0
	path=cpPath
	segments=string.split(uri,'/')
	for segment in segments:
		if segment==".":
			continue
		elif segment=="..":
			if walk:
				path,discard=os.path.split(path)
				walk=walk-1
			print "Warning: relative URL tried to leave the CP directory"
		else:
			walk=walk+1
			path=os.path.join(path,DecodePathSegment(segment))
	return path
import re
import os
import json
import Witty.library.functions as wf
from Witty.library.WittyStatement import WittyStatement
from Witty.library.Docblock import Docblock

# Debug wrappers
def warn(message, showStack = True): wf.warn(message, showStack, 3)
def info(message, showStack = True): wf.info(message, showStack, 3)
def pr(message, showStack = True): wf.pr(message, showStack, 3)

class WittyFile:

	def __init__(self, project, fileName, core = False):

		# The project we're modifying
		self.project = project

		# The filename
		self.fileName = fileName
		self.name = fileName

		# Set the working string to empty
		self.working = ''

		# Create the statements
		self.splitStatements = []
		self.statements = []

		# Empty the blocks
		self.docblocks = []

		# Create the scopes
		self.scopes = []
		self.scopeDocBlocks = {}

		# First we add an empty scope because 0 == False and all
		self.createNewScope('global', False)
		self.createNewScope('root', 0)

		self.root = {}

		# See if the language is set already
		self.language = project.getFileLanguage(fileName)

		self.intel = None

		# Open the original file
		if not core:
			fileHandle = open(fileName, 'rU')

			# Read in the original file
			self.original = fileHandle.read()

			# The array
			self.fileArray = self.original.split('\n')

			# Close the file
			fileHandle.close()

			# Do we have to get the language of the file?
			self.detectLanguage()

			# Recursively split all the statements
			splitStatements = wf.splitStatements(self.original, 1)
			self.objStatements = self.parseStatements(splitStatements, 1)

			wf.log(self.scopes, self.language + 'scopes')
			wf.log({fileName: splitStatements, 'scopes': self.scopes})
			wf.log(self.objStatements, 'witty-' + self.language + '-objstatements')

			# Recursively go through all the statements in this file
			for stat in self.objStatements:
				WittyStatement(self, stat)

			for s in self.statements:
				wf.log(s, 'witty-' + self.language + '-statements')

		self.setIntel()

	## Set the correct intel for this file
	def setIntel(self):

		if self.language == 'nodejs':
			self.intel = self.project.intelNode
		elif self.language == 'browser':
			self.intel = self.project.intelBrowser
		else:
			self.intel = self.project.intelNode

	## Get the language of this file
	def detectLanguage(self, noSideEffect = False):

		if self.language:
			return self.language

		# @todo: Remove strings & comments before detecting keywords

		# The counts
		node = 0
		browser = 0

		# Default is node
		result = 'nodejs'

		# Count node keywords
		for keyword in ['require(', 'global.', 'module.', 'module.exports', 'process.']:
			node += self.original.count(keyword)

		# Count browser keywords
		for keyword in ['window', 'document', 'getElementById', 'document.createElement']:
			browser += self.original.count(keyword)

		if browser > node:
			result = 'javascript'

		if not noSideEffect: self.setLanguage(result)

		return result

	## Set the language of this file
	def setLanguage(self, language):

		self.language = language
		self.setIntel()
		self.project.setFileLanguage(self.fileName, language)

	# Load in json files
	def loadFiles(self, directory, language):

		self.language = language

		for root, dirs, files in os.walk(directory, topdown=True):
			for fileName in files:
				filePath = os.path.join(root, fileName)
				tempFile = open(filePath, 'rU')
				json_data = tempFile.read()
				tempFile.close()

				try:
					data = json.loads(json_data)
				except ValueError:
					pr('Error decoding JSON file ' + filePath)
					continue

				targetScopeId = data['scope']
				targetLanguage = data['languages']

				# If this fiel is not meant for this language, skip it
				if not language in targetLanguage:
					continue

				# @todo: scope's above 0 should be loaded differently!
				targetScope = self.scopes[targetScopeId]
				targetScope['variables'].update(data['variables'])


	# Parsing statements begins here
	def parseStatements(self, workingStatements, scopeId = 1):

		wf.log(workingStatements, 'wittystats')

		statements = []

		for stat in workingStatements:
			statements.append(self.parseStatement(stat, scopeId))

		return statements

	## Parse the statement
	#  @param   self                The object pointer
	#  @param   statement           A primitive statement object
	#  @param   scopeId             The id of the scope it's in (id in the file)
	def parseStatement(self, statement, scopeId, docblock = False):

		statement['scopeId'] = scopeId
		statement['line'] = self.original.count('\n', 0, statement['beginId']) + 1

		if 'openType' in statement and statement['openType'] == 'statement':

			# @todo: Here, we just pass the statement docblock to the expressions
			try:
				docblock = statement['docblock']
			except KeyError:
				statement['docblock'] = ''
				docblock = False

			resultCount = 0

			if not isinstance(statement['result'], list):
				statement['result'] = [statement['result']]

			# Loop through all the results in this statement
			for r in statement['result']:

				# Add the docblock tot he first result, if it doesn't have one already
				if resultCount == 0 and docblock and not r['docblock']:
					r['docblock'] = docblock

				# If there is an expression in this result
				if 'expression' in r:
					self.parseStatement(r['expression'], scopeId, docblock)

				# Parse block content
				if 'block' in r:

					if statement['openName'] == 'function':
						# @todo: some blocks are created even when they're not a function!
						newScope = self.createNewScope(statement['line'], scopeId, docblock)
						statement['subscopeId'] = newScope
						for stat in r['block']['parsed']:
							self.parseStatement(stat, newScope)
					else:
						for stat in r['block']['parsed']:
							self.parseStatement(stat, scopeId, docblock)

				resultCount += 1


		elif 'openType' in statement and statement['openType'] == 'expression':
			# It's an expression

			for f in statement['functions']:

				lineNr = self.original.count('\n', 0, f['beginId']) + 1

				# @todo: the statement docblock is currently the only docblock we store
				# expressions can't have docblocks yet
				self.parseStatement(f, self.createNewScope(lineNr, scopeId, docblock))
		
		# Recursively parse block contents
		if 'block' in statement:
			
			for stat in statement['block']['parsed']:
				self.parseStatement(stat, scopeId, docblock)
		
		return statement

	def getFileLine(self, linenr):
		try:
			return self.fileArray[linenr-1]
		except IndexError:
			return False

	# Create a new scope, return its ID
	def createNewScope(self, name, parentScope, docBlock = ''):
		newId = len(self.scopes)

		if isinstance(name, int):
			name = self.getFileLine(name)
			if name:
				name = name.strip()
			else:
				name = 'ERROR'
		
		self.scopes.append({'id': newId, 'name': name, 'parent': parentScope, 'variables': {}, 'level': 0})

		self.scopeDocBlocks[newId] = docBlock

		workingScope = self.scopes[newId]

		# Determine the level of this scope
		while workingScope['parent']:
			self.scopes[newId]['level'] += 1
			workingScope = self.scopes[workingScope['parent']]

		return newId
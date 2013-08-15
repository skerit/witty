import pickle, sublime, sublime_plugin
import Witty.library.functions as wf
from Witty.library.WittyScope import WittyScope
from Witty.library.WittyScope import WittyRoot
from Witty.library.WittyParser import WittyParser
from Witty.library.WittyVariable import WittyVariable
from Witty.library.WittyFile import WittyFile
import os

# Debug wrappers
def warn(message, showStack = True): wf.warn(message, showStack, 3)
def info(message, showStack = True): wf.info(message, showStack, 3)
def pr(message, showStack = True): wf.pr(message, showStack, 3)

# All the open projects
allProjects = {}

# Parser threads by project
parserThreads = {}

class WittyProject:

	# WittyProject Constructor
	def __init__(self, window):

		# Store the window in here
		self.window = window

		# Get all the folders in this project
		folders = window.folders()

		# The project data
		self.projectData = window.project_data()

		# Make sure a witty entry is made
		if not 'witty' in self.projectData:
			self.projectData['witty'] = {'folders': {}}

		self.folderArray = folders
		self.folders = self.projectData['witty']['folders']

		# Store the folders
		for path in folders:

			if not path in self.folders:
				self.folders[path] = {}


		# Update the final hash
		self.id = wf.generateHash(folders)

		# The pickle filename
		self.pickleFileName = '/dev/shm/wittypickle-' + self.id

		# The Single Point Of Contact to get data
		self.intelNode = None
		self.intelBrowser = None

		# Init the intel
		self._initIntel()

	## Get the language type of a file
	def getFileLanguage(self, filepath):

		fileInfo = self.getFileInfo(filepath)

		if fileInfo:
			baseFolder = fileInfo['base']
			fileName = fileInfo['file']
		else:
			return False

		# If the basefolder is found, and it's in the folders dict
		if baseFolder and baseFolder in self.folders:
			try:
				return self.folders[baseFolder][fileName]['language']
			except KeyError:
				return None
		else:
			return False

	## Set a file's language
	def setFileLanguage(self, filepath, language):

		fileInfo = self.getFileInfo(filepath)

		if fileInfo:
			baseFolder = fileInfo['base']
			fileName = fileInfo['file']

			if not fileName in self.folders[baseFolder]:
				self.folders[baseFolder][fileName] = {'language': None}

			self.folders[baseFolder][fileName]['language'] = language

			# Set the project data
			self.window.set_project_data(self.projectData)

			return True
		else:
			return False

	## Get a filepath info
	def getFileInfo(self, filepath):

		baseFolder = None
		fileName = None

		# First we need to find out what base folder this is in
		for path in self.folderArray:
			if filepath.startswith(path):
				baseFolder = path

				# Get the filename, without leading /
				fileName = filepath[len(path)+1:]

				return {'base': baseFolder, 'file': fileName}

		return False

	## On file open
	def onFileOpen(self, view):

		# See if the file language is already set
		setLanguage = self.getFileLanguage(view.file_name())

		if setLanguage:

			if setLanguage == 'browser':
				view.set_syntax_file('Packages/JavaScript/JavaScript.tmLanguage')
			elif setLanguage == 'nodejs':
				view.set_syntax_file('Packages/Witty/nodejs.tmLanguage')

	## Get the syntax setting
	def getSyntaxSetting(self, view):

		syntax = view.settings().get('syntax').split('/')[-1]

		# Packages/JavaScript/JavaScript.tmLanguage
		if syntax == 'JavaScript.tmLanguage':
			syntax = 'browser'
		# Packages/Witty/nodejs.tmLanguage
		elif syntax == 'nodejs.tmLanguage':
			syntax = 'nodejs'

		return syntax

	## On file save, called right before paseFiles
	def onFileSave(self, view):

		language = self.getSyntaxSetting(view)
		self.setFileLanguage(view.file_name(), language)

	# Begin parsing files
	def parseFiles(self, savedFileName = ''):
		
		# If a thread is already running: stop it
		if self.id in parserThreads and parserThreads[self.id]:
			print('Killing running thread')
			parserThreads[self.id]._stop()

		info('Start parsing "' + savedFileName + '"')

		parserThreads[self.id] = WittyParser(self, savedFileName)
		parserThreads[self.id].start()

	# Is data already available for this file?
	def hasFileData(self, fileName):

		language = self.getFileLanguage(fileName)

		if language == 'nodejs':
			thisIntel = self.intelNode
		elif language == 'browser':
			thisIntel = self.intelBrowser
		else:
			return False

		# If data is empty, return false
		if not thisIntel:
			return False

		if fileName in thisIntel.files:
			return True

		return False

	# Store all the data on disk
	def storeOnDisk(self):

		if self.pickleFileName and ((self.intelNode and len(self.intelNode.files)) or (self.intelBrowser and len(self.intelBrowser.files))):
			# Pickle data
			pickleFile = open(self.pickleFileName, 'wb')
			pickle.dump({'nodejs': self.intelNode, 'browser': self.intelBrowser}, pickleFile)
			pickleFile.close()

	# Query for completions
	def queryForCompletions(self, view, prefix, locations):
		
		currentFileName = view.file_name()

		if not wf.isJavascriptFile(currentFileName):
			return

		current_file = view.file_name()

		# Get the region
		region = view.sel()[0]

		# Get the point position of the cursor
		point = region.begin()
		(row,col) = view.rowcol(point)

		# Get the lines from the beginning of the page until the cursor
		to_cursor_lines = view.lines(sublime.Region(0, point))

		lines = []

		for l in to_cursor_lines:
			lines.append(wf.removeComment(view.substr(l).strip()))

		stack = []
		oBraces = 0
		cBraces = 0
		mem = {}

		# Get the last open function line
		for l in lines:
			oBraces += l.count('{')
			cBraces += l.count('}')

			newDif = oBraces-cBraces

			try:
				if stack[0]['difference'] > newDif:
					
					if not oBraces in mem:
						try:
							del stack[0]
						except IndexError:
							pass

					mem[oBraces] = True
			except IndexError:
				pass

			if wf.isFunctionDeclaration(l):
				body = l.split('function', 1)[1]
				
				if body.count('{') > body.count('}'):
					stack.insert(0, {'line': l, 'open': oBraces, 'closed': cBraces, 'difference': oBraces-cBraces})

		try:
			function_scope = stack[0]['line']
		except IndexError:
			function_scope = current_file

		# Get the current line
		full_line = view.substr(view.line(region))

		# Get the line up to the cursor
		left_line = full_line[:col].strip()

		# Get the line after the cursor
		right_line = full_line[col:].strip()

		# All lines to the cursor
		text = '\n'.join(lines)

		# Get the better prefix
		brefix = wf.getBetterPrefix(left_line)

		stats = wf.splitStatements(text, 0)

		if not len(stats):
			lastStat = False
		else:
			lastStat = stats[len(stats)-1]

		scope = self.getScope(current_file, function_scope)

		if scope:

			getScopeVars = True
			normalized = False

			if lastStat and lastStat['openName'] == 'var':
				lastExpr = lastStat['result'][len(lastStat['result'])-1]
				
				if 'expression' in lastExpr:
					expr = lastExpr['expression']['result']['text']

					# Only get more info if the last expression hasn't been terminated!
					if not lastExpr['expression']['terminated']:
						try:
							normalized = wf.tokenizeExpression(expr)
							getScopeVars = False
						except KeyError:
							pass

			elif lastStat and lastStat['openName'] == 'expression':
				expr = lastStat['result']['text']

				if expr:
					normalized = wf.tokenizeExpression(expr)
					getScopeVars = False

			if normalized:
				
				temp = expr.replace(' ', '')
				temp = temp.replace('\n', '')
				temp = temp.replace('\t', '')

				endsWithMember = False

				if temp.endswith('.') or temp.endswith('['):
					endsWithMember = True

				active = {'properties': []}

				pr(normalized)
				
				for token in normalized:

					if not token['type']:
						active = {'properties': []}
						continue

					if 'member' in token and not token['member']:
						active = {}
						active['name'] = token['text']
						active['properties'] = []
					else:
						active['properties'].append(token['text'])

				if 'properties' in active and not endsWithMember and len(active['properties']):
					del active['properties'][len(active['properties'])-1]

				pr(active)

				if 'name' in active:
					foundVar = scope.findVariable(active['name'])

					if foundVar:

						# See if we need to get a property of this var
						if active['properties']:
							pr('Looking for properties')
							pr(active['properties'])
							temp = foundVar.findProperties(active['properties'])
							if temp: foundVar = temp

						# Make a copy of the foundVar properties
						variables = foundVar.getProperties()

						getScopeVars = False

						# # Now get the prototype properties of the foundVar's type
						# if foundVar.types:
						# 	# Create empty object
						# 	variables = {}

						# 	for typeName in foundVar.types:
						# 		pr('Looking for ' + typeName)
						# 		typeVar = scope.findVariable(typeName)

						# 		if 'prototype' in typeVar.properties:
						# 			variables.update(typeVar.properties['prototype'].properties)

						# 	# Now overwrite anything with our own properties
						# 	variables.update(foundVar.properties)

			else:
				getScopeVars = True

			# If variables isn't defined, get all the scope variables
			try:
				variables
			except NameError:
				getScopeVars = True

			if getScopeVars:
				variables = scope.getAllVariables()


			completions = []

			for varname, varinfo in variables.items():
				completions.append((varname + '\t' + str(len(varinfo.propArray)) + '\t' + str(varinfo.type), varname))

			# INHIBIT_WORD_COMPLETIONS = 8 = Only show these completions
			# INHIBIT_EXPLICIT_COMPLETIONS = 16 = ?
			return (completions, sublime.INHIBIT_WORD_COMPLETIONS)
		else:

			info('Scope "' + function_scope + '" in file ' + current_file + ' was not found')

			wittyOnly = True

			if wittyOnly:
				# We only want witty results, so make sure sublime doesn't interfere
				return ([], sublime.INHIBIT_WORD_COMPLETIONS)
			else:
				# Let sublime do what it wants
				return



	# Initially set the data by restoring or parsing
	def _initIntel(self):

		# Try to restore the data
		jar = self._unpickle()

		# If the jar is not empty, return the data
		if jar:
			self.intelNode = jar['nodejs']
			self.intelBrowser = jar['browser']
		else:

			# Create a new intel object
			self.intelNode = Intel(self, 'nodejs')
			self.intelBrowser = Intel(self, 'browser')

			# Load in the json files for node.js
			CORENODE = WittyFile(self, 'CORENODE', True)
			CORENODE.loadFiles(os.path.join(sublime.packages_path(), "Witty", "core"), 'nodejs')

			self.intelNode.files['CORENODE_FILE_WITTY'] = CORENODE

			# Load in the json files for node.js
			COREBROWSER = WittyFile(self, 'COREBROWSER', True)
			COREBROWSER.loadFiles(os.path.join(sublime.packages_path(), "Witty", "core"), 'browser')

			self.intelBrowser.files['COREBROWSER_FILE_WITTY'] = COREBROWSER

			# The jar is empty, so start the parser
			self.parseFiles()

	# Try to get restore data previously put on the disk
	def _unpickle(self):

		info('Unpickling project ' + str(self.id) + ' data')

		data = {}

		# @todo: reenable pickling
		return data

		# Load in existing completions previously stored
		try:
			pickleFile = open(self.pickleFileName, 'rb')
			try:
				data = pickle.load(pickleFile)
				pickleFile.close()
			except EOFError:
				warn('Unable to unpickle')
		except FileNotFoundError:
			pass

		return data

	## Get the scope from a specific file
	def getScope(self, filename, scopename):

		fileLanguage = self.getFileLanguage(filename)

		if fileLanguage == 'nodejs':
			intel = self.intelNode
		elif fileLanguage == 'browser':
			intel = self.intelBrowser
		else:
			intel = self.intelNode

		pr('Looking for scope "' + scopename + '" in file ' + filename)
		return intel.getScope(filename, scopename)

class Intel:

	def __init__(self, project, language):

		# The parent project
		self.project = project

		# Create the root scope
		self.root = WittyRoot(self)

		# All the types by name » variable
		self.types = {}

		# Files
		self.files = {}

		# The language
		self.language = language

		self.reset()

	## Reset all the class variables
	def reset(self):

		# The scopes
		self.scopes = []

		# The scopes by filename
		self.scopesByFilename = {}

		# All the variables, no matter the scope
		self.variables = []

		# Globals
		self.globals = []

		# Also reset root (it'll add itself to the scopes)
		self.root.resetIntel()

	# Called after every parse, so every save
	def postParse(self):

		# Reset everything
		# @todo: we could make it only reset the currently saved file,
		# but I haven't noticed any speed problems yet, so I'll do it later
		self.reset()
		info('Witty data has been reset, processing data ...')

		# Begin the real work
		for filename, wittyFile in self.files.items():

			pr('Processing ' + filename)

			# Disable json file loads
			#if not filename.endswith('.js'): continue

			pr(wittyFile)

			# Prepare all the scopes
			# Here, we assume the file itself is also a scope
			# That's kind-of true for node.js, but false for javascript
			fileScope = self.root.addChildScope(wittyFile)
			fileScope.setName(filename)
			fileScope.makeFileScope(True)

			# Make a temporary map of the scopes inside this file
			scopeMap = {1: fileScope}

			# Loop over every scope
			for scope in wittyFile.scopes:

				# Skip the first 2 scopes
				if scope['id'] < 2:
					continue

				# Get this scope's parent scope
				parentScope = scopeMap[scope['parent']]
				
				newScope = parentScope.addChildScope()
				newScope.setName(scope['name'])
				newScope.setIdInFile(scope['id'])

				scopeMap[scope['id']] = newScope

			#for statement in wittyFile.statements:
			#	pr('Adding statement ' + statement.typeName + ' from line ' + str(statement.lineNr) + ' to scope ' + str(statement.scopeId))

			for statement in wittyFile.statements:
				# Get the statement's scope
				statementScope = scopeMap[statement.scopeId]
				statementScope.addVariable(statement)

			for scope in wittyFile.scopes:
				if scope['id'] == 0:
					targetScope = self.root
				else:
					targetScope = scopeMap[scope['id']]

				for name, varinfo in scope['variables'].items():
					targetScope.addVariable(False, varinfo)

				wf.log(scope, 'witty-' + self.language + '-simplescopes', True)

			for i, scope in scopeMap.items():
				wf.log(scope, 'witty-' + self.language + '-WTScopes')

			self.registerTypes()

		# for name, file in self.files.items():
		# 	wf.log('\n\nFILENAME: "' + name + '"', 'witty-final-variables')
		# 	wf.log('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n'*3, 'witty-final-variables')
			
		for scope in self.scopes:
			wf.log('\n\n>>\nScope: ' + str(scope.name), 'witty-' + self.language + '-final-variables')
			wf.log((('>>>'*20) + '\n')*2, 'witty-' + self.language + '-final-variables')
			wf.log(scope.variables, 'witty-' + self.language + '-final-variables', True)



	## Register all the types
	#  @param   self        The object pointer
	def registerTypes(self):

		# Reset the types
		self.types = {}

		# Register all the new types
		for variable in self.variables:

			if variable.statement and variable.statement.hasAttribute('typename'):

				# Register them for every name given
				for name in variable.statement.name:
					# Only add not-already-existing types
					if not name in self.types:
						# @todo: apparently names like 'age) {' are still captured!
						# That should be fixed (but not here)
						self.types[name] = variable

	## Add a WittyVariable to the given scope without making a fuss
	#  @param   self        The object pointer
	#  @param   statement   A WittyStatement
	#  @param   variable    The variable
	#  
	#  @returns newVar
	def createEmptyVariable(self):

		# Create the new variable
		newVar = WittyVariable()

		# Set the id
		newVar.id = len(self.variables)

		# Store it among ALL the variables
		self.variables.append(newVar)

		return newVar

	## Get the scope from a specific file
	#  @param   self        The object pointer
	#  @param   filename    The filename the scope should be in
	#  @param   scopename   The 'name' of the scope (fileline)
	def getScope(self, filename, scopename):
		if not filename in self.scopesByFilename:
			wf.warn('File "' + filename + '" was not found while looking for scope "' + scopename + '"')
			return False
		else:
			pr('Filename scopes:')
			for scope in self.scopesByFilename[filename]:
				pr(scope.__dict__)
				if scope.name == scopename:
					return scope

	## Register the scope
	def registerScope(self, scope):

		# Get the new id for this scope
		scope.id = len(self.scopes)

		# And now add this scope to the project
		self.scopes.append(scope)

		# And add it to the scopes by filename
		if not scope.parentFile.name in self.scopesByFilename:
			self.scopesByFilename[scope.parentFile.name] = []

		self.scopesByFilename[scope.parentFile.name].append(scope)


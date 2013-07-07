import sublime, sublime_plugin, os, re, threading, json, pickle, imp, copy
import Witty.library.functions as wf
import Witty.library.Docblock as Docblock
from os.path import basename

# For development purposes
settings = sublime.load_settings("Preferences.sublime-settings")

# Witty only completions?
wittyOnly = settings.get('wittyonly')

if settings.get('env') == 'dev':
	# This forces a reload of the modules
	imp.reload(Docblock)
	imp.reload(wf)

# Debug wrappers
def warn(message, showStack = True): wf.warn(message, showStack, 3)
def info(message, showStack = True): wf.info(message, showStack, 3)
def pr(message, showStack = True): wf.pr(message, showStack, 3)

# Remove all the types of a certain file
def clear_types_file(filename):
	for key, value in allTypes.items():
		if value['filename'] == filename:
			del allTypes[key]

# Is something an array?
is_array = lambda var: isinstance(var, (list, tuple))

# All the open projects
allProjects = {}

# The single point of contact for a project
class Spoc:

	def __init__(self):
		pass


# A Content File
class FileContent:

	def __init__(self, project, fileName):

		# The project we're modifying
		self.project = project

		# The filename
		self.fileName = fileName
		self.name = fileName

		# Open the original file
		fileHandle = open(fileName, 'rU')

		# Read in the original file
		self.original = fileHandle.read()

		# Close the file
		fileHandle.close()

		# Set the working string to empty
		self.working = ''

		# Create the statements
		self.textStatements = []
		self.statements = []

		# Create the scopes
		self.scopes = []
		self.scopeDocBlocks = {}

		# First we add an empty scope because 0 == False and all
		self.createNewScope('global', False)
		self.createNewScope('root', 0)

		# Empty the blocks
		self.blocks = []

		self.root = {}

		# Parse the file
		self.parseFile()

		# Begin the second stage
		self.secondStage()

		wf.log(self.scopes, 'scopes')
		wf.log({fileName: self.textStatements, 'scopes': self.scopes})

	# Begin parsing this file
	def parseFile(self):

		# Find all the docblocks in the original string
		match = wf.reBlocks.findall(self.original)

		self.blocks = []

		if (match):
			for match_tupple in match:
				self.blocks.append(match_tupple[0])

		# Remove all single line comments
		self.working = re.sub(wf.reComment, '', self.original)

		# Replace all the existing docblocks with a placeholder for easy parsing
		self.working = re.sub(wf.reBlocks, '//DOCBLOCK//', self.working)

		# Recursively parse all the statements
		statements = self.parseStatements(self.working, self.blocks)

		self.textStatements = statements

		return self.blocks

	# Create a new scope, return its ID
	def createNewScope(self, name, parentScope, docBlock = ''):
		newId = len(self.scopes)
		self.scopes.append({'id': newId, 'name': name, 'parent': parentScope, 'variables': {}, 'level': 0})

		self.scopeDocBlocks[newId] = docBlock

		workingScope = self.scopes[newId]

		# Determine the level of this scope
		while workingScope['parent']:
			self.scopes[newId]['level'] += 1
			workingScope = self.scopes[workingScope['parent']]

		return newId

	# Parsing statements begins here
	def parseStatements(self, workingLines, docblocks, scopeId = 1, blockType = '', ignoreFirstNewBlock = False):

		# Turn the text into an array of lines
		if not is_array(workingLines):
			workingLines = workingLines.split('\n')

		# Initial value: no statement is open
		statementIsBusy = False

		statements = []

		dbcount = 0
		dbnow = False

		# The running statement
		s = {}
		w = ''

		for line in workingLines:

			strippedLine = line.strip()

			# If the line is empty, continue to the next line
			if len(strippedLine) == 0:
				continue

			# If it's a docblock, keep it for the next statement!
			if strippedLine == '//DOCBLOCK//':
				dbnow = docblocks[dbcount]
				dbcount += 1
				continue

			# Do we need to create a new statement or is one already busy?
			if not statementIsBusy:
				s = {'docblock': '', 'line': '', 'docblocks': [], 'multiline': False, 'scope': scopeId}
				s['line'] = [strippedLine]
				w = line
			else:
				s['multiline'] = True
				s['line'].append(strippedLine)
				w += ' ' + line

			# If the statement is not busy (this includes if a statement is BEGINNING, even if it doesn't end)
			if dbnow:
				if not statementIsBusy:
					s['docblock'] = dbnow
				else:
					s['docblocks'].append(dbnow)

				# Reset the dbnow
				dbnow = False

			# Now see if the statement is finished
			oBracket = w.count('{')
			cBracket = w.count('}')

			if not ignoreFirstNewBlock and oBracket > cBracket:
				statementIsBusy = True
			else:
				statementIsBusy = False
				statements.append(s)
				ignoreFirstNewBlock = False

		results = []
		previousStatement = None

		for stat in statements:
			newStat = self.parseStat(stat, scopeId, previousStatement, blockType, ignoreFirstNewBlock)
			results.append(newStat)

			# Store this new statement as the previous statement,
			# so we can pass it on next time
			previousStatement = newStat

		return statements

	## Find some additional information on a single line
	#  @param   self                The object pointer
	#  @param   statement           A primitive statement object
	#  @param   scopeId             The id of the scope it's in (id in the file)
	#  @param   blockType           What kind of block it's in
	#  @param   ignoreFirstNewBlock If the first line contains a block, ignore it
	def parseStat(self, statement, scopeId, previousStatement, blockType = '', ignoreFirstNewBlock = False):

		# Guess what a line is all about
		temp = self.guessLine(statement['line'][0], previousStatement)

		statement['insideBlock'] = blockType

		# Append the line info to the statement
		for name, value in temp.items():
			statement[name] = value

		# If the statement is a multiline, but we should NOT ignore the first new block
		if not ignoreFirstNewBlock and statement['multiline']:
			
			# We don't need a clone anymore
			#temp = statement['line'][:]

			temp = statement['line']

			# If this is a new function, everything under it is in a new scope
			if statement['function']:

				statement['subscope'] = self.parseStatements(temp, statement['docblocks'], self.createNewScope(temp[0], scopeId, statement['docblock']), 'function', True)
			else:
				newBlock = ''
				temp = re.sub(' ', '', temp[0])
				if temp.count('={'):
					newBlock = 'object'
				elif temp.count('if('):
					newBlock = 'if'
				elif temp.count('=['):
					newBlock = 'array'
				elif temp.count('switch'):
					newBlock = 'switch'

				statement['subblock'] = self.parseStatements(temp, statement['docblocks'], scopeId, newBlock, True)
		
		return statement

	# All the statements have been parsed, now we'll objectify them
	def secondStage(self):
		results = []

		# Recursively go through all the statements in this file
		self.recurseStatObj(self.textStatements)

		# Now do all the scope docblocks
		for scope in self.scopes:
			docblock = Docblock.Docblock(self.scopeDocBlocks[scope['id']])

			# @todo: properties!
			properties = docblock.getProperties()

			# params
			params = docblock.getParams()

			for pName, pValue in params.items():
				scope['variables'][pName] = pValue

	def recurseStatObj(self, statements, parentStatement = False):
		for stat in statements:
			# Create a Statement instance
			tempObject = WittyStatement(self.scopes, self.fileName, stat, parentStatement)

			# Append it to the statements array
			self.statements.append(tempObject)

			wf.log(tempObject, 'statements')

			# Now recursively do the subblocks and subscopes
			if 'subscope' in stat:
				self.recurseStatObj(stat['subscope'], tempObject)

			if 'subblock' in stat:
				self.recurseStatObj(stat['subblock'], tempObject)

	## Guess what a statement does (assignment or expression) and to what variables
	#  @param   self               The object pointer
	#  @param   text               The text to guess
	#  @param   previousStatement  The previous statement (instance of WittyStatement)
	def guessLine(self, text, previousStatement):
		result = {'type': 'expression', 'variables': [], 'function': False, 'value': '', 'info': {}, 'declaration': False}

		text = re.sub('!==', '', text)
		text = re.sub('!=', '', text)

		eqs = text.count('=')

		result['function'] = wf.isFunctionDeclaration(text)

		# If there are no equal signs, it could be an expression by default
		if text.count('var ') == 0 and eqs == 0:

			# See if it's a named function...
			if result['function']:

				# Get the function name, if it has one
				match = wf.reFnName.match(text)

				if match and match.group(1):

					result['info']['name'] = match.group(1)

					# If this line is NOT a function call (so the given function is not a parameter)
					if not wf.isFunctionCall(text):
						result['type'] = 'assignment'
						result['variables'].append(match.group(1))
						result['declaration'] = True

		else:
			# Count the equal signs part of comparisons
			comparisons = text.count('===') * 3

			# Remove the triple equals
			temp = re.sub('===', '', text)

			# Count the equals
			comparisons += temp.count('==') * 2
			
			# If all the equal signs are part of comparisons, return the result
			# @todo: equal signs part of a string will throw this of!
			if not eqs == comparisons:

				temp = text

				if temp.count('var '):
					result['declaration'] = True
					# Replace possible 'var' text
					temp = re.sub('var ', '', temp)
				else:
					# Maybe this is a multiline declaration?
					if previousStatement and previousStatement['declaration'] and previousStatement['line'][0].strip().endswith(','):
						result['declaration'] = True


				# Split the value we're assigning of
				split = temp.rsplit('=', 1)

				# Replace all strings so there are no more ' or "
				temp = re.sub(wf.reStrings, '__WITTY_STRING__', temp)

				# Split them by the comma
				declarations = temp.rsplit(',')

				for dec in declarations:
					dec = dec.strip()
					dec = dec.split('=')
					
					varName = dec[0].strip()

					try:
						assignment = dec[1].strip()
					except IndexError:
						assignment = ''
					
					# If dec is an empty string, continue
					if not dec:
						continue

					#print('Found: ' + varName + ' assigned with ' + assignment)

					result['variables'].append(varName)

					# @todo: since we can have multiple declarations per line, this needs to move!
					result['value'] = ''

					# @todo: same with this!
					result['type'] = 'assignment'

		return result

class WittyStatement:

	def __init__(self, scopes, filename, obj, parentStatement = False):

		statement = obj

		thisScope = scopes[obj['scope']]

		# The original line
		self.line = obj['line']

		# The parent statement (the block this is a part of)
		self.parent = parentStatement

		# The filename this statement is in
		self.filename = filename

		# The docblock of this statement
		self.docblock = Docblock.Docblock(obj['docblock'])

		# The type of this statement (assignment or expression)
		self.type = obj['type']

		# The blocktype this statement is in (function, if, switch, ...)
		self.insideBlock = obj['insideBlock']

		# The scope id
		self.scopeId = obj['scope']

		# The scope
		self.scope = scopes[self.scopeId]

		# The possible params (function)
		self.params = {}

		# The possible properties
		self.properties = {}

		# Modified variables
		self.variables = {}

		# If the variable has been declared
		# @todo: This will unfortunately be false if a multiline var is used!
		self.declaration = obj['declaration']

		# If the statement is a function
		self.function = obj['function']

		# The value is everything before the first semicolon
		# If something else comes after that: tough luck
		self.assignee = obj['value'].split(";")[0].strip()

		# Get this statement name, if any
		self.name = self.docblock.getName()

		# Add names found inside the statement
		if 'name' in obj['info']:
			self.name.append(obj['info']['name'])

		if self.type == 'assignment' and obj['function']:
			for name in obj['variables']:
				self.name.append(name)

		# Add all the variables to the scope
		for name in obj['variables']:
			tempName = name.replace('[\'', '.')
			tempName = tempName.replace('\']', '')

			#@todo: What to do with things like [i] or ['zever_'.i]

			pieces = tempName.split('.')

			workingPiece = self.variables

			for index, piece in enumerate(pieces):
				# If this is the first piece, it's the var name
				if index == 0:
					if not piece in self.variables:
						self.variables[piece] = {'name': piece, 'properties': {}}
					workingPiece = self.variables[piece]
				else:
					if not piece in workingPiece['properties']:
						workingPiece['properties'][piece] = {'name': piece, 'properties': {}}
		
			#thisScope['variables'][name] = {'type': '?', 'name': name, 'description': ''}

		# These should not be added to this scope, but the child scope
		#self.properties = self.docblock.getProperties()
		#self.params = self.docblock.getParams()

		#for pName, pValue in self.params.items():
		#	thisScope['variables'].append(pName)

	## Get a statement docblock attribute
	def getAttribute(self, attributeName):
		return self.docblock.getAttribute(attributeName)

	## See if a docblock attribute is present
	def hasAttribute(self, attributeName):
		return self.docblock.hasAttribute(attributeName)


class WittyParser(threading.Thread):

	def __init__(self, project, originFile): # collector, origin_file, open_folder_arr, timeout_seconds, globalCompletions):
		self.project = project
		self.originFile = originFile
		threading.Thread.__init__(self)

	# Get all javascript files (ending with .js, not containing .min.)
	def getJavascriptFiles(self, dir_name, *args):
		fileList = []
		for file in os.listdir(dir_name):
			dirfile = os.path.join(dir_name, file)
			if os.path.isfile(dirfile):
				fileName, fileExtension = os.path.splitext(dirfile)
				if fileExtension == ".js" and ".min." not in fileName:
					fileList.append(dirfile)
			elif os.path.isdir(dirfile):
				fileList += self.getJavascriptFiles(dirfile, *args)
		return fileList

	# Parse the given file and return a new FileContent object or False
	def startFileParse(self, fileName):

		if not wf.isJavascriptFile(fileName):
			return False

		# If the filename is already present,
		# and it's not the file we just saved, skip it
		if self.project.hasFileData(fileName) and fileName != self.originFile:
			return False

		nmCount = fileName.count('node_modules')
		mvcCount = fileName.count('alchemymvc')

		# Skip node_module files (except for alchemy)
		if nmCount and not mvcCount:
			return False
		elif nmCount > 1 and mvcCount:
			return False
		else:
			sublime.status_message('Witty is parsing: ' + fileName)
			info('Parsing file "' + fileName + '"')

			fileResult = FileContent(self.project, fileName)

			# If we got a new FileContent instance, store it in the project
			if fileResult:
				self.project.intel.files[fileName] = fileResult

	# Function that begins the thread
	def run(self):
		
		# Loop through every folder in the project
		for folder in self.project.folders:
			# Get all the javascript files in the project
			jsFiles = self.getJavascriptFiles(folder)
			for fileName in jsFiles:
				self.startFileParse(fileName)

		sublime.status_message('Witty has finished parsing')

		# Fire the postParse function
		self.project.intel.postParse()

		# Store the data on disk
		self.project.storeOnDisk()

class Intel:

	def __init__(self, project):

		# The parent project
		self.project = project

		# Create the root scope
		self.root = WittyRoot(self)

		# All the types by name » variable
		self.types = []

		# Files
		self.files = {}

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

			# Prepare all the scopes
			# Here, we assume the file itself is also a scope
			# That's kind-of true for node.js, but false for javascript
			fileScope = self.root.addChildScope(wittyFile)
			fileScope.setName(filename)
			fileScope.makeFileScope(True)

			# Make a temporary map of the scopes inside this file
			scopeMap = {1: fileScope}

			print('there are ' + str(len(wittyFile.scopes)) + ' scopes')

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

			#print(wittyFile.scopes)

			for statement in wittyFile.statements:
				# Get the statement's scope
				statementScope = scopeMap[statement.scopeId]
				statementScope.addVariable(statement)

			self.registerTypes()


	## Register all the types
	#  @param   self        The object pointer
	def registerTypes(self):

		# Reset the types
		self.types = []

		# Register all the new types
		for variable in self.variables:

			if variable.statement.hasAttribute('typename'):

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
			for scope in self.scopesByFilename[filename]:
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


class WittyScope:

	# Every scope has a unique identifier (project-wide)
	id = None

	# Every scope also has an identifier inside the file
	idInFile = None

	# This is not the root scope by default
	root = False

	# Every scope has a 'name'
	name = None

	# Is this a file scope?
	fileScope = False

	# The parent of this scope
	parent = None

	# The file we're in
	parentFile = None

	# What project do we belong to?
	project = None

	# All our child scopes will go here
	scopes = None

	# All variables will end up here
	variables = None

	# Store variables by id here
	variablesById = None

	## Constructor
	#  @param   self         The object pointer
	#  @param   parent       The parent WittyScope
	#  @param   parentFile   The file we're in
	def __init__(self, parent, parentFile):

		# Store the parent
		self.parent = parent

		# Store the file
		self.parentFile = parentFile

		# Store the project
		self.project = parent.project

		self.init()

	## Another constructor for creating new objects
	#  @param   self      The object pointer
	def init(self):
		self.scopes = {}
		self.variables = {}
		self.variablesById = {}

	## Get the root scope
	#  @param   self      The object pointer
	def getRoot(self):
		return self.project.intel.root

	## Add a child scope, and return the new instance
	#  @param   self      The object pointer
	def addChildScope(self, parentFile = False):

		if not parentFile:
			parentFile = self.parentFile

		# Create a new scope with ourselves as parent
		newScope = WittyScope(self, parentFile)

		self.project.intel.registerScope(newScope)

		# Return the new scope
		return newScope

	## Set the scope idInFile, its id inside the file
	#  @param   self     The object pointer
	#  @param   id       The id of the scope inside the file
	def setIdInFile(self, id):
		self.idInFile = id

	## Set the scope 'name'
	#  @param   self     The object pointer
	#  @param   name     The scope name
	def setName(self, name):
		self.name = name

	## Set fileScope value
	#  @param   self          The object pointer
	#  @param   isFileScope   If it's a filescope or not
	def makeFileScope(self, isFileScope):
		self.fileScope = isFileScope

		# Filescopes always have an internal id of 1
		if (self.fileScope):
			self.setIdInFile(1)

	## Get the fileScope
	#  @param   self          The object pointer
	def getFileScope(self):

		if self.fileScope:
			return self
		elif self.parent:
			return self.parent.getFileScope()
		else:
			return False

	## Find a specific variable
	#  @param   self     The object pointer
	#  @param   name     The variable name
	#  @param   local    Only look in this scope?
	def findVariable(self, name, local = False):

		# If the variable is found, return it
		if name in self.variables:
			return self.variables[name]

		# If we should not restrict ourselves to the local scope
		if not local and self.parent:
			return self.parent.findVariable(name)

		return False

	## Get all variables
	#  @param   self     The object pointer
	#  @param   local    Only look in this scope?
	def getAllVariables(self, local = False):

		# Variables we'll be working with
		workingVariables = {}

		# Get the upper variables if local is false
		if not local and self.parent:
			workingVariables = self.parent.getAllVariables()

		# Make a SHALLOW copy of the variables in this scope
		ourVariables = copy.copy(self.variables)

		# Update the upper variables with our variables
		workingVariables.update(ourVariables)

		return workingVariables

	## Register a variable inside this scope
	#  @param   variable   The WittyVariable to register
	def registerVariable(self, variable):

		if not hasattr(variable, 'name'):
			raise Exception("UnNamedVariable")

		# Register it by its id
		self.variablesById[variable.id] = variable

		# Register it by its name
		self.variables[variable.name] = variable


	## Add variables to this scope
	#  @param   self        The object pointer
	#  @param   statement   A WittyStatement
	#  @param   variable    The variable
	def addVariable(self, statement, variable = None):

		# If variable is undefined, use the statement
		if not variable:
			for varName, varInfo in statement.variables.items():
				self.addVariable(statement, varInfo)
			return

		# Has this variable been declared inside this scope?
		declared = statement.declaration

		# Is there an existing variable in upper scopes?
		existingVar = None

		match = wf.reValidNameWithPoints.match(variable['name'])

		if not match:
			return

		# The scope to use later on (self by default)
		useScope = self

		# If this is not a declaration (with var)
		# we must see if it's an existing variable
		# in upper scopes. If it's not, we'll
		# add it to the global or module scope
		if not declared:
			existingVar = self.findVariable(variable['name'])

			# If it's an existing var, add an appearance
			if existingVar:
				existingVar.addAppearance(statement, self)
			else:
				# @todo: In node.js you can't set something to the global by just omitting var
				# So we'll have to find something for that
				# Set the scope to the root scope (global)
				#useScope = self.getRoot()

				# Get the filescope
				useScope = self.getFileScope()

				# If it has not been found, raise an error
				if not useScope: raise Exception('FileScope not found')

		# Create a new empty variable (with the id set)
		newVar = self.project.intel.createEmptyVariable()

		# Set the scope
		newVar.setScope(useScope)

		# Set the statement
		newVar.setStatement(statement)

		# Set the name
		newVar.setName(variable['name'])

		if useScope.root:
			print('Registering "' + variable['name'] +'" to scope "' + str(useScope.name) + '"')

		# Add it to the correct scope
		useScope.registerVariable(newVar)

		return newVar


class WittyRoot(WittyScope):

	# The root scope is always id 0
	id = 0

	# This IS the root scope
	root = True

	def __init__(self, intel):

		# Set the intel
		self.intel = intel

		# Set the parent project
		self.project = intel.project

		# Set the name
		self.name = '::ROOT::'

		# Init
		self.init()

		# Reset the project
		self.resetIntel()

	def resetIntel(self):
		self.intel.scopes = []
		self.intel.scopes.append(self)

class WittyVariable:

	# Every variable has a unique id
	id = None

	# What is the scope of this variable?
	# This does NOT equal to where it was declared
	# As global variables can be declared elsewhere
	scope = None

	# In what statement was this variable declared?
	statement = None

	# Where was this variable used?
	statements = []

	## Constructor
	#  @param   self        The object pointer
	#  @param   statement   The statement of declaration
	#  @param   scope       The parent WittyScope
	# def __init__(self, statement, scope):

	# 	self.scope = scope
	# 	self.statement = statement

	## Set the name of this variable
	#  @param   self        The object pointer
	#  @param   name        The name of the variable
	def setName(self, name):

		match = wf.reValidNameWithPoints.match(name)

		if not match:
			raise Exception('This is not a valid variable name!')

		self.name = name

	## Set the scope
	#  @param   scope       The parent WittyScope
	def setScope(self, scope):
		self.scope = scope

	## Set the statement
	#  @param   statement   The statement of declaration
	def setStatement(self, statement):
		self.statement = statement

	## Indicate the variable was used here
	#  @param   self        The object pointer
	#  @param   scope       The scope where we appeared
	#  @param   statement   The statement where we appeared
	def addAppearance(self, scope, statement):
		self.statements.append(statement)


class WittyProject:

	# WittyProject Constructor
	def __init__(self, folders):

		# Update the final hash
		self.id = wf.generateHash(folders)

		# The pickle filename
		self.pickleFileName = '/dev/shm/wittypickle-' + self.id

		# Store the folders
		self.folders = folders

		# The Single Point Of Contact to get data
		self.intel = None

		# Init the intel
		self._initIntel()
		
	# Begin parsing files
	def parseFiles(self, savedFileName = ''):

		# @todo: the thread can't be stored in this instance,
		# because that breaks pickling
		# Maybe store in an outside global?

		# If a thread is already running: stop it
		#if self._parserThread:
		#	self.__parserThread.stop()
		info('Start parsing "' + savedFileName + '"')

		_parserThread = WittyParser(self, savedFileName)
		_parserThread.start()

	# Is data already available for this file?
	def hasFileData(self, fileName):

		# If data is empty, return false
		if not self.intel:
			return False

		if fileName in self.intel.files:
			return True

		return False

	# Store all the data on disk
	def storeOnDisk(self):
		if self.pickleFileName and self.intel and len(self.intel.files):
			# Pickle data
			pickleFile = open(self.pickleFileName, 'wb')
			pickle.dump(self.intel, pickleFile)
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
			lines.append(view.substr(l).strip())

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

		# Get the better prefix
		brefix = wf.getBetterPrefix(left_line)

		scope = self.getScope(current_file, function_scope)

		if scope:
			completions = []

			variables = scope.getAllVariables()

			for varname, varinfo in variables.items():
				pr(varinfo.__dict__)
				completions.append((varname, varname))

			# INHIBIT_WORD_COMPLETIONS = 8 = Only show these completions
			# INHIBIT_EXPLICIT_COMPLETIONS = 16 = ?
			return (completions, sublime.INHIBIT_WORD_COMPLETIONS)
		else:

			info('Scope "' + function_scope + '" in file ' + current_file + ' was not found')

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
		if jar and len(jar.files):
			self.intel = jar
		else:

			# Create a new intel object
			self.intel = Intel(self)

			# The jar is empty, so start the parser, but return an empty dict
			self.parseFiles()

	# Try to get restore data previously put on the disk
	def _unpickle(self):

		info('Unpickling project ' + str(self.id) + ' data')

		data = {}

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
		pr('Looking for scope "' + scopename + '" in file ' + filename)
		return self.intel.getScope(filename, scopename)



# The Witty entrance
class WittyCommand(sublime_plugin.EventListener):

	_parser_thread = None

	def __init__(self):

		self.allProjects = {}

		for window in sublime.windows():
			newProject = WittyProject(window.folders())
			self.allProjects[newProject.id] = newProject

			info('\n\n', False)
			info('New project created (' + str(newProject.id) + ')')
	
	# Get the project ID based on the view
	def getProjectId(self, view):
		projectFolders = view.window().folders()
		return wf.generateHash(projectFolders)

	# Get the project
	def getProject(self, view):
		projectId = self.getProjectId(view)

		if projectId in self.allProjects:
			return self.allProjects[projectId]
		else:
			return False


	# After saving a file, reparse it
	def on_post_save_async(self, view):
		
		savedFileName = view.file_name()

		if savedFileName.count('Witty.py'):
			return False

		# Get the project
		project = self.getProject(view)

		if project:
			project.parseFiles(savedFileName)

	# Query completions
	def on_query_completions(self, view, prefix, locations):

		project = self.getProject(view)

		if project:
			return project.queryForCompletions(view, prefix, locations)
	
class WittyReindexProjectCommand(sublime_plugin.ApplicationCommand):

	def run(self):
		# This actually gets the wrong window, so it doesn't do anything yet
		open_folder_arr = sublime.windows()[0].folders()
		#if self._parser_thread != None:
		#	self._parser_thread.stop()
		self._parser_thread = WittyParser(self, False, open_folder_arr, 30)
		
		self._parser_thread.start()

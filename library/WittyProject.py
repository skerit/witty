import pickle, sublime, sublime_plugin
import Witty.library.functions as wf
from Witty.library.WittyScope import WittyScope
from Witty.library.WittyScope import WittyRoot
from Witty.library.WittyParser import WittyParser
from Witty.library.WittyVariable import WittyVariable

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

		# If a thread is already running: stop it
		if self.id in parserThreads and parserThreads[self.id]:
			print('Killing running thread')
			parserThreads[self.id]._stop()

		info('Start parsing "' + savedFileName + '"')

		parserThreads[self.id] = WittyParser(self, savedFileName)
		parserThreads[self.id].start()

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

class Intel:

	def __init__(self, project):

		# The parent project
		self.project = project

		# Create the root scope
		self.root = WittyRoot(self)

		# All the types by name » variable
		self.types = {}

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
		self.types = {}

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

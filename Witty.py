import sublime, sublime_plugin, os, re, threading, json, pickle, imp
import Witty.library.functions as wf
import Witty.library.Docblock as Docblock
from os.path import basename

# For development purposes
settings = sublime.load_settings("Preferences.sublime-settings")

if settings.get('env') == 'dev':
	# This forces a reload of the modules
	imp.reload(Docblock)
	imp.reload(wf)

# Remove all the types of a certain file
def clear_types_file(filename):
	for key, value in allTypes.items():
		if value['filename'] == filename:
			del allTypes[key]

# Is something an array?
is_array = lambda var: isinstance(var, (list, tuple))

# All the open projects
allProjects = {}

# All the completions
allCompletions = {}

# All the types
allTypes = {}

# All the globals
allGlobals = {}

# A Content File
class Content:

	def __init__(self, file_name):

		self.file_name = file_name

		# Clear out allCompletions entry for this file
		allCompletions[file_name] = {}

		# Open the original file
		file_handler = open(file_name, 'rU')

		# Read in the original file
		self.original = file_handler.read()

		# Set the working string to empty
		self.working = ''

		# Create the statements
		self.statements = []

		# Create the scopes
		self.scopes = []
		self.scopeDocBlocks = {}

		# First we add an empty scope because 0 == False and all
		self.createNewScope('empty', False)
		self.createNewScope('root', 0)

		# Empty the blocks
		self.blocks = []

		self.root = {}

		# Parse the file
		self.parseFile()

		# Begin the second stage
		self.secondStage()

		# Expose everything
		self.expose()

		wf.log(self.scopes, 'scopes')
		wf.log({file_name: self.statements, 'scopes': self.scopes})

	# Export all the variables out
	def expose(self):
		allCompletions[self.file_name] = self.scopes

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

		self.statements = statements

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

		if not is_array(workingLines):
			# Turn the text into an array of lines
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

		for stat in statements:
			newStat = self.parseStat(stat, scopeId, blockType, ignoreFirstNewBlock)
			results.append(newStat)

		return statements

	# Find some additional information on a single line
	def parseStat(self, statement, scopeId, blockType = '', ignoreFirstNewBlock = False):
		temp = self.guessLine(statement['line'][0])

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
		self.recurseStatObj(self.statements)

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
			testObject = Statement(self.scopes, self.file_name, stat, parentStatement)
			wf.log(testObject, 'statements')

			# Now recursively do the subblocks and subscopes
			if 'subscope' in stat:
				self.recurseStatObj(stat['subscope'], testObject)

			if 'subblock' in stat:
				self.recurseStatObj(stat['subblock'], testObject)

	# Guess what a statement does (assignment or expression) and to what variables
	def guessLine(self, text):
		result = {'type': 'expression', 'variables': [], 'function': False, 'value': '', 'info': {}, 'declaration': False}

		text = re.sub('!==', '', text)
		text = re.sub('!=', '', text)

		eqs = text.count('=')

		result['function'] = wf.isFunctionDeclaration(text)

		# If there are no equal signs, it could be an expresison by default
		if eqs == 0:

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
			if not eqs == comparisons:

				temp = text

				if temp.count('var '):
					result['declaration'] = True
					# Replace possible 'var' text
					temp = re.sub('var ', '', temp)

				# Split the value we're assigning of
				split = temp.rsplit('=', 1)

				variables = wf.reANames.findall(text)
				
				for varname in variables:
					if not varname.count('='):
						result['variables'].append(varname.strip())

				result['value'] = split[1]

				result['type'] = 'assignment'

		return result

class Statement:

	def __init__(self, scopes, filename, obj, parentStatement = False):

		statement = obj
		thisScope = scopes[obj['scope']]

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

		# The value is everything before the first ;
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
		
			print('Var: ' + name)
			print(self.variables)

			#thisScope['variables'][name] = {'type': '?', 'name': name, 'description': ''}

		# These should not be added to this scope, but the child scope
		#self.properties = self.docblock.getProperties()
		#self.params = self.docblock.getParams()

		#for pName, pValue in self.params.items():
		#	thisScope['variables'].append(pName)


class WittyParser(threading.Thread):

	def __init__(self, collector, origin_file, open_folder_arr, timeout_seconds, globalCompletions):
		print('Witty parser is starting...')
		self.collector = collector
		self.timeout = timeout_seconds
		self.origin_file = origin_file
		self.open_folder_arr = open_folder_arr
		self.allCompletions = globalCompletions
		threading.Thread.__init__(self)

	def get_javascript_files(self, dir_name, *args):
		fileList = []
		for file in os.listdir(dir_name):
			dirfile = os.path.join(dir_name, file)
			if os.path.isfile(dirfile):
				fileName, fileExtension = os.path.splitext(dirfile)
				if fileExtension == ".js" and ".min." not in fileName:
					fileList.append(dirfile)
			elif os.path.isdir(dirfile):
				fileList += self.get_javascript_files(dirfile, *args)
		return fileList

	def save_method_signature(self, file_name):

		if not wf.isJavascriptFile(file_name):
			return

		# If the filename is already present,
		# and it's not the file we just saved, skip it
		if file_name in self.allCompletions and file_name != self.origin_file:
			return

		nmCount = file_name.count('node_modules')
		mvcCount = file_name.count('alchemymvc')

		# Skip node_module files (except for alchemy)
		if nmCount and not mvcCount:
			return
		elif nmCount > 1 and mvcCount:
			return
		else:
			sublime.status_message('Witty is parsing: ' + file_name)
			results = Content(file_name)

	def run(self):
		#self.save_method_signature('/home/skerit/Projecten/alchemy-skeleton/node_modules/alchemymvc/lib/class/model.js')
		#return
		for folder in self.open_folder_arr:
			jsfiles = self.get_javascript_files(folder)
			for file_name in jsfiles:
				self.save_method_signature(file_name)

		sublime.status_message('Witty has finished parsing')

		if len(self.allCompletions):
			# Pickle data
			pfile = open('/dev/shm/wittypickle', 'wb')
			pickle.dump(self.allCompletions, pfile)

class WittyCommand(sublime_plugin.EventListener):

	_parser_thread = None

	def __init__(self):

		global allProjects
		global allCompletions

		for window in sublime.windows():
			identifier = ''
			for foldername in window.folders():
				identifier += foldername

			allProjects[identifier] = {}

		# Load in existing completions previously stored
		try:
			pfile = open('/dev/shm/wittypickle', 'rb')
			try:
				allCompletions = pickle.load(pfile)
			except EOFError:
				print('Unable to unpickle')
		except FileNotFoundError:
			pass

	def on_post_save_async(self, view):
		if view.file_name().count('Witty.py'):
			return False
		open_folder_arr = view.window().folders()
		#if self._parser_thread != None:
		#	self._parser_thread.stop()
		self._parser_thread = WittyParser(self, view.file_name(), open_folder_arr, 30, allCompletions)
		
		self._parser_thread.start()

	def on_modified(self, view):
		# This runs on every keypress
		#print("Testing on_modified")
		#view.show_popup_menu(["moeder"], False)
		return None

	def on_query_context(self, view, key, operator, operand, match_all):
		return None

	def on_query_completions(self, view, prefix, locations):
		global allCompletions
		current_file = view.file_name()

		if not wf.isJavascriptFile(current_file):
			return

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
			function_scope = 'root'

		# Get the current line
		full_line = view.substr(view.line(region))

		# Get the line up to the cursor
		left_line = full_line[:col].strip()

		# Get the line after the cursor
		right_line = full_line[col:].strip()

		# Get the better prefix
		brefix = wf.getBetterPrefix(left_line)

		try:
			scopes = allCompletions[current_file]
		except KeyError:
			print('Key not found: ' + current_file)
			return
		
		# Default to the first scope
		found_scope = scopes[1]

		for s in scopes:
			if s['name'] == function_scope:
				found_scope = s
				break;

		hierarchy = [found_scope]
		workingScope = found_scope

		# Determine the level of this scope
		while workingScope['parent']:
			workingScope = scopes[workingScope['parent']]
			hierarchy.insert(0, workingScope)

		#print('>>> found scope:')
		#print(function_scope)

		completions = []
		temp = []
		
		for s in hierarchy:

			if not len(s['variables']):
				continue

			# First order the variables
			myvars = []
			keys = list(s['variables'].keys())
			keys.sort()

			#print(keys)

			for k in keys:
				myvars.append(s['variables'][k])

			# Then add them to the autocomplete list
			for v in myvars:
				completions.insert(0, (v['name'] + '\t' + v['type'], v['name']))

		sublime.status_message('Auto completing "' + brefix + '"')

		# INHIBIT_WORD_COMPLETIONS = 8 = Only show these completions
		# INHIBIT_EXPLICIT_COMPLETIONS = 16 = ?
		return (completions, sublime.INHIBIT_WORD_COMPLETIONS)
	
class WittyReindexProjectCommand(sublime_plugin.ApplicationCommand):

	def run(self):
		# This actually gets the wrong window, so it doesn't do anything yet
		open_folder_arr = sublime.windows()[0].folders()
		#if self._parser_thread != None:
		#	self._parser_thread.stop()
		self._parser_thread = WittyParser(self, False, open_folder_arr, 30)
		
		self._parser_thread.start()

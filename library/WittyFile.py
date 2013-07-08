import re
import Witty.library.functions as wf
from Witty.library.WittyStatement import WittyStatement
from Witty.library.Docblock import Docblock

# Debug wrappers
def warn(message, showStack = True): wf.warn(message, showStack, 3)
def info(message, showStack = True): wf.info(message, showStack, 3)
def pr(message, showStack = True): wf.pr(message, showStack, 3)

class WittyFile:

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
		self.docblocks = []

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
		docblocks = wf.reBlocks.findall(self.original)

		self.docblocks = []

		if (docblocks):
			for match_tupple in docblocks:
				self.docblocks.append(match_tupple[0])

		# Remove all single line comments
		self.working = re.sub(wf.reComment, '', self.original)

		# Replace all the existing docblocks with a placeholder for easy parsing
		self.working = re.sub(wf.reBlocks, '//DOCBLOCK//', self.working)

		# Recursively parse all the statements
		statements = self.parseStatements(self.working, self.docblocks)

		self.textStatements = statements

		return self.docblocks

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

	## Turn text into an array of objects
	#  @param   self          The object pointer
	#  @param   workingLines
	def convertText(self, workingLines):

		# Do nothing if it's already an array
		if wf.is_array(workingLines):
			if len(workingLines):
				# If we're dealing with an array of strings
				if isinstance(workingLines[0], str):
					beginArray = workingLines
				else:
					return workingLines
			else:
				return workingLines
		else:
			beginArray = workingLines.split('\n')


		resultArray = []

		# Line numbers start at 1
		originalLineCount = 1

		# Our internal docblock starts at zero
		docblockCount = 0

		for line in beginArray:

			# Our current line length is 1 line by default
			# This is not the amount of characters in one line
			# but some lines continue on other lines
			currentLineLength = 1

			# Skip empty lines
			if line:

				# Use the default newline adding
				addDefaultNewline = True

				newLine = {}
				newLine['linenr'] = originalLineCount
				newLine['text'] = False
				newLine['docblock'] = False
				
				# Get the original line nr
				if line == '//DOCBLOCK//':

					docblock = self.docblocks[docblockCount]
					newLine['docblock'] = docblock

					currentLineLength += docblock.count('\n')

					text = False

					# Go to the next docblock for next iteration
					docblockCount += 1
				else:
					text = line.strip()
					stats = wf.splitStatements(text)

					# If there is just one statement, add that
					if len(stats) == 1:
						newLine['text'] = text
					else:
						# If there is more than 1, or none...
						
						addDefaultNewline = False

						for p in stats:
							subLine = {}
							subLine['linenr'] = originalLineCount
							subLine['text'] = p
							subLine['docblock'] = False
							# @todo: this is true for every statement but the last, probably!
							subLine['length'] = 1
							resultArray.append(subLine)

				newLine['linenr'] = originalLineCount
				newLine['length'] = currentLineLength

				# Append the new line object to the result array
				if addDefaultNewline:
					resultArray.append(newLine)

			# Increate the original linecount
			originalLineCount += currentLineLength

		return resultArray

	# Parsing statements begins here
	def parseStatements(self, workingLines, docblocks, scopeId = 1, blockType = '', ignoreFirstNewBlock = False):

		# Turn the text into an array of line objects
		workingLines = self.convertText(workingLines)

		pr(workingLines)

		# Initial value: no statement is open
		statementIsBusy = False

		statements = []

		dbnow = False

		# The running statement
		s = {}
		w = ''

		for lineObject in workingLines:

			strippedLine = lineObject['text']

			# If it's a docblock, keep it for the next statement!
			if lineObject['docblock']:
				dbnow = lineObject['text']
				continue

			# Do we need to create a new statement or is one already busy?
			if not statementIsBusy:
				s = {'docblock': '', 'line': '', 'docblocks': [], 'multiline': False, 'scope': scopeId}
				s['line'] = [strippedLine]
				w = strippedLine
			else:
				s['multiline'] = True
				s['line'].append(strippedLine)
				w += ' ' + strippedLine #originally line

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
			docblock = Docblock(self.scopeDocBlocks[scope['id']])

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
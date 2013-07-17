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

		# Empty the blocks
		self.docblocks = []

		# Create the scopes
		self.scopes = []
		self.scopeDocBlocks = {}

		# First we add an empty scope because 0 == False and all
		self.createNewScope('global', False)
		self.createNewScope('root', 0)

		self.root = {}

		self.parse()

		# Begin the second stage
		#self.secondStage()

		wf.log(self.scopes, 'scopes')
		wf.log({fileName: self.textStatements, 'scopes': self.scopes})

	## Start parsing the file
	def parse(self):

		# Recursively parse all the statements
		self.textStatements = self.parseStatements(self.original, self.docblocks)

	# Parsing statements begins here
	def parseStatements(self, workingLines, docblocks, scopeId = 1):

		# Turn the text into an array of line objects
		workingLines = wf.splitStatements(workingLines)

		#pr(workingLines)
		wf.log(workingLines, 'wittystats')

		statements = []

		dbnow = False

		# The running statement
		s = {}

		for lineObject in workingLines:

			# If it's a docblock, keep it for the next statement!
			if lineObject['typeName'] == 'docblock':
				dbnow = lineObject['result']
				continue

			# Set the docblock
			lineObject['docblock'] = dbnow
			dbnow = False

			# Set the scope id
			lineObject['scopeId'] = scopeId

			statements.append(lineObject)

		previousStatement = None

		for stat in statements:
			#newStat = self.parseStat(stat, scopeId, previousStatement)

			# Store this new statement as the previous statement,
			# so we can pass it on next time
			previousStatement = stat

		wf.log(statements, 'wittytwo')

		return statements

	## Find some additional information on a single line
	#  @param   self                The object pointer
	#  @param   statement           A primitive statement object
	#  @param   scopeId             The id of the scope it's in (id in the file)
	def parseStat(self, statement, scopeId, previousStatement):

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
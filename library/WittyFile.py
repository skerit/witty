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

		# The array
		self.fileArray = self.original.split('\n')

		# Close the file
		fileHandle.close()

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

		# Recursively split all the statements
		splitStatements = wf.splitStatements(self.original, 1)
		self.objStatements = self.parseStatements(splitStatements, 1)

		wf.log(self.scopes, 'scopes')
		wf.log({fileName: splitStatements, 'scopes': self.scopes})
		wf.log(self.objStatements, 'witty-objstatements')

		# Recursively go through all the statements in this file
		for stat in self.objStatements:
			WittyStatement(self, stat)

		for s in self.statements:
			wf.log(s, 'witty-statements')


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
			docblock = statement['docblock']

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
				# @todo: the statement docblock is currently the only docblock we store
				# expressions can't have docblocks yet
				self.parseStatement(f, self.createNewScope(statement['line'], scopeId, docblock))
		
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
		
		pr('CREATING NEW SCOPE:')
		pr(name)
		pr('<<<<<<<<<<<<<<<')

		self.scopes.append({'id': newId, 'name': name, 'parent': parentScope, 'variables': {}, 'level': 0})

		self.scopeDocBlocks[newId] = docBlock

		workingScope = self.scopes[newId]

		# Determine the level of this scope
		while workingScope['parent']:
			self.scopes[newId]['level'] += 1
			workingScope = self.scopes[workingScope['parent']]

		return newId
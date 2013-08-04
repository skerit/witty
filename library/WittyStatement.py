import Witty.library.functions as wf
from Witty.library.Docblock import Docblock

# Debug wrappers
def warn(message, showStack = True): wf.warn(message, showStack, 3)
def info(message, showStack = True): wf.info(message, showStack, 3)
def pr(message, showStack = True): wf.pr(message, showStack, 3)

class WittyStatement:

	def __init__(self, parentfile, obj):

		parentfile.statements.append(self)
		
		self.statement = obj
		self.parentfile = parentfile

		# The original line nr
		self.lineNr = obj['line']

		# The parent statement (the block this is a part of)
		#self.parent = parentStatement

		# The filename this statement is in
		self.filename = parentfile.fileName

		# The docblock of this statement
		self.docblock = Docblock(obj['docblock'])

		# The type of this statement (assignment or expression)
		self.type = obj['openType']

		# The type name
		self.typeName = obj['openName']

		# The scope id
		self.scopeId = obj['scopeId']

		# The scope
		self.scope = parentfile.scopes[self.scopeId]

		# The possible params (function)
		self.params = {}

		# The possible properties
		self.properties = {}

		# Modified variables
		self.variables = {}

		self.process()

		# Add all the variables to the scope
		# for name in obj['variables']:
		# 	tempName = name.replace('[\'', '.')
		# 	tempName = tempName.replace('\']', '')

		# 	#@todo: What to do with things like [i] or ['zever_'.i]

		# 	pieces = tempName.split('.')

		# 	workingPiece = self.variables

		# 	for index, piece in enumerate(pieces):
		# 		# If this is the first piece, it's the var name
		# 		if index == 0:
		# 			if not piece in self.variables:
		# 				self.variables[piece] = {'name': piece, 'properties': {}}
		# 			workingPiece = self.variables[piece]
		# 		else:
		# 			if not piece in workingPiece['properties']:
		# 				workingPiece['properties'][piece] = {'name': piece, 'properties': {}}
		
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

	def process(self):

		if self.typeName == 'var':
			self.processVar()
		elif self.typeName == 'function':
			self.processFunction()
		elif self.typeName == 'expression':
			self.processExpression()

	def createEmpty(self, name, type):
		return {'name': name, 'type': type, 'docblock': None, 'declared': False, 'value': None}

	def addNewVar(self, name, type = None):

		newVar = self.createEmpty(name, type)
		self.variables[name] = newVar

		return newVar

	def processExpression(self):
		# If it's not an assignment, just ignore it
		if not self.statement['result']['assignment']:
			return

		# Get the raw expression
		expression = wf.normalizeExpression(self.statement['result']['text'])

		pr(">> Expression name:")
		pr(expression)


	# Process a var statement
	def processVar(self):

		# Go over every assignment
		for index, entry in enumerate(self.statement['result']):

			newVar = self.addNewVar(entry['name']['name'], 'undefined')

			# Since we used the var statement, it's declared
			newVar['declared'] = True

			if '=' in entry and 'expression' in entry:
				# @todo: what goes on in this expression?
				newVar['value'] = entry['expression']

			if entry['docblock']:

				newVar['docblock'] = Docblock(entry['docblock'])
				dbtype = newVar['docblock'].getType()
				if dbtype:
					newVar['type'] = dbtype


	# Process a function statement
	def processFunction(self):

		result = self.statement['result'][0]

		# Add the function variable to this scope
		if 'name' in result:
			newVar = self.addNewVar(result['name']['name'], 'Function')
			newVar['declared'] = True

		# Create a new statement for inside the next scope
		scopeStat = WittyStatement(self.parentfile, {
			'line': self.lineNr,
			'docblock': None,
			'openType': 'scope',
			'openName': 'scope',
			'scopeId': self.statement['subscopeId'],
			})

		# Process variable in the parens,
		# Add them to the subscope
		parenVars = result['paren']['content'].split(',')
		for varName in parenVars:

			# Strip out any spaces or newlines
			varName = varName.strip()

			if varName:
				newVar = scopeStat.addNewVar(varName.strip())
				newVar['declared'] = True # Parameters are declared variables

		# Recursively go through all the statements in this file
		for stat in result['block']['parsed']:
			WittyStatement(self.parentfile, stat)

		




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
		return {
			'name': name,
			'type': type,
			'docblock': None,
			'declared': False,
			'value': None,
			'description': None,
			'reference': False,
			'properties': {}
		}

	def touchProperty(self, parent, name, type = None):

		if name in parent['properties']:
			prop = parent['properties'][name]
			if type: prop['type'] = type
		else:
			prop = self.createEmpty(name, type)
			prop['type'] = type
			prop['declared'] = 'property'
			parent['properties'][name] = prop

		return prop

	## Touch a variable, possibly creating it in the process
	#  @param   self           The object pointer
	#  @param   name           The name of the variable
	#  @param   type           The type of the variable
	def touchVar(self, name, type = None):

		if name in self.variables:
			newVar = self.variables[name]
			if type: newVar['type'] = type
		else:
			newVar = self.createEmpty(name, type)
			self.variables[name] = newVar

		# this is always declared
		if name == 'this' or name == 'arguments':
			newVar['declared'] = True

		return newVar

	def processExpression(self):
		# If it's not an assignment, just ignore it
		if not self.statement['result']['assignment']:
			return

		# Get the raw expression
		expression = wf.normalizeExpression(self.statement['result']['text'])

		pr(">> Expression name:")
		pr(expression)
		pr(self.statement)
		targetVar = False

		for target in expression['target']:

			if not 'name' in target:
				pr('Missing name in target:')
				pr(target)
				continue

			targetVar = self.touchVar(target['name'])

			prop = targetVar

			# Now go over every property
			for part in target['parts']:
				prop = self.touchProperty(prop, part['text'])

			# If there's a type, set it to the last prop
			# We don't parse the value yet, so just set it to unknwon
			if prop != targetVar: prop['type'] = 'unknown'

			# If there is a docblock here, set that
			if self.statement['docblock']:
				prop['docblock'] = self.statement['docblock']


	# Process a var statement
	def processVar(self):

		#pr(self.statement)

		# Go over every assignment
		for index, entry in enumerate(self.statement['result']):

			newVar = self.touchVar(entry['name']['name'], 'undefined')

			# Since we used the var statement, it's declared
			newVar['declared'] = True

			if '=' in entry and 'expression' in entry:

				if entry['expression']['functions']:
					self.processFunction(entry['expression']['functions'][0], newVar)
				else:
					# @todo: what goes on in this expression?
					newVar['value'] = entry['expression']

			if entry['docblock']:

				newVar['docblock'] = Docblock(entry['docblock'])
				dbtype = newVar['docblock'].getType()
				if dbtype:
					newVar['type'] = dbtype


	# Process a function statement
	def processFunction(self, result = None, newVar = None):

		if not result:
			result = self.statement['result'][0]

		#if not scopeId:
		#scopeId = self.statement['subscopeId']
		if 'scopeId' in result:
			scopeId = result['scopeId']
		else:
			scopeId = self.statement['subscopeId']

		pr('>>>>>>>>>> Processing function!')

		# Add the function variable to this scope
		if not newVar and 'name' in result:
			newVar = self.touchVar(result['name']['name'], 'Function')
			newVar['declared'] = True

		newVar['type'] = 'Function'

		# Create a new statement for inside the next scope
		scopeStat = WittyStatement(self.parentfile, {
			'line': self.lineNr,
			'docblock': None,
			'openType': 'scope',
			'openName': 'scope',
			'scopeId': scopeId,
			})

		# Process variable in the parens,
		# Add them to the subscope
		parenVars = result['paren']['content'].split(',')

		paraminfo = self.docblock.getParams()

		for varName in parenVars:

			# Strip out any spaces or newlines
			varName = varName.strip()

			if varName:
				parVar = scopeStat.touchVar(varName.strip())
				parVar['declared'] = True # Parameters are declared variables

				if varName in paraminfo:
					parVar['type'] = paraminfo[varName]['type']
					parVar['description'] = paraminfo[varName]['description']

		# Add the function name as a variable to the current scope
		if 'name' in result:
			parVar = scopeStat.touchVar(result['name']['name'])
			parVar['declared'] = True
			parVar['reference'] = newVar['name']

		# Recursively go through all the statements in this file
		for stat in result['block']['parsed']:
			WittyStatement(self.parentfile, stat)

		




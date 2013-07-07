import Witty.library.functions as wf
from Witty.library.Docblock import Docblock

# Debug wrappers
def warn(message, showStack = True): wf.warn(message, showStack, 3)
def info(message, showStack = True): wf.info(message, showStack, 3)
def pr(message, showStack = True): wf.pr(message, showStack, 3)

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
		self.docblock = Docblock(obj['docblock'])

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
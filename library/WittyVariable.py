import Witty.library.functions as wf
from Witty.library.Docblock import Docblock

# Debug wrappers
def warn(message, showStack = True): wf.warn(message, showStack, 3)
def info(message, showStack = True): wf.info(message, showStack, 3)
def pr(message, showStack = True): wf.pr(message, showStack, 3)

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
	statements = None

	# Properties of this variable
	properties = None
	propArray = None

	docblock = None

	## Constructor
	#  @param   self        The object pointer
	#  @param   statement   The statement of declaration
	#  @param   scope       The parent WittyScope
	def __init__(self):
		self.statements = []
		self.propArray = []
		self.properties = {}

	def setDocblock(self, text):
		
		if not text:
			return

		if isinstance(text, Docblock):
			self.docblock = text
		else:
			self.docblock = Docblock(text)

		type = self.docblock.getType()

		if type:
			self.type = type


	def setBase(self, variable):
		self.info = variable
		self.type = variable['type']

		if 'docblock' in variable and variable['docblock']:
			self.setDocblock(variable['docblock'])

		if not self.type or self.type in ['undefined', 'unknown']:

			if variable['value'] and 'result' in variable['value']:
				# See if there is a value assignment
				value = variable['value']['result']['text']

				if not len(value):
					pass # Do nothing if there is no text
				elif value[0] == '"' or value[0] == "'":
					self.type = 'String'
				elif value in ['true', 'false']:
					self.type = 'Boolean'
				elif value[0] == '{':
					self.type = 'Object'
				elif value[0] == '[':
					self.type = 'Array'
				elif value.isdigit():
					self.type = 'Number'
				elif self.scope:
					# See if it's an existing variable somewhere
					existing = self.scope.findVariable(value)

					if existing:
						self.makeReference(existing)

	# Make a reference to another variable
	def makeReference(self, existing):

		if existing.type in ['Function', 'Object', 'Array']:
			self.properties = existing.properties
			self.propArray = existing.propArray

		self.type = existing.type

	## Set the name of this variable
	#  @param   self        The object pointer
	#  @param   name        The name of the variable
	def setName(self, name):

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

	def touchProperties(self, properties):

		for name, prop in properties.items():
			self.addProperty(prop['name'], prop)


	## Add a property to this variable
	def addProperty(self, name, info):

		if name in self.properties:
			prop = self.properties[name]

			# If there is a new type set
			if info['type']:
				prop.type = info['type']

		else:
			prop = WittyVariable()

			# Add some basic info
			prop.id = 0
			prop.setScope(self.scope)
			prop.setStatement(self.statement)

			# Set the name
			prop.setName(name)

			# Set basic info
			prop.setBase(info)

			self.properties[name] = prop
			self.propArray.append(prop)

		if 'properties' in info:
			# Recursively add deeper properties
			prop.touchProperties(info['properties'])
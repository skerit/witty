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

	type = None
	types = None

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

		self.setType(self.docblock.getType())

	def getAttribute(self, name):

		if self.docblock:
			return self.docblock.getAttribute(name)
		else:
			return None

	def setType(self, type):
		if type:
			self.type = type
			self.types = type.split(',')


	## Get the properties of the types
	def getTypeProperties(self):

		# Initial value is empty
		variables = {}

		# Go over every type this variable has
		for typeName in self.types:

			# Don't do ourselves, that'll cause a loop
			if typeName == self.name:
				continue

			# Get the variable for the given type
			typeVar = self.scope.findVariable(typeName)

			# Update the result value with the found prototype properties
			if typeVar: variables.update(typeVar.getPrototypeProperties())
		
		return variables

	def getPrototypeProperties(self, typePrototype = True):
		result = {}

		if 'prototype' in self.properties:
			result = self.properties['prototype'].properties
		
		if typePrototype:
			result.update(self.getTypeProperties())

		return result

	## Get all the properties of this variable
	#  @param   self                     The object pointer
	#  @param   includeTypeProperties    Include the prototypal properties of the type
	def getProperties(self, includeTypeProperties=True):

		pr('Getting properties of ' + self.name)

		variables = {}

		# Now get the prototype properties of the foundVar's type
		if includeTypeProperties and self.types:

			# Create empty object
			variables = self.getTypeProperties()

			pr(self.properties)

			# Now overwrite anything with our own properties
			variables.update(self.properties)
		else:
			if self.properties:
				return self.properties
		
		return variables

	def setBase(self, variable):
		self.info = variable
		self.setType(variable['type'])

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

	## Look for properties inside this variable
	def findProperties(self, properties):

		if isinstance(properties, str):
			properties = properties.split('.')

		if not len(properties):
			return False

		findNext = properties.pop(0)

		if findNext in self.properties:

			if len(properties):
				return self.properties[findNext].findProperties(properties)
			else:
				return self.properties[findNext]

		else:
			return False



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
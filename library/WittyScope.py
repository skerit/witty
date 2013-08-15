import copy
import Witty.library.functions as wf

# Debug wrappers
def warn(message, showStack = True): wf.warn(message, showStack, 3)
def info(message, showStack = True): wf.info(message, showStack, 3)
def pr(message, showStack = True): wf.pr(message, showStack, 3)

class WittyScope:

	# Every scope has a unique identifier (project-wide)
	id = None

	# Every scope also has an identifier inside the file
	idInFile = None

	# This is not the root scope by default
	root = False

	# Every scope has a 'name'
	name = None

	# Is this a file scope?
	fileScope = False

	# The parent of this scope
	parent = None

	# The file we're in
	parentFile = None

	# What project do we belong to?
	project = None

	# All our child scopes will go here
	scopes = None

	# All variables will end up here
	variables = None

	# Store variables by id here
	variablesById = None

	## Constructor
	#  @param   self         The object pointer
	#  @param   parent       The parent WittyScope
	#  @param   parentFile   The file we're in
	def __init__(self, parent, parentFile):

		# Store the parent
		self.parent = parent

		# Store the file
		self.parentFile = parentFile

		# Store the project
		self.project = parent.project

		# Get the parent intel
		self.intel = parent.intel

		self.init()

	## Another constructor for creating new objects
	#  @param   self      The object pointer
	def init(self):
		self.scopes = {}
		self.variables = {}
		self.variablesById = {}

	## Get the root scope
	#  @param   self      The object pointer
	def getRoot(self):
		return self.intel.root

	## Add a child scope, and return the new instance
	#  @param   self      The object pointer
	def addChildScope(self, parentFile = False):

		if not parentFile:
			parentFile = self.parentFile

		# Create a new scope with ourselves as parent
		newScope = WittyScope(self, parentFile)

		self.intel.registerScope(newScope)

		# Return the new scope
		return newScope

	## Set the scope idInFile, its id inside the file
	#  @param   self     The object pointer
	#  @param   id       The id of the scope inside the file
	def setIdInFile(self, id):
		self.idInFile = id

	## Set the scope 'name'
	#  @param   self     The object pointer
	#  @param   name     The scope name
	def setName(self, name):
		self.name = name

	## Set fileScope value
	#  @param   self          The object pointer
	#  @param   isFileScope   If it's a filescope or not
	def makeFileScope(self, isFileScope):
		self.fileScope = isFileScope

		# Filescopes always have an internal id of 1
		if (self.fileScope):
			self.setIdInFile(1)

	## Get the fileScope
	#  @param   self          The object pointer
	def getFileScope(self):

		if self.fileScope:
			return self
		elif self.parent:
			return self.parent.getFileScope()
		else:
			return False

	## Find a specific variable
	#  @param   self     The object pointer
	#  @param   name     The variable name
	#  @param   local    Only look in this scope?
	def findVariable(self, names, local = False):

		# Main variable result
		var = False

		# Split the name
		pieces = names.split('.')

		# Get the first entry in the array, that's the main variable
		name = pieces.pop(0)

		# If the variable is found, return it
		if name in self.variables:
			var = self.variables[name]

		# If we should not restrict ourselves to the local scope
		elif not local and self.parent:
			var = self.parent.findVariable(name)

		if var:
			# If there are more pieces, look deeper
			if len(pieces):
				return var.findProperties(pieces)
			else:
				return var

		return False

	## Find a variable in this or children scopes
	def findVariableDown(self, name, local = False, skipScopeId = False):

		# If the variable is found in this scope, return it
		if name in self.variables:
			return self.variables[name]

		## @todo: Should this go down first and up later?

	## Get all variables
	#  @param   self     The object pointer
	#  @param   local    Only look in this scope?
	def getAllVariables(self, local = False):

		# Variables we'll be working with
		workingVariables = {}

		# Get the upper variables if local is false
		if not local and self.parent:
			workingVariables = self.parent.getAllVariables()

		# Make a SHALLOW copy of the variables in this scope
		ourVariables = copy.copy(self.variables)

		# Update the upper variables with our variables
		workingVariables.update(ourVariables)

		return workingVariables

	## Register a variable inside this scope
	#  @param   variable   The WittyVariable to register
	def registerVariable(self, variable):

		if not hasattr(variable, 'name'):
			raise Exception("UnNamedVariable")

		# Register it by its id
		self.variablesById[variable.id] = variable

		# Register it by its name
		self.variables[variable.name] = variable


	## Add variables to this scope
	#  @param   self        The object pointer
	#  @param   statement   A WittyStatement
	#  @param   variable    The variable
	def addVariable(self, statement, variable = None, defaults = {}):

		# If variable is undefined, use the statement
		if not variable:
			for varName, varInfo in statement.variables.items():
				self.addVariable(statement, varInfo)
			return

		# Has this variable been declared inside this scope?
		if 'declared' in variable:
			declared = variable['declared']
		elif 'declared' in defaults:
			declared = defaults['declared']
		else:
			declared = True

		# Is there an existing variable in upper scopes?
		existingVar = None

		# The scope to use later on (self by default)
		useScope = self

		#pr('Adding variable to scope ' + str(self.id) + ' called "' + variable['name'] + '" declared: ' + str(declared))

		# If this is not a declaration (with var)
		# we must see if it's an existing variable
		# in upper scopes. If it's not, we'll
		# add it to the global or module scope
		if not declared:

			existingVar = self.findVariable(variable['name'])

			# If it's an existing var, add an appearance
			if existingVar:
				existingVar.addAppearance(statement, self)
				# Add possible properties
				existingVar.touchProperties(variable['properties'], statement)
				return existingVar
			else:

				# Create a new empty variable (with the id set)
				newVar = self.intel.createEmptyVariable()

				# In node.js undeclared variables are restricted to the module
				if self.intel.language == 'nodejs':
					useScope = self.getFileScope()
				elif self.intel.language == 'browser':
					useScope = self.getRoot()

				# If it has not been found, raise an error
				if not useScope: raise Exception('Scope not found')
		else:
			existingVar = self.findVariable(variable['name'], True)

			if existingVar:
				newVar = existingVar
			else:
				newVar = self.intel.createEmptyVariable()

		# Set the scope
		newVar.setScope(useScope)

		newVar.setBase(variable)

		# Set the options
		if 'options' in variable:
			newVar.options = variable['options']
		else:
			newVar.options = {}

		# Set the statement
		newVar.setStatement(statement)

		# Add it to the correct scope
		useScope.registerVariable(newVar)

		# Add possible properties
		newVar.touchProperties(variable['properties'])

		return newVar


class WittyRoot(WittyScope):

	# The root scope is always id 0
	id = 0

	# This IS the root scope
	root = True

	def __init__(self, intel):

		# Set the intel
		self.intel = intel

		# Set the parent project
		self.project = intel.project

		# Set the name
		self.name = '::ROOT::'

		# Init
		self.init()

		# Reset the project
		self.resetIntel()

	def resetIntel(self):
		self.intel.scopes = []
		self.intel.scopes.append(self)
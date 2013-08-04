import Witty.library.functions as wf

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
	statements = []

	# Properties of this variable
	properties = {}

	## Constructor
	#  @param   self        The object pointer
	#  @param   statement   The statement of declaration
	#  @param   scope       The parent WittyScope
	# def __init__(self, statement, scope):

	# 	self.scope = scope
	# 	self.statement = statement

	def setBase(self, variable):
		self.info = variable
		self.type = variable['type']

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

	## Add a property to this variable
	def addProperty(self):
		pass
import re
import Witty.library.functions as wf

# Debug wrappers
def warn(message, showStack = True): wf.warn(message, showStack, 3)
def info(message, showStack = True): wf.info(message, showStack, 3)
def pr(message, showStack = True): wf.pr(message, showStack, 3)

# Match descriptions
reDescription = re.compile('\/\*(.*?)[@|\/]', re.M|re.S)

# Docblock properties
reAt = re.compile('^.*?@(\w+)?[ \t]*(.*)', re.M)

#
# The DocBlock class
#
class Docblock:

	def __init__(self, text):
		
		if not text:
			text = ''

		self.original = text
		self.description = self.parseDescription()
		self.properties = self.parseProperties()

	# Get the description inside the given docblock text
	def parseDescription(self):
		text = self.original
		description = reDescription.match(text)

		if description:
			description = description.group(1)
			# Remove the leading stars
			return re.sub('^\s?\*\s?', '', description, 0, re.M|re.S)
		else:
			return False

	# Get all the properties of a docblock
	def parseProperties(self):
		text = self.original
		match = reAt.findall(text)
		properties = {}

		for match_tupple in match:
			property_name = match_tupple[0].lower().strip()

			if not (property_name in properties):
				properties[property_name] = []

			properties[property_name].append(match_tupple[1].strip())

		return properties

	# Get the name property
	def getName(self):
		if 'name' in self.properties:
			return self.properties['name']
		
		return []

	# Get the type property
	def getType(self):
		result = self.getAttribute('type')

		if result:
			result = re.sub('{', '', result)
			result = re.sub('}', '', result)
			result = result.strip()
			
		return result

	# Parse a simple attribute
	def parseAttribute(self, text):

		if isinstance(text, list):
			text = text[0]

		# Remove all double whitespaces
		text = re.sub('\s+', ' ', text)

		return text

	# Parse param/property information
	def parseParam(self, text):
		result = {'type': '', 'name': '', 'description': ''}

		name = ''
		description = ''
		typeName = ''

		# Remove all double whitespaces
		text = re.sub('\s+', ' ', text)

		# Get the type
		temp = text.split(' ', 1)

		try:
			name = temp[1]
		except IndexError:
			# If there is no name, there is no parameter
			return False

		typeName = temp[0]
		result['type'] = re.sub('[\{\}]', '', typeName)

		# Get the name
		temp = name.split(' ', 1)

		try:
			description = temp[1]
		except IndexError:
			pass

		name = temp[0].strip()

		if not len(name):
			return False

		result['name'] = name
		result['description'] = description

		return result

	# Return properties defined in the type-name-description format
	def __getTypes(self, typeName):
		result = {}

		if typeName in self.properties:
			for p in self.properties[typeName]:
				temp = self.parseParam(p)

				if temp:
					result[temp['name']] = temp

		return result

	# Return a single property
	def getAttribute(self, name):
		
		if not name in self.properties:
			return None
		else:
			return self.parseAttribute(self.properties[name])

	# See if this property is present
	def hasAttribute(self, name):
		
		if name in self.properties:
			return True

	# Get the @property properties
	def getProperties(self):
		return self.__getTypes('property')

	# Get the @param properties
	def getParams(self):
		return self.__getTypes('param')
		
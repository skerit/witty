#
# These functions are used throughout the Witty plugin,
# and are mainly for getting information out of code
#
import os, re, threading, pprint, json, pickle, hashlib, inspect, sublime, datetime

doDebug = False

# Is something an array?
def is_array(object):
	return isinstance(object, (list, tuple))


doDebug = False
debugLevel = 1

#
# Regexes
#

# Match docblocks
reBlocks = re.compile('(\/\*(.*?)\*/)', re.M|re.S)

# Match descriptions
reDescription = re.compile('\/\*(.*?)[@|\/]', re.M|re.S)

# Docblock properties
reAt = re.compile('^.*?@(\w+)?[ \t]*(.*)', re.M)

# Simple single-line comments
reComment = re.compile('^\s*\/\/.*', re.M)

# All comments (including comments inside strings!)
reComments = re.compile(r'''[ \t]*(?:\/\*(?:.(?!(?<=\*)\/))*\*\/|\/\/[^\n\r]*\n?\r?)''', re.M)

# Get the function name (not the assigned var!)
reFnName = re.compile('^.*function\s+(\w*?)\s*?\(', re.M)

# Does this line begin with a function call?
reFnCallBegin = re.compile('^\s*(?!\s)[\w\.\[\]]*\w\(', re.M)

# Get assignment variable names
reANames = re.compile('(\S*?)\s*\=(?!\=)', re.M)

# Get declaration pairs
reDeclarations = re.compile('(?= |\,)(\w+)\s*={0,1}\s*.*?(?=,|$)', re.M)

# This works in regexr, but not in python ((?=^| |\,|\,\s+)(\w+)\s*\={0,1}.*?(?=,|$))

reDeclarations = re.compile(r'((?=^| |\,|\,\s+)(\w+)\s*\={0,1}.*?(?=,|$))', re.M)

# Find strings (even with escaped ' and ")
# Regex is actually (?<!\\)(?:(')|")(?(1)(\\'|[^'\r])+?'|(\\"|[^\r"])+?")
reStrings = re.compile(r'''(?<!\\)(?:(')|")(?(1)(\\'|[^'\r])+?'|(\\"|[^\r"])+?")''', re.M|re.X)

# Valid javascript variable name regex,
# this does not include unicode stuff
reValidName = re.compile('^(?!(?:do|if|in|for|let|new|try|var|case|else|enum|eval|false|null|this|true|void|with|break|catch|class|const|super|throw|while|yield|delete|export|import|public|return|static|switch|typeof|default|extends|finally|package|private|continue|debugger|function|arguments|interface|protected|implements|instanceof)$)[a-zA-Z_$][0-9a-zA-Z_$]*$')

# The same as above, but allow points
reValidNameWithPoints = re.compile('^(?!(?:do|if|in|for|let|new|try|var|case|else|enum|eval|false|null|this|true|void|with|break|catch|class|const|super|throw|while|yield|delete|export|import|public|return|static|switch|typeof|default|extends|finally|package|private|continue|debugger|function|arguments|interface|protected|implements|instanceof)$)[a-zA-Z_$][0-9a-zA-Z_$\.]*$')

#
# Log Functions
#

# Prepare the pretty printer
pp = pprint.PrettyPrinter(indent=2)

# Create a dictionary for open files
openFiles = {}

# Generate a hash
def generateHash(data):
	# Prepare the project id hash
	hashId = hashlib.md5()

	# Loop through all the folders to generate a hash
	for folderName in data:
		hashId.update(folderName.encode('utf-8'))

	return hashId.hexdigest()

def dictify(data, level=0):

	if level > 2:
		return data

	upLevel = level + 1

	# If the object is a dictionary
	if isinstance(data, dict):
		tempDict = {}

		for key, value in data.items():
			tempDict[key] = dictify(value, upLevel)

		return tempDict

	# If the object is a list
	if isinstance(data, list):
		tempList = []
		for item in data:
			tempList.append(dictify(item, upLevel))

		return tempList

	# If the object does not have a dict, return it
	try:
		return dictify(data.__dict__, upLevel)
	except AttributeError:
		return data

# Log data to the given file in /dev/shm/ (memory fs)
def log(data, filename='workfile', doDictify=False):

	global openFiles

	if not filename in openFiles:
		openFiles[filename] = open('/dev/shm/' + filename, 'w')

	try:
		if doDictify:
			data = dictify(data)
		else:
			data = data.__dict__

		openFiles[filename].write('\n' + pp.pformat(data)) # data.__dict__
	except AttributeError:
		openFiles[filename].write('\n' + pp.pformat(data))

def color(t, c):
	
	# For sublime just use 'esc' to stand out
	return t + chr(0x1b) + ' '

	# For terminal
	#return chr(0x1b)+"["+str(c)+"m"+t+chr(0x1b)+"[0m"

## Echo something to the console
#  @param   message      The message to print
#  @param   stackLevel   How many functions to skip
def echo(message, showStack = True, stackLevel = 1):

	if showStack:

		# Get the current frame
		frame = inspect.currentframe()

		# Get the outer frame
		outer = inspect.getouterframes(frame)

		# The second element is the calling frame
		caller = outer[stackLevel]

		# Split out the filename
		fileName = caller[1].rsplit('/')
		fileName = fileName[len(fileName)-1]

		# Get the line number
		lineNr = caller[2]

		# Get the caller function name
		callerName = caller[3]

		# Add some color to the stack info
		stackinfo = color('[' + fileName + ':' + str(lineNr) + ' ' + callerName + '] ', 1)

		# And print it out
		print(stackinfo + str(message))
	else:
		print(message)

## Print out a warning to the console (level 1)
#  @param   message      The message to print
def warn(message, showStack = True, stackLevel = 2):

	# If debugLevel is zero, nothing should be shown
	if debugLevel > 0:
		echo(message, showStack, stackLevel)

## Print out info to the console (level 2)
#  @param   message      The message to print
def info(message, showStack = True, stackLevel = 2):

	# Only print if debugLevel is higher than 1
	if debugLevel > 1:
		echo(message, showStack, stackLevel)

## Print out debug message to the console (level 3)
#  @param   message      The message to print
def pr(message, showStack = True, stackLevel = 2):

	# Only print if debugLevel is higher than 2
	if debugLevel > 2:
		echo(message, showStack, stackLevel)

#
# String manipulators / searchers
#

# Is the given file a javascript file?
# Right now, it only checks for .js in the filename
def isJavascriptFile(filename):
	return '.js' in filename

# Does this line contain a function declaration?
def isFunctionDeclaration(text):
	# If there is no function to be found, it definitely isn't one
	if not text.count('function'):
		return False

	# 'function' appears somewhere, but how?

	# Replace all strings with this placeholder
	text = re.sub(reStrings, '"a"', text)

	if text.count('function') > 0:
		return True

	return False

# Is this line a function call? (Does it begin with one)
def isFunctionCall(text):
	match = reFnCallBegin.match(text)

	if match:
		return True
	else:
		return False

# Get a better prefix
def getBetterPrefix(text):

	# Get everything after these chars, in this order
	chars = [' ', '(', ')', '[', ']', '-', '+']

	for needle in chars:
		temp = text.rsplit(needle, 1)

		# If it was found, save it as the result
		try:
			text = temp[1]
		except IndexError:
			pass

	return text

## Remove docblocks from the code and return them in an array
#  @param   text         The original code
#  @returns text,array   Tuple: modified text and docblock array
def extractDocblocks(text):

	# Find all the docblocks in the original string
	docblocks = reBlocks.findall(text)

	resultArray = []
	resultText = ''

	if (docblocks):
		for match_tupple in docblocks:
			resultArray.append(match_tupple[0])

	# Remove all single line comments
	resultText = re.sub(reComment, '', text)

	# Replace all the existing docblocks with a placeholder for easy parsing
	resultText = re.sub(reBlocks, '//DOCBLOCK//', resultText)

	return resultText, resultArray

## Get the characters before, and after the id
#  @param   text   The text
#  @param   id     The current id
def getSurround(text, id, default = ''):

	previous = default
	next = default

	length = len(text)

	# Get the previous character
	if id-1 > -1:
		previous = text[id-1]

	# Get the after character
	if id+1 < length:
		next = text[id+1]

	return previous, next

# Chars
whitespace = [' ', '\n', '\t']

# All the operators
operators = ['+', '=', '-', '*', '/', '%', '<', '>', '~']

# Things that denote expressions
expressionizers = ['+', '=', '-', '*', '/', '%', '<', '>', '~', '(', ',']

# This list is far from finished, just for testing!
wordDelim = [',', ' ', '\n', '\t', '(', ')', '{', '}', '[', ']']

def hasWordAfter(text, word, id = False):
	return hasCharsAfter(text, word, id, True)

def hasCharsAfter(text, word, id = False, checkForSpace = False):

	if id > -1:
		text = text[id:]

	if not text.startswith(word):
		return False
	else:
		# Make sure it's actually a word, not part of something else
		wordlength = len(word)
		maxTextId = len(text)-1

		# Get the chars that should match
		after = text[:wordlength]

		if after == word:

			if checkForSpace:
				extraChar = text[wordlength-1:1]
				if extraChar in wordDelim:
					return True
				else:
					return False
			else:
				return True
		else:
			return False

def getCharAfterId(text, word, id = False, checkForSpace = False):

	isPresent = hasCharsAfter(text, word, id, checkForSpace)

	if not isPresent:
		return False
	else:
		for i, c in enumerate(text):
			if c == word:
				return i


## Find a text before
#  @param   text   The text
#  @param   id     The current position
#  @param   word  The word to find
def hasWordBefore(text, id, word):

	piece = text[:id].strip()

	if not piece.endswith(word):
		return False
	else:
		# Make sure it's actually a word, not part of something else
		wordlength = len(word)
		maxPieceId = len(piece)-1

		# Get the char before the word
		before = text[maxPieceId-wordlength]

		if before == ' ' or before == '\n' or before == '\t' or before == '=':
			return True
		else:
			return False

## Find a character before
def hasCharBefore(text, id, char, ignore = [], ignoreWhitespace = True):

	# If a single char is given, turn it into an array
	if isinstance(char, str):
		char = [char]

	piece = text[:id]

	# Make sure it's actually a word, not part of something else
	maxPieceId = len(piece)-1

	# Get the char before the word
	before = piece[maxPieceId]

	# If the char before is a whitespace...
	if before in whitespace:
		return hasCharBefore(piece, id-1, char, ignoreWhitespace)
	elif before in char:
		return True
	else:
		return False


## Check if id is an opening array literal
def isArrayLiteral(text, id):

	char = text[id]

	if char == '[':
		return hasCharBefore(text, id, ['+', '=', '-', '*', '/', '%', '<', '>', '~', '(', ',', ';'])
	else:
		return False

## Check if a char is a valid part of a name
#  @param   char          The char to check
#  @param   beginOfName   Is this the begin of the name?
def isValidName(char, beginOfName = False):

	if char.isalpha() or char in ['_', '$']:
		return True
	elif char.isnumeric() and not beginOfName:
		return True
	else:
		return False


class LOC:

	# Type
	type = None

	# Name
	name = None

	# The string that begins this LOC
	begins = None

	# The string that ends this LOC
	ends = None

	# If a begin is greedy, it does not
	# care what comes after it
	# (If it's a whole word or not)
	greedy = None

	# Naming things
	namePosition = None
	nameRequired = None

	# Paren location
	parenPosition = None
	parenRequired = None

	# Block location
	blockPosition = None
	blockRequired = None

	# Is there an expression anywhere?
	expressionPosition = None
	expressionRequired = None

	# Extra settings
	extras = {}

	# If one "begins" can be used for
	# multiple name-paren-block
	grouping = None

	def setBegin(self, string):
		self.begins = string

	def setEnd(self, string):
		self.ends = string

	def setGreedy(self, greedy):
		self.greedy = greedy

	def setName(self, order, required = False):
		self.namePosition = order
		self.nameRequired = required

	def setParen(self, order, required = False):
		self.parenPosition = order
		self.parenRequired = required

	def setBlock(self, order, required = False):
		self.blockPosition = order
		self.blockRequired = required

	def setExpression(self, order, required = False):
		self.expressionPosition = order
		self.expressionRequired = required

	def setGroup(self, delimiter):
		self.grouping = delimiter

	def setExtra(self, order, char, required = False):
		self.extras[order] = {
			'char': char,
			'position': order,
			'required': required
		}


	def getNextTarget(self, position):

		if position in self.extras:
			return self.extras[position]['char'], self.extras[position]['required']
		elif self.namePosition == position:
			return 'name', self.nameRequired
		elif self.parenPosition == position:
			return 'paren', self.parenRequired
		elif self.blockPosition == position:
			return 'block', self.blockRequired
		elif self.expressionPosition == position:
			return 'expression', self.expressionRequired

		return False, False


	def extract(self, text, startId):

		if self.greedy:
			return self.extractGreedy(text)
		else:

			# Get the beginning
			begin = self.begins

			# Get the new current id
			id = len(begin)

			# Remove the beginning
			rest = text[id:]

			# Position
			position = 0

			extractions = {'beginId': id}

			# See what we have to do next
			while True:

				position += 1

				(targetName, targetRequired) = self.getNextTarget(position)

				if targetName == 'name':
					(result, endId, newLines) = self.extractName(rest)

					# Store the result in the extractions
					extractions['name'] = {
						'name': result,
						'beginId': id,
						'endId': id+endId
					}

					# Set the next Id
					id = id+endId+1

					# Get the new rest
					rest = text[id:]

				elif targetName == 'expression':
					(result, endId, newLines) = self.extractExpression(rest)

					# Work on this next!

				elif targetName == 'paren':
					(result, endId, newLines) = self.extractParen(rest)

					# Store the result in the extractions
					extractions['paren'] = {
						'content': result,
						'beginId': id,
						'endId': endId
					}

					# Set the next Id
					id = endId+1

					# Get the new rest
					rest = text[id:]
				elif targetName:
					
					# Get extra stuff
					endId = getCharAfterId(rest, targetName)

					print('Get extra >> ' + str(endId))

					if endId or endId > -1:
						extractions[targetName] = {
							'content': targetName,
							'beginId': id,
							'endId': endId
						}
						
						# Set the next Id
						id = endId+1

						# Get the new rest
						rest = text[id:]
					else:
						
						if targetRequired:
							break
						else:
							continue

				else:
					break

			print({'rest':rest})
			print(extractions)

	def extractExpression(self, text):

		# The new lines we've encountered
		newLines = 0
		
		# Result
		result = ''

		# Has the expression begin?
		hasBegun = False

		for i, c in enumerate(text):

			if c == '\n':
				newLines += 1

			if not hasBegun:
				
				# Skip whitespaces
				if isWhitespace(c):
					continue

	def extractParen(self, text):
		return extractBetween(text, '(', ')')

	def extractName(self, text):

		# The new lines we've encountered
		newLines = 0
		
		# Result
		result = ''

		# Has the name begin?
		hasBegun = False

		for i, c in enumerate(text):

			if c == '\n':
				newLines += 1

			# If the name hasn't begun yet
			if not hasBegun:

				# Skip spaces
				if isSpacing(c):
					continue

				# See if it's a valid start
				if isValidName(c, True):
					hasBegun = True
					result += c
			else:
				# The name has begun!

				if isValidName(c):
					result += c
				else:
					# It's not a valid part of a name, so finish!
					break

		endId = i-1

		return result, endId, newLines


	def extractBegin(self, text):
		pass

	def extractBetween(self, text, open, close):

		# The new lines we've encountered
		newLines = 0

		# Result
		result = ''

		# Counter
		betweenOpen = 0

		# Stringopen
		stringOpen = False

		# Escape
		escape = False

		# Between is open
		isOpen = False

		for i, c in enumerate(text):

			# Count newlines
			if c == '\n':
				newLines += 1

			# If c is a backslash, invert the backslash status
			if c == "\\":
				escape = not escape

			# If a string is open
			if stringOpen:

				# Add the current char no matter what
				result = result + c

				# And the new char is the same literal,
				# and it wasn't backslash-escaped
				if c == stringOpen and not backslash:
					stringOpen = False

			if not isOpen:

				# Skip whitespaces
				if isWhitespace(c):
					continue
				elif c == open:
					isOpen = True
					betweenOpen = 1
					result += c
				else:
					break
			# We have started!
			else:

				endId = i
				result = result + c

				# First do some string checking
				if c == "'":
					stringOpen = "'"
				elif c == '"':
					stringOpen = '"'
				else:
					if c == open:
						betweenOpen += 1
					elif c == close:
						betweenOpen -= 1

						# If we closed the last one...
						if betweenOpen == 0:
							break

			endId = i

		return result, endId, newLines



	# Extract a greedy statement, one that does not care
	# what comes between begin and end char, like /* */
	def extractGreedy(self, text):

		# The new lines we've encountered
		newLines = 0
		
		# Skip to id
		skipToId = False

		# Include to id
		includeToId = False

		# Include to and end at this id
		endAtId = False

		# Result
		result = ''

		for i, c in enumerate(text):

			# Count newlines
			if c == '\n':
				newLines += 1

			if skipToId and i <= skipToId:
				continue
			elif includeToId and i <= includeToId:
				result += c
				continue
			elif endAtId and i <= endAtId:
				result += c

				if endAtId == i:
					break

			if i == 0:
				if text.startswith(self.begins):
					includeToId = len(self.begins) - 1
			else:
				if hasCharsAfter(text, self.ends, i):
					endAtId = i + (len(self.ends)-1)

			result += c
		
		endId = i

		return result, endId, newLines



statements = {}
expressions = {}

class Statement(LOC):

	type = 'statement'

	def __init__(self, name):
		self.name = name
		statements[name] = self
	

class Expression(LOC):

	type = 'expression'

	def __init__(self, name):
		self.name = name
		expressions[name] = self



docblock = Statement('docblock')
docblock.setBegin('/*')
docblock.setEnd('*/')
docblock.setGreedy(True)

var = Statement('var')
var.setBegin('var')
var.setName(1, True)
var.setExpression(3)
var.setExtra(2, '=', True)
var.setGroup(',')


# statements = {
# 	'var': {
# 		'begins': 'var',
# 		'ends': False,
# 		'strict': False,
# 		'name': 1,
# 		'parens': False,
# 		'block': False,
# 		'grouping': ',',
# 		'expressions': True
# 	},
# 	'function': {
# 		'begins': 'function',
# 		'strict': False,
# 		'name': 1,
# 		'parens': 2,
# 		'block': 3
# 	}
# }

expressions = {
	'function': {
		'begins': 'function',
		'strict': False,
		'name': 1,
		'parens': 2,
		'block': 3
	},
	'paren': {
		'begins': '(',
		'ends': ')',
		'strict': True
	},
}

## See if a char is a space or a tab
def isSpacing(char):
	if char == ' ' or char == '\t':
		return True
	return False

## See if a char is a space, a tab or a newline
def isWhitespace(char):
	if isSpacing(char) or char == '\n':
		return True


def determineOpen(text, id):

	# Do not strip the text here,
	# It'll mess up the line numbers
	text = text[id:]

	# Is it a statement?
	for name, stat in statements.items():

		# Strict means we don't care what comes after the opening tag
		if stat.greedy:
			if text.startswith(stat.begins):
				result, newId, newLines = stat.extract(text, id)
				return 'statement', name, id, newId+id, result, newLines
		else:
			if hasCharsAfter(text, stat.begins):
				print('A statement called ' + name + ' begins at ' + str(id))
				result, newId, newLines = stat.extract(text, id)
				return 'statement', name, id, newId+id, result, newLines

	return False, False, False, False, False, False



def splitStatements(text):

	# The total length of the text
	length = len(text)

	# The max char id in the text
	maxId = length-1

	# The current id
	id = 0

	# The line nr
	lineNr = 1

	# The current open type
	openType = False
	openName = False

	# Go over every letter
	while id < length:

		# Get the current char
		cur = text[id]

		# Get the surrounding characters
		(prev, next) = getSurround(text, id)

		# If nothing is open, see what the next statement does
		if not openType:

			if not isWhitespace(cur):
				(openType, openName, beginId, endId, result, newLines) = determineOpen(text, id)

				if openType:
					print({'type': openType, 'typeName': openName, 'beginId': beginId, 'endId': endId, 'result': result, 'newlines': newLines})
					id = beginId
					openType = False
					#print('LineNr ' + str(lineNr) + ' begins a ' + str(openName) + ' ' + str(openType))
		else:
			pass

		if cur == '\n':
			lineNr += 1

		#if cur == '\n' or cur == ';':
		#	openType = False

		id += 1



## Split a block (including a complete text file)
#  into multiple statements
#  @param   text   The line to split
def oldsplitStatements(text):

	# Where all the result statements go
	results = []

	# The previous character
	prev = ''

	# The next character
	next = ''

	# The working statement
	working = ''

	# Debug info
	debug = ''

	# The line number
	lineNr = 1
	beginLineNr = 1

	# The length of the original text
	length = len(text)

	# Loop variables
	append = False
	lineType = False

	# What is currently open?
	stringOpen = False
	docblockOpen = False
	inlineCommentOpen = False
	backslash = False
	
	lettersBefore = False
	colonBefore = False
	parenBefore = False
	closeParenBefore = False
	equalBefore = False
	commaBefore = False
	hasFunction = False
	functionParameters = False
	inParamParens = 0
	functionBody = False
	closingBody = False
	openArray = 0

	# Count the number of open object literals
	openObject = 0

	for i, c in enumerate(text):

		# Get the surrounding characters
		(prev, next) = getSurround(text, i)
		
		# If c is a backslash, invert the backslash status
		if c == "\\":
			backslash = not backslash

		# If a string is open
		if stringOpen:

			# Add the current char no matter what
			working = working + c

			# And the new char is the same literal,
			# and it wasn't backslash-escaped
			if c == stringOpen and not backslash:
				stringOpen = False
		elif docblockOpen:
			
			working = working + c

			# /*/ is not a docblock, it has to be longer!
			if len(working) > 3 and prev == "*" and c == "/":
				append = working
				lineType = 'docblock'
				working = ''
				docblockOpen = False
		elif inlineCommentOpen:
			# We just remove/dont add inline comments
			if c == "\n":
				inlineCommentOpen = False
		elif c == "/" and next == "*": # Docblock
			docblockOpen = True
			beginLineNr = lineNr

			if working.strip():
				append = working
			
			working = c
		elif c == "/" and next == "/": # Inline comment, we just remove these
			inlineCommentOpen = True

			if working.strip():
				append = working

			working = ''
		else:

			working = working + c

			if c == ';':
				append = working
				working = ''

				if prev == '}':
					append = False
			elif (parenBefore or equalBefore or (openObject and colonBefore)) and c == '{':
				openObject += 1
				beginLineNr = lineNr
			elif openObject and c == '}':
				openObject -= 1

				if openObject == 0:
					append = working
					working = ''
			elif c == '[':
				if isArrayLiteral(text, i):
					openArray += 1
			elif c == ']' and openArray:
				openArray -= 1
			elif c == '{':
				append = working
				lineType = 'openblock'
				working = ''
			elif c == '}':
				append = working
				lineType = 'closeblock'
				working = ''

				if next == ';':
					append += ';'

			elif c == '"':
				stringOpen = '"'
				beginLineNr = lineNr
			elif c == "'":
				stringOpen = "'"
				beginLineNr = lineNr

		# If c is not a backslash, the backslash status for
		# the next iteration is false again
		if not c == "\\":
			backslash = False

		# Determin characters before the next char
		if not stringOpen:
			# Are there letters before the next char?
			if c.isalpha() or c == '$' or c == '_':
				lettersBefore = True
			elif lettersBefore and (c.isnumeric() or c == ' ' or c == '\t'):
				pass
			else:
				lettersBefore = False

			# Is there an colon somewhere before the next char?
			if c == ':':
				colonBefore = True
			elif colonBefore and (c == ' ' or c == '\n' or c == '\t'):
				pass
			else:
				colonBefore = False

			# Find parens inside parameters
			if functionParameters and c == '(':
				inParamParens += 1
			elif functionParameters and c == ')':
				if inParamParens == 0:
					functionParameters = False
				else:
					inParamParens -= 1

			# Look for function body
			if hasFunction and not functionParameters and not functionBody and c == '{':
				functionBody = True

			if hasFunction and functionBody and openObject == 0 and c == '}':
				functionBody = False
				hasFunction = False
				closingBody = True

			# Look for parameters
			if not functionParameters and hasFunction and c == '(':
				functionParameters = True

			# Look for the function statement
			if not functionBody and not functionParameters and c == ' ' or c == '\t':
				hasFunction = hasWordBefore(text, i, 'function')

			# Is there an open paren before the next char?
			# This does NOT count open parens, because once a different char
			# has been found, this is false!
			if c == '(':
				parenBefore = True
			elif parenBefore and (c == ' ' or c == '\n' or c == '\t'):
				pass
			else:
				parenBefore = False

			# Detect a close paren
			if c == ')':
				closeParenBefore = True
			elif closeParenBefore and (c == ' ' or c == '\n' or c == '\t'):
				pass
			else:
				closeParenBefore = False

			# Detect an equal sign
			if c == '=':
				equalBefore = True
			elif equalBefore and (c == ' ' or c == '\t'):
				pass
			else:
				equalBefore = False

			# Detect a comma
			if c == ',':
				commaBefore = True
			elif commaBefore and (c == ' ' or c == '\t' or c == '\n'):
				pass
			else:
				commaBefore = False

			# If we're closing a block body
			if closingBody and not next == ')' and not next == ';':
				append = working
				working = ''
				closingBody = False
			# If a newline begins see if it's the end of this statement
			elif c == '\n' and (not functionBody and not openArray and not docblockOpen and not openObject and not commaBefore and not closeParenBefore):

				# See if there is an expressionizer
				if hasCharBefore(text, i, expressionizers):
					pass
				else:
					append = working
					working = ''

		# If the append is set, append it
		if append and append.strip():
			if beginLineNr:
				nr = beginLineNr
			else:
				nr = lineNr

			newEntry = {'text': append.strip(), 'line': nr, 'type': lineType}
			results.append(newEntry)

			append = False
			lineType = False
			beginLineNr = False
			debug = ''

		# If c is a return, increase the linenr
		if c == "\n":
			lineNr += 1


	# Don't forget to add the last working line!
	if working.strip():
		results.append({'text': working.strip(), 'line': lineNr, 'type': lineType})

	postNormalize(results)

	return results

## Does this line declare something by using var?
def hasDeclaration(text):

	if text.beginswith('var '):
		return True
	else:
		return False

## Get declaration variables
def getAssignmentVariables(text):
	pass

## We've split & joined the statements
#  to the best of our abilities,
#  now we need to normalize them some more
def postNormalize(inputArray, recurse = False):

	#if recurse:
	#	print(inputArray)

	# The results to return in the end
	results = []

	# The current group
	group = []

	# The current docblock
	activeDocblock = False

	# Are we in an open block?
	openBlock = 0
	openBlockBegin = False
	recurseResult = []

	# Default surround object
	default = {'text': '', 'line': False, 'type': False}

	for id, entry in enumerate(inputArray):

		(prev, next) = getSurround(inputArray, id, default)

		# Set the docblock if present
		if entry['type'] == 'docblock':
			next['docblock'] = entry['text']
			continue
		else:
			next['docblock'] = False

		# If the current entry opens a new block
		if entry['type'] == 'openblock':
			openBlock += 1

			if openBlock == 1:
				openBlockBegin = entry

		# If the previous entry opened a block, reset the group
		if prev['type'] == 'openblock':
			if openBlock == 1:
				if not entry['type'] == 'closeblock':
					group = []

		if entry['type'] == 'closeblock':
			if openBlock > 0:
				openBlock -= 1

		# Add the current entry to the group
		group.append(entry)

		if openBlock == 1 and next['type'] == 'closeblock':
			if recurse:
				print('>> ' + str(next))
			if not recurse:
				print(next)

			# If the next statement will close this block...
			# Recursively add body statements to this one
			openBlockBegin['body'] = postNormalize(group, True)

			# Reset the group with the beginning line of the block
			group = [openBlockBegin]
			openBlockBegin = False

		if not entry['type'] and not openBlock:
			results.append(group)
			group = []
		elif not openBlock and entry['type'] == 'closeblock':
			results.append(group)
			group = []

	if not recurse:
		for x in results:
			pass
			print(x)

	return results




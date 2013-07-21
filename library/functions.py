#
# These functions are used throughout the Witty plugin,
# and are mainly for getting information out of code
#
import os, re, threading, pprint, json, pickle, hashlib, inspect, sublime, datetime
from decimal import *

doDebug = False
debugLevel = 1

# Chars
whitespace = [' ', '\n', '\t']

# All the operators
operators = ['+', '=', '-', '*', '/', '%', '<', '>', '~']

operatorSymbols = [
	'>>>=', '>>=', '<<=', '%=', '/=', '*=', '-=', '+=', '&=', '^=', '|=',   # Assignment
	'==', '!=', '===', '!==', '>', '>=', '<', '<=', # Comparison
	'%', '++', '--', '-', '+', # Arithmetic
	'&', '|', '^', '~', '<<', '>>', '>>>', # Bitwise
	'&&', '||', '!', # Logical
	'?', ':', # Conditional
	'.', '['  # Members
	]

operatorTokens = [
	'delete', 'in', 'instanceof', 'new', 'typeof', 'void', 'yield'
]

operatorSymbols.sort(key=len, reverse=True)
operatorTokens.sort(key=len, reverse=True)

# Things that denote expressions
expressionizers = ['+', '=', '-', '*', '/', '%', '<', '>', '~', '(', ',']

# This list is far from finished, just for testing!
wordDelim = [',', ' ', '\n', '\t', '(', ')', '{', '}', '[', ']']

# Opening Statements
statWords = ['if', 'do', 'while', 'for', 'var', 'try', 'let', 'else', 'case', 'throw', 'const', 'yield', 'continue', 'break', 'debugger', 'function']

literals = ["'", '"', '{', '[']

# Is something an array?
def is_array(object):
	return isinstance(object, (list, tuple))

#
# Log Functions
#

# Prepare the pretty printer
pp = pprint.PrettyPrinter(indent=2)

# Create a dictionary for open files
openFiles = {}

## Generate a hash
#  @param   data      The list with strings
def generateHash(data):

	# Prepare the project id hash
	hashId = hashlib.md5()

	# Loop through all the folders to generate a hash
	for text in data:
		hashId.update(text.encode('utf-8'))

	return hashId.hexdigest()

## Turn the given parameter into a dictionary
#  @param   data   The data to turn into a dict
#  @param   level  
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

## Log data to the given file in /dev/shm/ (memory fs)
#  @param   data        The data to write to the file
#  @param   filename    The filename inside /dev/shm/
#  @param   doDictify   Dictify the given data
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

## Colorize the following part of the string
#  @param   t      The previous part of the string
#  @param   c      The colour
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

## Get a better prefix (Sublime autocomplete)
#  @param   text
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

# Is the given file a javascript file?
# Right now, it only checks for .js in the filename
def isJavascriptFile(filename):
	return '.js' in filename

## Is this line a function call? (Does it begin with one)
#  @param   text   The text to identify
def isFunctionCall(text):
	match = reFnCallBegin.match(text)

	if match:
		return True
	else:
		return False

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

def hasWordNext(text, word, id = False):
	return _hasChars(text, word, id, False, False)

# Look for chars directly after the given text, spaces first invalidate the result
def hasCharsNext(text, word, id = False, checkForSpace = False):
	return _hasChars(text, word, id, False, not checkForSpace)

def hasCharsAfter(text, word, id = False, ignoreEndWhitespace = True):
	return _hasChars(text, word, id, True, ignoreEndWhitespace)

def _hasChars(text, word, id = False, ignoreBeginningWhitespace = True, ignoreEndWhitespace = True, returnId = False, returnWord = False):

	#pr('Looking for ' + str(word) + ' in text ' + text[id:id+5] + '... ignoreBeginningWhitespace: ' + str(ignoreBeginningWhitespace) + ' ignoreEndWhitespace: ' + str(ignoreEndWhitespace))

	result = False

	while True:
	
		if not len(text):
			break

		if not isinstance(id, bool):
			try:
				text = text[id:]
			except IndexError:
				break
		else:
			id = 0

		try:
			# If we should ignore the beginning space, recurse
			if ignoreBeginningWhitespace and text[id] in whitespace:
				return _hasChars(text, word, id+1, ignoreBeginningWhitespace, ignoreEndWhitespace, returnId, returnWord)

		except IndexError:
			break

		if isinstance(word, list):

			wordList = word
			word = False

			for w in wordList:
				temp = _hasChars(text, w, 0, ignoreBeginningWhitespace, ignoreEndWhitespace, True)

				if temp > -1:
					word = w
					result = id + temp
					break

			break

		# If this text doesn't start with this word at all, return False
		if not text.startswith(word):
			break
		else:
			# The text does start with the word
			wordlength = len(word)

			if ignoreEndWhitespace:
				result = id
			else:
				# Make sure it's actually a word, not part of something else
				extraChar = text[wordlength:wordlength+1]

				if extraChar in wordDelim:
					result = id
				else:
					break


		break

	if isinstance(result, bool):

		if returnId:
			result = -1
	else:

		if not returnId:
			# We want a boolean
			if result > -1:
				result = True
			else:
				result = False

	if returnWord:
		return result, word
	else:
		return result

def getCharAfterId(text, word, id = False, checkForSpace = False):

	if not checkForSpace:
		temp = text.strip()
	else:
		temp = text

	isPresent = hasCharsNext(temp, word, id, checkForSpace)

	if not isPresent:
		return False
	else:
		for i, c in enumerate(text):
			if c == word:
				return i

# Get the id for the next given word
# Does not care about anything inbetween
def getNextCharId(text, word, id = False):

	if id > -1:
		text = text[id:]
	else:
		id = 0

	length = len(word)

	for i, c in enumerate(text):

		stack = text[i:i+length]

		if stack == word:
			return id+i

	return False

# See if there's an operator somewhere after
def hasOperatorAfter(text, id = False):

	(text, exists) = shiftString(text, id)

	if exists:

		# See if there are any symbols, which allow spaces after it
		symbolId = _hasChars(text, operatorSymbols, False, True, True, True)

		if symbolId > -1:
			return True

		# See if there are any tokens, which don't allow spaces after it
		tokenId = _hasChars(text, operatorTokens, False, True, False, True)

		if tokenId > -1:
			return True
	
	return False

def hasOperatorNext(text, id = False):

	(text, exists) = shiftString(text, id)

	if exists:

		# See if there are any symbols, which allow spaces after it
		symbolId = _hasChars(text, operatorSymbols, False, False, True, True)

		if symbolId > -1:
			return True

		# See if there are any tokens, which don't allow spaces after it
		tokenId = _hasChars(text, operatorTokens, False, False, False, True)

		if tokenId > -1:
			return True
	
	return False


# Get a part of the given string
def shiftString(text, id):

	if len(text) <= id:
		return text, False

	if id == 0:
		return text, True
	try:
		text = text[id:]
		return text, True
	except IndexError:
		return text, False

def extractOperatorAfter(text, id = False):

	(text, exists) = shiftString(text, id)

	while exists:

		# See if there are any symbols, which allow spaces after it
		(beginId, word) = _hasChars(text, operatorSymbols, False, True, True, True, True)

		if beginId > -1:
			break

		# See if there are any tokens, which don't allow spaces after it
		(beginId, word) = _hasChars(text, operatorTokens, False, True, False, True, True)

		if beginId > -1:
			break

		break
	
	if beginId > -1:
		endId = beginId + len(word)
		newLines = text.count('\n', 0, endId)
	else:
		endId = False
		newLines = False
		word = False

	return word, endId, newLines

# See if there's a statement after (simple version)
def hasStatementAfter(text, id = False):

	try:
		if id > -1:
			text = text[id:]

		if isWhitespace(text[0]):
			return hasStatementAfter(text, 1)
	except IndexError:
		return False

	for stat in statWords:
		if _hasChars(text, stat, False, False, False):
			return True

	return False

def extractStatementAfter(text, id = False):

	(text, exists) = shiftString(text, id)

	(beginId, word) = _hasChars(text, statWords, False, True, False, True, True)
	
	if beginId > -1:
		endId = beginId + len(word)
		newLines = text.count('\n', 0, endId)
	else:
		endId = False
		newLines = False
		word = False

	return word, endId, newLines


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

def _hasCharsBefore(text, id, word, ignoreBeginningWhitespace = True, ignoreTrailingWhitespace = True):

	if isinstance(id, bool):
		pass
	else:
		text = text[:id]

	# If we can ignore the trailing whitespace, strip the text
	if ignoreTrailingWhitespace:
		text = text.strip()

	if isinstance(word, list):

		for w in word:
			result = _hasCharsBefore(text, False, w, ignoreBeginningWhitespace, False)

			if result:
				return True

		# If nothing in the list matched, return False
		return False

	if text.endswith(word):
		return True
	else:
		return False

## Look for chars before the id position,
#  does not care about spaces before or after the word
#  @param   text   The text to look
#  @param   id     The id to look before
#  @param   word   The word(s) to look for
def hasCharsBefore(text, id, word):
	return _hasCharsBefore(text, id, word)


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

## Extract the first string from the given text
#  @param    text         The original text to use
#  @param    literal      The literal to use (' or ")
#  @param    id           The id position in the text to start from
def extractString(text, literal, id = False):

	if id > -1:
		text = text[id:]

	# Count the newlines
	newLines = 0

	result = ''

	stringOpen = False

	escaped = False

	for i, c in enumerate(text):

		if c == '\n':
			newLines += 1

		if not stringOpen:

			if isWhitespace(c):
				continue
			elif c == literal:
				stringOpen = True
				result += c
			else:
				break

		else:

			if c == '\\' and not escaped:
				escaped = True
				continue

			if c == literal and not escaped:
				result += c
				break
			elif c == '\n':
				pass
			else:
				if escaped:
					result += '\\'
				result += c

	return result, i, newLines

## Extract the next name from the given text
def extractName(text):

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
				name = False
				break
		else:
			# The name has begun!

			if isValidName(c):
				result += c
			else:
				# It's not a valid part of a name, so finish!
				break

	endId = i - 1

	return result, endId, newLines

def extractParen(text):
	return extractBetween(text, '(', ')')

def extractCurly(text):
	return extractBetween(text, '{', '}')

def extractSquare(text):
	return extractBetween(text, '[', ']')

def extractBetween(text, open, close):

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

		# If c is a escape, invert the escape status
		if c == "\\":
			escape = not escape

		# If a string is open
		if stringOpen:

			# Add the current char no matter what
			result = result + c

			# And the new char is the same literal,
			# and it wasn't escaped
			if c == stringOpen and not escape:
				stringOpen = False
				
		elif not isOpen:

			# Skip whitespaces
			if isWhitespace(c):
				continue
			elif c == open:
				isOpen = True
				betweenOpen = 1
				#result += c # Do not add the opener!
			else:
				# This is not a space and not an opener, so stop!
				break
		# We have started!
		else:

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

			result = result + c

	endId = i

	return result, endId, newLines

# Extract a greedy statement, one that does not care
# what comes between begin and end char, like /* */
def extractGreedy(text, begins, ends):

	# The new lines we've encountered
	newLines = 0
	
	# Skip to id
	skipToId = False

	# Include to id
	includeToId = False

	# Include to and end at this id
	endAtId = False

	# Have we begun?
	hasBegun = False

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
			if text.startswith(begins):
				includeToId = len(begins) - 1
				hasBegun = True
		else:
			if hasCharsNext(text, ends, i):
				endAtId = i + (len(ends)-1)

		if hasBegun:
			result += c
	
	endId = i

	return result, endId, newLines

## See if a char is a space or a tab
def isSpacing(char):
	if char == ' ' or char == '\t':
		return True
	return False

## See if a char is a space, a tab or a newline
def isWhitespace(char):
	if isSpacing(char) or char == '\n':
		return True

def willExpressionContinue(text, id, hasBegun, waitingForOperand):

	(text, exists) = shiftString(text, id)

	if exists:
		if not hasBegun:
			return True

		if waitingForOperand:
			return True

		(tempOperator, newId, tempLines) = extractOperatorAfter(text)

		if tempOperator:
			return True
		else:
			return False

	# If it doesn't exists, the expression has ended
	return False

## If the next line is an expression, extract it
#  @param   text       The text to start from
#  @param   hasBegun   If we already now this is an expression
#  @param   waitingForOperand   If we're waiting for an operand
def extractExpression(text, scopeLevel, lineNr, currentId, startId = 0, hasBegun = False, waitingForOperand = False):

	(text, exists) = shiftString(text, startId)

	pr({'text': text})

	# The new lines we've encountered
	newLines = 0

	# Result
	result = ''

	# Skip
	skipToId = False

	operandBusy = False
	docblockEnd = False
	currentDocblock = False

	# Extra extractions
	extras = []

	# Loop through the text
	for i, c in enumerate(text):

		# Skip any characters we might have already added
		if i < skipToId:
			continue

		if isWhitespace(c):
			operandBusy = False

		if hasOperatorNext(c):
			operandBusy = False
			waitingForOperand = True

		if c == ';':
			break

		# Count newlines
		if c == '\n':

			opBefore = hasCharsBefore(text, i, operatorSymbols) or hasCharsBefore(text, i, operatorTokens)
			opAfter = hasOperatorAfter(text, i)

			if opBefore:
				pass
			elif opAfter:
				pass
			else:
				break

			newLines += 1

		tempWord = False

		if not operandBusy:
			# Look for a statement
			(tempWord, tempId, tempNewLines) = extractStatementAfter(text, i)

		# A statement word was found
		if tempWord:

			if hasBegun and tempWord == 'function':

				# Extract the function
				tempResult = function.extract(text, scopeLevel, lineNr+newLines, i)

				pr('>>>>>>>>>>>>>>> FUNCTION >>>>>>>>>>>>>>>>>>>>>')
				pr(tempResult)
				

				extras.append(tempResult['result'])

				# This can't be added to the result
				result += ' '

				# Skip to the id after it
				skipToId = tempResult['endId']+1

				# Up the newline count
				newLines += tempResult['newLines']

				pr('-')
				pr({'NEXT': text[skipToId:]})
				pr('-')

				waitingForOperand = False

				continue

			else:
				i -= 1
				break
		# If c is a starting paren
		elif c == '(':

			# Extract everything between the parens
			(tempResult, tempEndId, tempNewLines) = extractParen(text[i:])

			result += '(' + tempResult + ')'
			skipToId = i+tempEndId+1
			newLines += tempNewLines

			hasBegun = True

			waitingForOperand = False
			
			continue
		elif hasCharsAfter(text, '/*', i):

			docblockOpen = getNextCharId(text, '/*', i)
			skip = getNextCharId(text, '*/', i)

			if skip > -1:
				currentDocblock = text[i:skip+1]
				skipToId = skip + 2
				docblockEnd = skip + 1
				continue
			else:
				break
		# Skip inline comments
		elif hasCharsAfter(text, '//', i):
			
			skip = getNextCharId(text, '\n', i)

			if skip > -1:
				skipToId = skip+1
				continue
			else:
				break
		# Extract literals
		elif c in literals:

			if c == "'" or c == '"':
				(tempResult, tempId, tempNewLines) = extractString(text, c, i)

				result += tempResult

				skipToId = i+tempId+1
				newLines += tempNewLines
			elif c == '{':
				(tempResult, tempEndId, tempNewLines) = extractCurly(text[i:])
				result += '{' + tempResult + '}'
				skipToId = i+tempEndId+1
				newLines += tempNewLines
			elif c == '[':
				(tempResult, tempEndId, tempNewLines) = extractSquare(text[i:])
				result += '[' + tempResult + ']'
				skipToId = i+tempEndId+1
				newLines += tempNewLines

			waitingForOperand = False

			continue
			
		else:
			result += c
			operandBusy = True
			continue

	# If the parsed text ends with a docblock, rewind the ending id
	if docblockEnd:
		tempText = text[:i].strip()

		if tempText.endswith('*/'):
			endId = docblockOpen
		else:
			endId = i
	else:
		endId = i

	pr({'REST': text[endId:]})

	endId += currentId + startId

	pr({'REST2': endId})

	result = {'text': result.strip(), 'functions': extras, 'docblock': currentDocblock, 'scope': scopeLevel}

	return {'scope': scopeLevel, 'line': lineNr, 'newLines': newLines, 'openType': 'expression', 'openName': 'expression', 'result': result, 'beginId': currentId, 'endId': endId, 'functions': extras}


class Statement:

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
	extras = None

	# If one "begins" can be used for
	# multiple name-paren-block
	grouping = None

	def __init__(self, name):

		# Does this have scope?
		self.scope = False

		self.type = 'statement'
		self.extras = {}
		self.name = name
		statements[name] = self

	def setScope(self, hasScope):
		self.scope = hasScope

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

	def setExtra(self, order, char, required = False, options = False):
		self.extras[order] = {
			'char': char,
			'position': order,
			'required': required,
			'options': options
		}

	def getNextTarget(self, position):

		if position in self.extras:
			return self.extras[position]['char'], self.extras[position]['required'], self.extras[position]['options']
		elif self.namePosition == position:
			return 'name', self.nameRequired, False
		elif self.parenPosition == position:
			return 'paren', self.parenRequired, False
		elif self.blockPosition == position:
			return 'block', self.blockRequired, False
		elif self.expressionPosition == position:
			return 'expression', self.expressionRequired, False

		return False, False, False


	def extract(self, text, scopeLevel, lineNr, currentId, startId = 0):

		a = datetime.datetime.now()

		(text, exists) = shiftString(text, startId)

		if text[0] in [' ', '\t', '\n']:
			
			if text[0] == '\n':
				lineNr += 1

			return self.extract(text[1:], scopeLevel, lineNr, currentId+1, 0)

		# Default newlines
		newLines = 0

		# The actual id where this statement starts
		beginId = currentId + startId

		# If this statement has scope...
		if self.scope:
			scopeLevel += 1

		if self.greedy:
			# Extract greedy pieces, like /* */ docblocks
			(result, endId, newLines) = extractGreedy(text, self.begins, self.ends)

			# Return the result
			return {'scope': scopeLevel, 'line': lineNr, 'newLines': newLines, 'openType': 'statement', 'openName': self.name, 'result': result, 'beginId': beginId, 'endId': beginId+endId}
		else:

			# Get the beginning
			begin = self.begins

			# Get the new current id
			id = len(begin)

			# Text length
			textLength = len(text)

			# Remove the beginning
			rest = text[id:]

			# Position
			position = 0

			# Start a new group?
			startNewGroup = False

			extractions = {'beginId': id}

			groupResult = {'group': []}

			# Has an expression already begun?
			expressionHasBegun = False
			waitingForOperand = False

			# See what we have to do next
			while True:

				position += 1

				# Have we reached the end of the string?
				if id >= textLength:
					break
				
				if self.grouping and text[id] == self.grouping:

					# Add the previous extractions to the group
					groupResult['group'].append(extractions)

					# Increase the id
					id = id + 1

					# Create a new extraction
					extractions = {'beginId': id}

					# Reset the position
					position = 0
					continue

				(targetName, targetRequired, extraOptions) = self.getNextTarget(position)

				if targetName == 'name':

					(result, endId, newLines) = extractName(text[id:])

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

					#(result, endId, newLines) = extractExpression(text, scopeLevel, lineNr+newLines, id, expressionHasBegun, waitingForOperand)
					result = extractExpression(text, scopeLevel, lineNr, beginId, id, expressionHasBegun, waitingForOperand)

					# Get the newLines
					newLines = result['newLines']

					extractions['expression'] = result

					id = result['endId'] + 1 - beginId

					expressionHasBegun = False
					waitingForOperand = False

					# Get the new rest
					rest = text[id:]

				elif targetName == 'paren':

					(result, endId, newLines) = extractParen(rest)

					# Store the result in the extractions
					extractions['paren'] = {
						'content': result,
						'beginId': id,
						'endId': id+endId
					}

					# Set the next Id
					id = id+endId+1

					# Get the new rest
					rest = text[id:]

				elif targetName == 'block':

					(result, endId, newLines) = extractCurly(rest)

					# If the result is empty, make sure it was because
					# the block was empty
					if not result:
						
						# If there is no block, get the first expression
						if not hasCharsAfter(rest, '{'):
							tempResult = extractExpression(rest, scopeLevel, lineNr, startId+id, 0, True, True)
							result = tempResult['result']['text']
							endId = tempResult['endId']
							newLines = tempResult['newLines']
							#(result, endId, newLines) = extractExpression(rest, scopeLevel, lineNr+newLines, True, True)

						pass

					# Now parse these results, too!
					parsedResults = splitStatements(result, scopeLevel, lineNr)

					# Store the result in the extractions
					extractions['block'] = {
						'content': result,
						'parsed': parsedResults,
						'beginId': id,
						'endId': id+endId
					}

					# Set the next Id
					id = id+endId+1

					# Get the new rest
					rest = text[id:]
				elif targetName:

					if extraOptions == 'expressionHasBegun':
						expressionHasBegun = True
						waitingForOperand = True

					# Get extra stuff
					endId = getCharAfterId(text[id:], targetName)

					if endId or endId > -1:
						extractions[targetName] = {
							'content': targetName,
							'beginId': id,
							'endId': id+endId
						}
						
						# Set the next Id
						id = id+endId+1

						# Get the new rest
						rest = text[id:]
					else:
						
						if targetRequired:
							break
						else:
							continue

				else:
					break

			if self.grouping:
				# Add the last result to the group
				groupResult['group'].append(extractions)
				result = groupResult['group']
			else:
				result = extractions

		b = datetime.datetime.now()
		c = b - a

		pr('...')
		return {'scope': scopeLevel, 'line': lineNr, 'newLines': newLines, 'openType': 'statement', 'openName': self.name, 'result': result, 'beginId': beginId, 'endId': beginId+id-1}

# Get the next statement/expression
def determineOpen(text, scopeLevel, lineNr, id):

	# Do not strip the text here,
	# It'll mess up the line numbers
	text = text[id:]

	# Is it a statement?
	for name, stat in statements.items():

		# Strict means we don't care what comes after the opening tag
		if stat.greedy:
			if text.startswith(stat.begins):
				pr('greed')
				return stat.extract(text, scopeLevel, lineNr, id)
				#result, endId, newLines = stat.extract(text, scopeLevel, id)
				#return 'statement', name, id, endId, result, newLines
		else:
			if hasWordNext(text, stat.begins):
				pr('nongreed')
				return stat.extract(text, scopeLevel, lineNr, id)
				#result, endId, newLines = stat.extract(text, scopeLevel, id)
				#return 'statement', name, id, endId, result, newLines

	# It wasn't a statement, so try getting the expression
	pr("express")
	return extractExpression(text, scopeLevel, lineNr, id, 0)
	#(result, endId, newLines) = extractExpression(text, scopeLevel)

	return False

# Parsing starts here
def splitStatements(text, scopeLevel, lineNr = 1):

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

	results = []

	# Go over every letter
	while id < length:

		# Get the current char
		cur = text[id]

		pr('>>> (' + str(scopeLevel) + ') Getting id ' + str(id) + ' on linenr ' + str(lineNr))

		if not isWhitespace(cur):
			
			result = determineOpen(text, scopeLevel, lineNr, id)

			if result:

				endId = result['endId']

				results.append(result)

				# Increase the line nr
				lineNr += result['newLines']

				# If the endId is smaller than the id we risk an infinite loop
				if endId < id:
					warn('====================================')
					warn('endId is smaller than current id, infinite loop!')
					warn('====================================')
					break

				id = endId

		if cur == '\n':
			lineNr += 1

		id += 1

	returnResults = []
	dbnow = False

	# Move docblocks
	for wstat in results:

		# If it's a docblock, keep it for the next statement!
		if wstat['openName'] == 'docblock':
			dbnow = wstat['result']
			continue

		# Set the docblock
		wstat['docblock'] = dbnow
		dbnow = False

		# Set the scope id
		wstat['scopeLevel'] = scopeLevel

		returnResults.append(wstat)

	return returnResults


## Does this line declare something by using var?
def hasDeclaration(text):

	if text.beginswith('var '):
		return True
	else:
		return False

## Get declaration variables
def getAssignmentVariables(text):
	pass


# Place to store all the type of statements in
statements = {}

docblock = Statement('docblock')
docblock.setBegin('/*')
docblock.setEnd('*/')
docblock.setGreedy(True)

var = Statement('var')
var.setBegin('var')
var.setName(1, True)
var.setExpression(3)
var.setExtra(2, '=', True, 'expressionHasBegun')
var.setGroup(',')

function = Statement('function')
function.setBegin('function')
function.setName(1, False)
function.setParen(2, True)
function.setBlock(3, True)
function.setScope(True)

ifStat = Statement('if')
ifStat.setBegin('if')
ifStat.setParen(1, True)
ifStat.setBlock(2)

elseStat = Statement('else')
elseStat.setBegin('else')
elseStat.setBlock(1)

forStat = Statement('for')
forStat.setBegin('for')
forStat.setParen(1, True)
forStat.setBlock(2)

switch = Statement('switch')
switch.setBegin('switch')
switch.setParen(1, True)
switch.setBlock(2, True)

do = Statement('do')
do.setBegin('do')
do.setBlock(1, True)

whileStat = Statement('while')
whileStat.setBegin('while')
whileStat.setParen(1, True)
whileStat.setBlock(2, False) # Block is optional when do/while

returnStatement = Statement('return')
returnStatement.setBegin('return')
returnStatement.setExpression(1, False)

breakStat = Statement('break')
breakStat.setBegin('break')
breakStat.setName(1, False)

contStat = Statement('continue')
contStat.setBegin('continue')
contStat.setName(1, False)

throwStat = Statement('throw')
throwStat.setBegin('throw')
throwStat.setExpression(1)

tryStat = Statement('try')
tryStat.setBegin('try')
tryStat.setBlock(1, True)

catch = Statement('catch')
catch.setBegin('catch')
catch.setParen(1, True)
catch.setBlock(2, True)

finallyStat = Statement('finally')
finallyStat.setBegin('finally')
finallyStat.setBlock(1, True)


#
# These functions are used throughout the Witty plugin,
# and are mainly for getting information out of code
#
import os, re, threading, pprint, json, pickle, hashlib, inspect, sublime, datetime
from decimal import *

doDebug = False
debugLevel = 1

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

def hasWordNext(text, word, id = False):
	return _hasChars(text, word, id, False, False)

# Look for chars directly after the given text, spaces first invalidate the result
def hasCharsNext(text, word, id = False, checkForSpace = False):
	return _hasChars(text, word, id, not checkForSpace)

def hasCharsAfter(text, word, id = False, ignoreEndWhitespace = True):
	return _hasChars(text, word, id, True, ignoreEndWhitespace)

def _hasChars(text, word, id = False, ignoreBeginningWhitespace = True, ignoreEndWhitespace = True, returnId = False, returnWord = False):

	#pr('Looking for ' + str(word) + ' in text ' + text[id:15] + '... ignoreBeginningWhitespace: ' + str(ignoreBeginningWhitespace) + ' ignoreEndWhitespace: ' + str(ignoreEndWhitespace))

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
			if ignoreBeginningWhitespace and text[0] in whitespace:
				temp = _hasChars(text, word, 1, ignoreBeginningWhitespace, ignoreEndWhitespace, True)

				if temp > -1:
					result = id + temp
					break

		except IndexError:
			break

		if isinstance(word, list):

			for w in word:
				temp = _hasChars(text, w, 0, ignoreBeginningWhitespace, ignoreEndWhitespace, True)

				if temp > -1:
					word = w
					result = id + temp
					break
				else:
					word = False

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
def extractExpression(text, hasBegun = False, waitingForOperand = False):

	pr({'text': text})

	# The new lines we've encountered
	newLines = 0

	# Result
	result = ''

	# Skip
	skipToId = False

	operandBusy = False
	docblockEnd = False

	# Loop through the text
	for i, c in enumerate(text):

		if isWhitespace(c):
			operandBusy = False

		if hasOperatorNext(c):
			operandBusy = False
			waitingForOperand = True

		# Count newlines
		if c == '\n':
			willContinue = willExpressionContinue(text, i, hasBegun, waitingForOperand)

			# If the expression has ended, break out!
			if not willContinue:
				i -= 1
				break

			newLines += 1

		# Skip any characters we might have already added
		if i < skipToId:
			continue

		tempWord = False

		if not operandBusy:
			# Look for a statement
			(tempWord, tempId, tempNewLines) = extractStatementAfter(text, i)

		# A statement word was found
		if tempWord:

			if hasBegun and tempWord == 'function':
				# Extract the function
				(fncResult, fncId, fncNewlines) = function.extract(text, i)

				# Add it to the result string
				result += fncResult

				# Skip to the id after it
				skipToId = i+fncId+1

				# Up the newline count
				newLines += fncNewlines

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

	return result.strip(), endId, newLines
			





## If the next line is an expression, extract it
#  @param   text       The text to start from
#  @param   hasBegun   If we already now this is an expression
#  @param   waitingForOperand   If we're waiting for an operand
def oldextractExpression(text, hasBegun = False, waitingForOperand = False):

	pr({'ExtractingExpresison': text[:20]})
	
	# The new lines we've encountered
	newLines = 0
	
	# Result
	result = ''

	# Skip
	skipToId = False

	# Set hasBegun next time
	setHasBegun = False

	# Is an operand busy?
	operandBusy = False

	# The possible end position of the statement
	# Actually: last newline
	possibleEnd = False

	docblockOpen = False
	docblockEnd = False

	if not hasBegun and not waitingForOperand:
		waitingForAnything = True
	else:
		waitingForAnything = False

	# Loop through the text
	for i, c in enumerate(text):

		# Indicates the expression has started
		# (and function is now always an expression)
		if setHasBegun:
			hasBegun = True

		# Count newlines
		if c == '\n':
			newLines += 1

		# Skip any characters we might have already added
		if skipToId and i < skipToId:
			continue
		elif c == ',':
			i -= 1
			break
		# If the next characters open a comment block, ignore them
		elif hasCharsAfter(text, '/*', i):

			docblockOpen = getNextCharId(text, '/*', i)
			skip = getNextCharId(text, '*/', i)

			if skip > -1:
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
		# Set the possibleEnd index (last newline)
		elif c == '\n':
			possibleEnd = i

		# Detect statement delimiters
		if c == ';':
			result += c
			break

		# Skip whitespaces before we begin
		if not hasBegun:
			
			# Skip whitespaces
			if isWhitespace(c):
				continue
			else:
				# Set hasBegun next loop
				setHasBegun = True

		# If this is a newline, see what comes after!
		if possibleEnd == i:

			# If a statement follows an enter, stop the expression
			if hasStatementAfter(text, i):
				break

			# If waiting for operand, or operand is busy
			if waitingForOperand or operandBusy:
				# The newline is allowed
				pass
			elif hasCharsAfter(text, ['{', '('], i):
				# The newline is not allowed
				break
			elif hasOperatorAfter(text, i+1):
				# An operator was found on the newline

				# @todo: actually check for "++" like operators,
				# because they start a new statement

				# Continue without adding the newline
				continue
			else:
				break
		
		if waitingForOperand or True:

			if hasBegun and hasWordNext(text, 'function', i):
				pr({'test': text[i:i+10]})
				(fncResult, fncId, fncNewlines) = function.extract(text, i)
				pr(fncResult)
				die()

			if operandBusy and isWhitespace(c):

				if hasCharsAfter(text, '.', i):
					continue
				elif hasCharsAfter(text, '[', i):
					continue
				else:
					operandBusy = False
					waitingForOperand = False
					continue

			# Extract everything between parens
			elif c == '(':
				(tempResult, tempEndId, tempNewLines) = extractParen(text[i:])
				result += '(' + tempResult + ')'
				skipToId = i+tempEndId+1
				newLines += tempNewLines

				# The operand is likely done, but we still could see a () call
				operandBusy = True

				continue
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

					# The operand is likely done, but we still could see a () call
					operandBusy = True
				elif c == '[':
					(tempResult, tempEndId, tempNewLines) = extractSquare(text[i:])
					result += '[' + tempResult + ']'
					skipToId = i+tempEndId+1
					newLines += tempNewLines

					# The operand is likely done, but we still could see a () call
					operandBusy = True

				continue
				
			else:
				result += c
				operandBusy = True
				continue

		if not waitingForOperand or True: # Waiting for operator

			pr({'LookingForOperator': text[i:]})
			pr(hasOperatorAfter(text, i))

			if c == '(':
				(tempResult, tempEndId, tempNewLines) = extractParen(text[i:])
				result += '(' + tempResult + ')'
				skipToId = i+tempEndId+1
				newLines += tempNewLines

				# The operand is likely done, but we still could see a () call
				operandBusy = True
			else:

				(tempOperator, newId, tempLines) = extractOperatorAfter(text, i)

				if not isinstance(tempOperator, bool):

					print({'word': tempOperator, 'newid': newId, 'newLines': newLines})

					if tempOperator == 'function':
						(fncResult, fncId, fncNewlines) = function.extract(text, i-newId)
						pr(fncResult)
					else:
						waitingForOperand = True
						result += tempOperator  # This will result in an operator without a space in front if there is one, but oh well
						skipToId = i + newId + 1
						newLines += tempLines

						pr('Currentid: ' + str(i))
						pr('Skipto: ' + str(skipToId))

				else:
					
					result += c

					#(tempWord, tempEndId, tempNewLines) = extractWord(text, i)
					#if not isinstance(tempWord, bool):




	# If the parsed text ends with a docblock, rewind the ending id
	if docblockEnd:
		tempText = text[:i].strip()

		if tempText.endswith('*/'):
			endId = docblockOpen
		else:
			endId = i
	else:
		endId = i

	return result.strip(), endId, newLines

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
	extras = None

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


	def extract(self, text, startId = 0):

		a = datetime.datetime.now()

		if text[0] in [' ', '\t', '\n']:
			(result, newId, newLines) = self.extract(text[1:], 0)

			if text[0] == '\n':
				newLines += 1

			return result, newId+1, newLines

		# Shifting in extract messes things up
		#(text, exists) = shiftString(text, startId)

		pr('>>> Extracting ' + self.name + ' <<<')
		pr({'text': text[:50]})

		if self.greedy:
			return extractGreedy(text)
		else:

			# Get the beginning
			begin = self.begins

			# Get the new current id
			id = len(begin)

			# Text length
			textLength = len(text)

			# Remove the beginning
			rest = text[id:]

			
			pr({'rest': rest[:10]})

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
				if id == textLength:
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

				pr(' -- Get position ' + str(position) + ' named "' + str(targetName) + '"')

				if targetName == 'name':

					(result, endId, newLines) = extractName(text[id:])

					pr('Name')
					pr(result)

					# Store the result in the extractions
					extractions['name'] = {
						'name': result,
						'beginId': id,
						'endId': id+endId
					}

					# Set the next Id
					id = id+endId+1

				elif targetName == 'expression':

					(result, endId, newLines) = extractExpression(text[id:], expressionHasBegun, waitingForOperand)

					extractions['expression'] = {
						'text': result,
						'beginId': id,
						'endId': id+endId
					}

					id = id+endId+1

					expressionHasBegun = False
					waitingForOperand = False

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

					# If there were no curly braces
					# @todo: then get only 1 statement, the next one
					if not result and endId == 1:
						#(result, endId, newLines) = extractExpression(rest, True, True)
						#pr({'noblock': result})
						pass

					# Store the result in the extractions
					extractions['block'] = {
						'content': result,
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

		pr({'extracted': result, 'type': self.name})
		pr('Extract took ' + str(c.microseconds) + ' microseconds, or ' + str(Decimal(c.microseconds/1000000).quantize(Decimal('.01'), rounding=ROUND_DOWN)) + ' seconds')

		return result, startId+id-1, newLines

def extractName(text):

	pr({'ExtractName': text[:10]})

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
def extractGreedy(text):

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
			if hasCharsNext(text, self.ends, i):
				endAtId = i + (len(self.ends)-1)

		result += c
	
	endId = i

	return result, endId, newLines



statements = {}
expressions = {}

class Statement(LOC):

	type = 'statement'

	# Extra settings
	extras = {}

	def __init__(self, name):
		self.extras = {}
		self.name = name
		statements[name] = self
	

class Expression(LOC):

	type = 'expression'

	def __init__(self, name):
		self.extras = {}
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
var.setExtra(2, '=', True, 'expressionHasBegun')
var.setGroup(',')

function = Statement('function')
function.setBegin('function')
function.setName(1, False)
function.setParen(2, True)
function.setBlock(3, True)

## See if a char is a space or a tab
def isSpacing(char):
	if char == ' ' or char == '\t':
		return True
	return False

## See if a char is a space, a tab or a newline
def isWhitespace(char):
	if isSpacing(char) or char == '\n':
		return True

# Get the next statement/expression
def determineOpen(text, id):

	# Do not strip the text here,
	# It'll mess up the line numbers
	text = text[id:]

	pr({'checking': text[:10]})

	# Is it a statement?
	for name, stat in statements.items():

		# Strict means we don't care what comes after the opening tag
		if stat.greedy:
			if text.startswith(stat.begins):
				result, newId, newLines = stat.extract(text, id)
				return 'statement', name, id, newId+id, result, newLines
		else:
			if hasWordNext(text, stat.begins):
				pr('A statement called ' + name + ' begins at ' + str(id))
				result, newId, newLines = stat.extract(text, id)
				return 'statement', name, id, newId+id, result, newLines

	# It wasn't a statement, so try getting the expression
	(result, newId, newLines) = extractExpression(text)

	if result:
		return 'expression', 'expression', id, newId+id, result, newLines

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

	results = []

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
					results.append({'beginLine': lineNr, 'type': openType, 'typeName': openName, 'beginId': beginId, 'endId': endId, 'result': result, 'newlines': newLines})

					# Increase the line nr
					lineNr += newLines

					# 
					id = endId
					openType = False
		else:
			pass

		if cur == '\n':
			lineNr += 1

		id += 1

	pr('splitStatements has finished')

	for r in results:
		pr(r)


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
				pr('>> ' + str(next))
			if not recurse:
				pr(next)

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
			pr(x)

	return results

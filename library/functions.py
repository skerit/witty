#
# These functions are used throughout the Witty plugin,
# and are mainly for getting information out of code
#
import os, re, threading, pprint, json, pickle
test = 'hi'
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

# Find strings (even with escaped ' and ")
# Regex is actually (?<!\\)(?:(')|")(?(1)(\\'|[^'\r])+?'|(\\"|[^\r"])+?")
reStrings = re.compile(r'''(?<!\\)(?:(')|")(?(1)(\\'|[^'\r])+?'|(\\"|[^\r"])+?")''', re.M)

#
# Log Functions
#

# Prepare the pretty printer
pp = pprint.PrettyPrinter(indent=2)

# Create a dictionary for open files
openFiles = {}

# Log data to the given file in /dev/shm/ (memory fs)
def log(data, filename='workfile'):

	global openFiles

	if not filename in openFiles:
		openFiles[filename] = open('/dev/shm/' + filename, 'w')

	try:
		openFiles[filename].write('\n' + pp.pformat(data.__dict__))
	except AttributeError:
		openFiles[filename].write('\n' + pp.pformat(data))

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
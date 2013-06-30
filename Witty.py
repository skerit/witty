import sublime, sublime_plugin, os, re, threading, pprint
from os.path import basename

pp = pprint.PrettyPrinter(indent=2)
tfile = open('/tmp/workfile', 'w')

def log(data):
	tfile.write('\n' + pp.pformat(data))

is_array = lambda var: isinstance(var, (list, tuple))

# Match docblocks
reBlocks = re.compile('(\/\*(.*?)\*/)', re.M|re.S)

# Match descriptions
reDescription = re.compile('\/\*(.*?)[@|\/]', re.M|re.S)

# Docblock properties
reAt = re.compile('^.*?@(\w+)?[ \t]*(.*)', re.M)

# Simple single-line comments
reComment = re.compile('^\s*\/\/.*', re.M)

# Get the function name (not the assigned var!)
reFnName = re.compile('function\s+(\w*?)\s*?\(')

# Get assignment variable names
reANames = re.compile('(\S*?)\s*\=(?!\=)', re.M)

# All the completions
allCompletions = {}

class Content:

	def __init__(self, file_name):

		self.file_name = file_name

		# Clear out allCompletions entry for this file
		allCompletions[file_name] = []

		# Open the original file
		file_handler = open(file_name, 'rU')

		# Read in the original file
		self.original = file_handler.read()

		# Set the working string to empty
		self.working = ''

		# Create the scopes
		self.statements = []

		# Empty the blocks
		self.blocks = []

		self.root = {}

		# Parse the file
		self.parseFile()

	# Get all the docblocks inside the given text string
	def parseFile(self):

		# Find all the docblocks in the original string
		match = reBlocks.findall(self.original)

		self.blocks = []

		if (match):
			for match_tupple in match:
				self.blocks.append(match_tupple[0])

		# Remove all single line comments
		self.working = re.sub(reComment, '', self.original)

		# Replace all the existing docblocks with a placeholder for easy parsing
		self.working = re.sub(reBlocks, '//DOCBLOCK//', self.working)

		# Recursively parse all the statements
		statements = self.parseStatements(self.working, self.blocks)

		for s in statements:
			self.allVariables(s)

		return self.blocks

	def allVariables(self, statement):
		for i in statement['variables']:
			allCompletions[self.file_name].append((i + '\tTest\nNewline', i))

		if 'subblock' in statement:
			for s in statement['subblock']:
				self.allVariables(s)

		if 'subscope' in statement:
			for s in statement['subscope']:
				self.allVariables(s)

	def parseStatements(self, workingLines, docblocks):

		if not is_array(workingLines):
			# Turn the text into an array of lines
			workingLines = workingLines.split('\n')

		# Initial value: no statement is open
		statementIsBusy = False

		statements = []

		dbcount = 0
		dbnow = False

		# The running statement
		s = {}
		w = ''

		for line in workingLines:

			strippedLine = line.strip()

			# If the line is empty, continue to the next line
			if len(strippedLine) == 0:
				continue

			# If it's a docblock, keep it for the next statement!
			if strippedLine == '//DOCBLOCK//':
				dbnow = docblocks[dbcount]
				dbcount += 1
				continue

			# Do we need to create a new statement or is one already busy?
			if not statementIsBusy:
				s = {'docblock': '', 'line': '', 'docblocks': [], 'multiline': False}
				s['line'] = [strippedLine]
				w = line
			else:
				s['multiline'] = True
				s['line'].append(strippedLine)
				w += ' ' + line

			# If the statement is not busy (this includes if a statement is BEGINNING, even if it doesn't end)
			if dbnow:
				if not statementIsBusy:
					s['docblock'] = dbnow
				else:
					s['docblocks'].append(dbnow)

				# Reset the dbnow
				dbnow = False

			# Now see if the statement is finished
			oBracket = w.count('{')
			cBracket = w.count('}')

			if oBracket > cBracket:
				statementIsBusy = True
			else:
				statementIsBusy = False
				statements.append(s)

		results = []

		for stat in statements:
			results.append(self.parseStat(stat))

		return results

	def parseStat(self, statement):
		temp = self.guessLine(statement['line'][0])

		# Append the line info to the statement
		for name, value in temp.items():
			statement[name] = value

		# If the statement is a multiline
		if statement['multiline']:
			temp = statement['line'][:]

			# Remove the first entry
			del temp[0]

			if statement['function']:
				# Remove the last }
				#temp[len(temp)-1] = re.sub('}', '', len(temp)-1)

				statement['subscope'] = self.parseStatements(temp, statement['docblocks'])
			else:
				statement['subblock'] = self.parseStatements(temp, statement['docblocks'])
		
		return statement

	# Guess what a statement does (assignment or expression) and to what variables
	def guessLine(self, text):
		result = {'type': 'expression', 'variables': [], 'function': False, 'value': ''}

		eqs = text.count('=')

		if text.count('function') > 0:
			result['function'] = True

		# If there are no equal signs, it could be an expresison by default
		if eqs == 0:

			# See if it's a named function...
			if result['function']:

				# Get the function name, if it has one
				match = reFnName.match(text)

				if match and match.group(1):
					result['type'] = 'assignment'
					result['variables'].append(match.group(1))

		else:
			# Count the equal signs part of comparisons
			comparisons = text.count('===') * 3

			# Remove the triple equals
			temp = re.sub('===', '', text)

			# Count the equals
			comparisons += temp.count('==') * 2
			
			# If all the equal signs are part of comparisons, return the result
			if not eqs == comparisons:

				# Replace possible 'var' text
				temp = re.sub('var ', '', text)

				# Split the value we're assigning of
				split = temp.rsplit('=', 1)

				variables = reANames.findall(text)
				
				for varname in variables:
					if not varname.count('='):
						result['variables'].append(varname.strip())

				result['value'] = split[1]

				result['type'] = 'assignment'

		return result

	# Get the description inside the given docblock text
	def getDescription(self, text):
		description = self.description.match(text)

		if description:
			description = description.group(1)
			return re.sub('^\s?\*\s?', '', description, 0, re.M|re.S)
		else:
			return False

	# Get all the properties of a docblock
	def getProperties(self, text):
		match = self.at.findall(text)
		properties = {}

		for match_tupple in match:
			property_name = match_tupple[0].lower()

			if not (property_name in properties):
				properties[property_name] = []

			properties[property_name].append(match_tupple[1])

		return properties


class WittyParser(threading.Thread):

	def __init__(self, collector, origin_file, open_folder_arr, timeout_seconds):
		self.collector = collector
		self.timeout = timeout_seconds
		self.origin_file = origin_file
		self.open_folder_arr = open_folder_arr
		threading.Thread.__init__(self)

	def get_javascript_files(self, dir_name, *args):
		fileList = []
		for file in os.listdir(dir_name):
			dirfile = os.path.join(dir_name, file)
			if os.path.isfile(dirfile):
				fileName, fileExtension = os.path.splitext(dirfile)
				if fileExtension == ".js" and ".min." not in fileName:
					fileList.append(dirfile)
			elif os.path.isdir(dirfile):
				fileList += self.get_javascript_files(dirfile, *args)
		return fileList

	def save_method_signature(self, file_name):

		# If the filename is already present,
		# and it's not the file we just saved, skip it
		if file_name in allCompletions and file_name != self.origin_file:
			return

		nmCount = file_name.count('node_modules')
		mvcCount = file_name.count('alchemymvc')

		# Skip node_module files (except for alchemy)
		if nmCount and not mvcCount:
			return
		elif nmCount > 1 and mvcCount:
			return
		else:
			print('Witty: ' + file_name)
			results = Content(file_name)

	def run(self):
		print('Witty parser begins')
		#self.save_method_signature('/home/skerit/Projecten/alchemy-skeleton/node_modules/alchemymvc/lib/class/model.js')
		#return
		for folder in self.open_folder_arr:
			jsfiles = self.get_javascript_files(folder)
			for file_name in jsfiles:
				self.save_method_signature(file_name)

		print('Witty parser is finished')

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

class WittyCommand(sublime_plugin.EventListener):

	_parser_thread = None

	def on_post_save(self, view):
		open_folder_arr = view.window().folders()
		#if self._parser_thread != None:
		#	self._parser_thread.stop()
		self._parser_thread = WittyParser(self, view.file_name(), open_folder_arr, 30)
		print('Witty parser is starting...')
		self._parser_thread.start()

	def on_modified(self, view):
		# This runs on every keypress
		#print("Testing on_modified")
		#view.show_popup_menu(["moeder"], False)
		return None

	def on_query_context(self, view, key, operator, operand, match_all):
		return None

	def on_query_completions(self, view, prefix, locations):
		#print('Auto completing...')

		current_file = view.file_name()

		#print(current_file)

		# Get the region
		region = view.sel()[0]

		# Get the point position of the cursor
		point = region.begin()
		(row,col) = view.rowcol(point)

		# Get the current line
		full_line = view.substr(view.line(region))

		# Get the line up to the cursor
		left_line = full_line[:col].strip()

		# Get the line after the cursor
		right_line = full_line[col:].strip()

		# Get the better prefix
		brefix = getBetterPrefix(left_line)

		completions = [("EXTRA\textra\ttest", "EXTRA"), ("ELANGERBTERTESTS\t veel langere text\ttest", "LANG")]
		try:
			completions = allCompletions[current_file]
		except KeyError:
			print('Key not found: ' + current_file)
			pass
		
		sublime.status_message('Auto completing "' + brefix + '"')

		# INHIBIT_WORD_COMPLETIONS = 8 = Only show these completions
		# INHIBIT_EXPLICIT_COMPLETIONS = 16 = ?
		return (completions, sublime.INHIBIT_WORD_COMPLETIONS)
	

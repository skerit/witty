import threading, os, sublime, sublime_plugin
from os.path import basename
import Witty.library.functions as wf
from Witty.library.WittyFile import WittyFile

# Debug wrappers
def warn(message, showStack = True): wf.warn(message, showStack, 3)
def info(message, showStack = True): wf.info(message, showStack, 3)
def pr(message, showStack = True): wf.pr(message, showStack, 3)

#
# WittyParser has to take the original text files
# and convert them to something we can use later on
#
class WittyParser(threading.Thread):

	def __init__(self, project, originFile):
		self.project = project
		self.originFile = originFile
		threading.Thread.__init__(self)

	# Function that begins the thread
	def run(self):
		
		# Loop through every folder in the project
		for folder, data in self.project.folders.items():
			# Get all the javascript files in the project
			jsFiles = self.getJavascriptFiles(folder)
			for fileName in jsFiles:
				self.startFileParse(fileName)

		sublime.status_message('Witty has finished parsing')

		# Fire the postParse function for both languages
		self.project.intelNode.postParse()
		self.project.intelBrowser.postParse()

		# Store the data on disk
		self.project.storeOnDisk()

	# Get all javascript files (ending with .js, not containing .min.)
	def getJavascriptFiles(self, dir_name, *args):
		fileList = []
		for file in os.listdir(dir_name):
			dirfile = os.path.join(dir_name, file)
			if os.path.isfile(dirfile):
				fileName, fileExtension = os.path.splitext(dirfile)
				if fileExtension == ".js" and ".min." not in fileName:
					fileList.append(dirfile)
			elif os.path.isdir(dirfile):
				fileList += self.getJavascriptFiles(dirfile, *args)
		return fileList

	# Parse the given file and return a new WittyFile object or False
	def startFileParse(self, fileName):

		if not wf.isJavascriptFile(fileName):
			return False

		# If the filename is already present,
		# and it's not the file we just saved, skip it
		if self.project.hasFileData(fileName) and fileName != self.originFile:
			return False

		nmCount = fileName.count('node_modules')
		mvcCount = fileName.count('alchemymvc')

		# Skip node_module files (except for alchemy)
		if nmCount and not mvcCount:
			return False
		elif nmCount > 1 and mvcCount:
			return False
		else:
			sublime.status_message('Witty is parsing: ' + fileName)
			info('Parsing file "' + fileName + '"')

			fileResult = WittyFile(self.project, fileName)

			# If we got a new WittyFile instance, store it in the project
			if fileResult:

				if fileResult.language == 'nodejs':
					self.project.intelNode.files[fileName] = fileResult
				else:
					self.project.intelBrowser.files[fileName] = fileResult

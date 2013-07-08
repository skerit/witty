import sublime, sublime_plugin, re, json, imp, sys

# For development purposes
settings = sublime.load_settings("Preferences.sublime-settings")

# Default debug setting
doDebug = False

# Development stuff
if settings.get('env') == 'dev':
	reloadModules = []
	doDebug = True

	# Make sure all the modules are removed from cache
	for name, value in sys.modules.items():
		try:
			cache = value.__dict__['__cached__']
			if cache and cache.lower().count('witty'):
				if not name == 'Witty.Witty':
					reloadModules.append(name)
		except KeyError:
			pass

	for moduleName in reloadModules:
		del sys.modules[moduleName]

	for key in reloadModules:
		newmodule = __import__(key)

from Witty.library.WittyProject import WittyProject
from Witty.library.WittyProject import Intel
from Witty.library.WittyParser import WittyParser
from Witty.library.WittyFile import WittyFile
from Witty.library.WittyScope import WittyScope
from Witty.library.WittyScope import WittyRoot
from Witty.library.WittyStatement import WittyStatement
from Witty.library.WittyVariable import WittyVariable
from Witty.library.Docblock import Docblock
import Witty.library.functions as wf

# Witty only completions?
wittyOnly = settings.get('wittyonly')

# Set the debug level, default to 0
wf.debugLevel = settings.get('wittylevel') or 0
wf.doDebug = doDebug

# Debug wrappers
def warn(message, showStack = True): wf.warn(message, showStack, 3)
def info(message, showStack = True): wf.info(message, showStack, 3)
def pr(message, showStack = True): wf.pr(message, showStack, 3)

# Remove all the types of a certain file
def clear_types_file(filename):
	for key, value in allTypes.items():
		if value['filename'] == filename:
			del allTypes[key]


# The Witty entrance
class WittyCommand(sublime_plugin.EventListener):

	_parser_thread = None

	def __init__(self):

		self.allProjects = {}

		for window in sublime.windows():
			newProject = WittyProject(window.folders())
			self.allProjects[newProject.id] = newProject

			info('\n\n', False)
			info('New project created (' + str(newProject.id) + ')')
	
	# Get the project ID based on the view
	def getProjectId(self, view):
		projectFolders = view.window().folders()
		return wf.generateHash(projectFolders)

	# Get the project
	def getProject(self, view):
		projectId = self.getProjectId(view)

		if projectId in self.allProjects:
			return self.allProjects[projectId]
		else:
			return False


	# After saving a file, reparse it
	def on_post_save_async(self, view):
		
		savedFileName = view.file_name()

		if savedFileName.count('Witty.py'):
			return False

		# Get the project
		project = self.getProject(view)

		if project:
			project.parseFiles(savedFileName)

	# Query completions
	def on_query_completions(self, view, prefix, locations):

		project = self.getProject(view)

		if project:
			return project.queryForCompletions(view, prefix, locations)
	
class WittyReindexProjectCommand(sublime_plugin.ApplicationCommand):

	def run(self):
		# This actually gets the wrong window, so it doesn't do anything yet
		open_folder_arr = sublime.windows()[0].folders()
		#if self._parser_thread != None:
		#	self._parser_thread.stop()
		self._parser_thread = WittyParser(self, False, open_folder_arr, 30)
		
		self._parser_thread.start()
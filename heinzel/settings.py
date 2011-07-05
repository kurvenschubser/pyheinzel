import sys, os
from os import sep


DEBUG = False

DEFAULT_ENCODING = "utf-8"


######################### Database related ########################
DBNAME = "test.db"
DB_SAVE_PATH = os.path.abspath(__file__)
CACHE = True
MAX_CACHE = 1000
FORCE_CREATE_TABLE = True

# A RelationField's related_name will be set to RELATED_NAME_PREFIX +
# model_class.__name__.lower() + RELATED_NAME_POSTFIX by default
RELATED_NAME_PREFIX = ""
RELATED_NAME_POSTFIX = "_set"


## XXX: unused?
###########################    heinzel    #########################
##                       !DO NOT INTERFERE!                      ##
# Do not set directly, use `set_project` instead
PROJECT_NAME = "aaa"


def set_project(path):
	#print "set_project path", path
	dir, file = os.path.split(path)
	#print "set_project dir, file", dir, file
	base, project = os.path.split(dir)
	
	assert len(project.split(".")) == 1, "A project folder may not contain any dots! Please rename the folder."
	
	# Make modules under `base` importable
	sys.path.append(base)
	
	# Set this settings.PROJECT_NAME to `project`
	module = sys.modules[__name__]
	#print "set_prject module", module
	#print "set project project", project
	setattr(module, "PROJECT_NAME", project)
	#print "set_project PROJECT_NAME", getattr(module, "PROJECT_NAME")


def get_module(mod_name):
	# import module
	module = __import__(mod_name)
	# Get to the desired module
	if len(mod_name.split(".")) > 1:
		# ...[1:] because the first item in the list already is in `module`, 
		# so the traversing needs to start right after it
		for attr in mod_name.split(".")[1:]:
			module = getattr(module, attr)
	return module

def set_vars(module=None, **kwargs):
	module = get_module(module or __name__)
	for name, value in kwargs.items():
		setattr(module, name, value)

def get_vars(module=None, exclude=[]):
	module = get_module(module or __name__)
	exclude = exclude or ("os", "sys", "sep")

	d = {}
	for name in dir(module):
		if not name in exclude or not name.startswith("_"):
			attr = getattr(module, name)
			if not callable(attr):
				d[name] = attr
	return d

##                       !DO NOT INTERFERE!                      ##
###########################    heinzel    #########################

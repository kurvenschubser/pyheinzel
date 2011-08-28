import os
import re

try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup


## VERSION = re.search('version = "([^"]+)"',
## 					open("heinzel/__init__.py").read()).group(1)


def find_packages():
	# implement a simple find_packages so we don't have to depend on
	# setuptools
	packages = []
	for directory, subdirectories, files in os.walk("heinzel"):
		if '__init__.py' in files:
			packages.append(directory.replace(os.sep, '.'))
	return packages


setup(
	name="heinzel",
	version=VERSION,
	description=("Object relational mapper (ORM), influenced by "
					"Django's and the Storm ORM."),
	author="Malte Engelhardt",
	author_email="kurvenschubser@googlemail.com",
	packages=find_packages(),
	package_data={
		"": ["*.txt"]
	},
	install_requires=["pytz"]
)


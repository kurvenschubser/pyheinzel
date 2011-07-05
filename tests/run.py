import os, sys
from unittest import TestCase, TestSuite
from optparse import OptionParser

from utils import runtests
from heinzel.core.utils import import_helper


def get_all_modules():
	for fname in filter(lambda f: f.endswith("py"), os.listdir(os.path.abspath("."))):
		yield fname[:-3]


def get_module_tests(modname):
	mod = import_helper(modname)
	modattrs = [attr for attr in dir(mod) if not attr.startswith("__")]
	
	tests = []
	for objname in modattrs:
		test = get_test(modname, objname)
		if test is not None:
			tests.append(test)
	return tests


def is_test(test):
	return (
			(
				isinstance(test, type)
				and issubclass(test, TestCase)
				and getattr(test, "runTest", False) is not False
			) or (
				isinstance(test, type)
				and issubclass(test, TestSuite)
				and getattr(test, "run", False) is not False
			)
		)


def get_test(pkgname, testname):
	test = import_helper(pkgname, testname)

	if is_test(test):
		return test


def get_tests(test_or_mod_names):
	tests = []
	for test_or_mod_name in test_or_mod_names:
		try:
			pkgname, testname = test_or_mod_name.rsplit(".", 1)
		except ValueError:
			pkgname, testname = test_or_mod_name, None

		# Get all tests of one module ...
		if testname is None or testname == "*":
			tests.extend(get_module_tests(pkgname))
		# ... or a specified one.
		else:
			tests.append(get_test(pkgname, testname))
	return tests


if __name__ == "__main__":
	p = OptionParser()
	p.add_option("-t", "--tests", action="append", metavar="TESTS",
		help="Any tests specified in the manner 'pkgname.testname' or "\
			"'testname' will be added to the tests, except when TESTALL "\
			"is specified. Then, all tests specified with this option "\
			"will be excluded from testing.",
		default=[]
	)
	p.add_option("-a", "--testall", action="store_true", default=False, 
		help="Test all tests in modules in the same folder as run.py, "\
			"except for those specified by TESTS.",
		metavar="TESTALL"
	)
	p.add_option("-v", "--verbosity", action="store", default=2, help="One of (1,2,3).")

	opts, args = p.parse_args()

	tests = opts.tests
	if args:
		tests.extend(args)
	
	negate = opts.testall

	if negate:
		exclude = tests
		tests = get_all_modules()
	else:
		exclude = []

	
		
	for t in tests:
		print t, type(t)
		if t in exclude:
			continue

		runtests(get_tests([t]), verbosity=opts.verbosity)

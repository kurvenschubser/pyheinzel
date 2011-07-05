import os
import unittest
import time



class Fixture(unittest.TestCase):
	
	def setUp(self):
		from heinzel.maintenance import syncdb
		from heinzel import settings

		if os.path.exists(os.path.abspath(settings.DBNAME)):
			os.remove(settings.DBNAME)

		from heinzel.core import models
		syncdb(models.registry, settings.DBNAME)

	def tearDown(self):
		self.closeDB()
		self.closeCache()

		from heinzel import settings

		if os.path.exists(os.path.abspath(settings.DBNAME)):
			os.remove(settings.DBNAME)

	def closeDB(self):
		from heinzel.core import connection
		conn = connection.connect()
		conn.close()

	def closeCache(self):
		from heinzel.core.queries import storage
		storage.clear()

	def check_db(self):
		raw_input('\nCheck database\n\n')


def runtests(tests=None, **options):
	if tests is None: return
		
	suite = unittest.TestSuite()
	for t in tests:
		suite.addTest(t())

	unittest.TextTestRunner(verbosity=options.get("verbosity", 2)).run(suite)


def stopwatch(func, *args, **kwargs):
	start = time.time()

	if args and not kwargs:
		func(*args)
	elif args and kwargs:
		func(*args, **kwargs)
	elif not args and not kwargs:
		func()
	elif not args and kwargs:
		func(**kwargs)

	return time.time() - start

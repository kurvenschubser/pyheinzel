#schnuckenack-test.py
import unittest, os

from utils import Fixture, runtests

from model_examples import Car, Brand, Manufacturer, Driver, Key
from heinzel.core import models


models.register([Car, Brand, Manufacturer, Driver, Key])

DBNAME = "test.db"


class TestMisc(Fixture):

	def runTest(self):
		test_underscore = Car(name="Test_underscore")
		test_underscore.save()

		self.assert_(Car.objects.filter(name="Test_underscore")[0] is test_underscore)

		
if __name__ == "__main__":
	alltests = (
		TestMisc,
	)
	runtests(alltests)

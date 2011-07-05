# encoding: utf-8


from utils import Fixture, runtests
from heinzel.core.exceptions import DoesNotExist
from heinzel.core import utils

from model_examples import Actor, Movie, Car, Brand, Manufacturer, Driver, Key
from heinzel.core import models


models.register([Actor, Movie])


class TestSelectQuery(Fixture):
	def runTest(self):
		pass
		
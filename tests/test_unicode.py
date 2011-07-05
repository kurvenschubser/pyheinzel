# encoding: utf-8


from utils import Fixture, runtests
from heinzel.core.exceptions import DoesNotExist

from model_examples import Actor, Movie, Car, Brand, Manufacturer, Driver, Key
from heinzel.core import models


models.register([Actor, Movie])



class TestUnicode(Fixture):
	def runTest(self):
		houseflydag, created = Movie(title="十面埋伏").save()
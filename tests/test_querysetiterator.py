# -*- coding: utf-8 -*-

from utils import Fixture, runtests
from heinzel.core.exceptions import DoesNotExist, SQLSyntaxError
from heinzel.core import utils


from model_examples import (
	Actor, Movie, Car, Brand, Manufacturer, Driver, Key, Item
)
from heinzel.core.sql.dml import (Avg, Max, Min, Count, Sum)
from heinzel.core import models


models.register([Actor, Movie, Item])

from heinzel.core.queries import storage as store


class GetItemTest(Fixture):
	def runTest(self):
		for i in xrange(100):
			Item.objects.create(name="item_nr_%i" % i)

		self.assert_(list(Item.objects.filter(pk__lt=51)) 
						== Item.objects.all()[:50])

		self.assert_(list(Item.objects.filter(pk__gt=50))
						== Item.objects.all()[50:])

		# test stepping
		self.assert_(list(Item.objects)[::2]
						== Item.objects.all()[::2])

		# test reversing
		self.assert_(list(Item.objects)[-1:-101:-1]
						== Item.objects.all()[-1:-101:-1])


if __name__ == "__main__":
	alltests = (
		GetItemTest,
	)


	runtests(alltests, verbosity=3)

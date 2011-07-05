# -*- coding: utf-8 -*-

from heinzel.core import models
from heinzel.core import exceptions
from heinzel.tests.utils import Fixture, runtests


from model_examples import Car, Brand, Manufacturer, Driver, Key


models.register([Manufacturer, Brand, Car, Driver, Key])


#debug
from heinzel.core.queries import queryset_storage as store


class save(Fixture):
	def runTest(self):
		vw = Brand(name="Volkswagen")
		vw.save()
		
		self.assert_(Brand.objects.get(name__startswith="V") is vw)


class delete(Fixture):
	def runTest(self):
		vw = Brand(name="Volkswagen")
		vw.save()
		
		self.assert_(Brand.objects.get(name__startswith="V") is vw)
		
		vw.delete()
		
		self.assertRaises(exceptions.DoesNotExist, Brand.objects.get, name__startswith="V")


if __name__ == "__main__":
	alltests = (
		save,
		delete,
		
		#! implement
		# reset,
		# undo,
		# redo,
		
	)

	runtests(tests=alltests, verbosity=3)

# -*- coding: utf-8 -*-



from utils import Fixture, runtests

from model_examples import Car, Brand, Manufacturer, Driver, Key
from heinzel.core import models

models.register([Manufacturer, Brand, Car, Driver, Key])



class TestUncache(Fixture):
	def runTest(self):	
		b = Brand(name="Foo")
		b.uncache()
		
		from heinzel.core.queries import storage
		self.assert_(
			storage._alive.get((Brand, b._inst_info.get_pk_as_key())) \
			is None
		)

		self.assert_(storage._dirty.get(b._inst_info) is None)

		self.assert_(not b._inst_info in storage._cache)
		
		b.save()
		
		self.assert_(
			storage._alive.get((Brand, b._inst_info.get_pk_as_key())) \
			is None
		)

		self.assert_(storage._dirty.get(b._inst_info) is None)

		self.assert_(not b._inst_info in storage._cache)
		
		self.assert_(b.pk == 1)
		
		b2 = Brand.objects.get(name="Foo")
		self.assert_(b2 is not b)
		self.assert_(b2.pk == b.pk)
		
		self.assert_(map(id, Brand.objects.all()) == [id(b2)])
		
		



if __name__ == "__main__":
	alltests = (
		TestUncache,
	)

	runtests(tests=alltests, verbosity=3)
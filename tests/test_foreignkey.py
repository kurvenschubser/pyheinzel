# -*- coding: utf-8 -*-

"""Please see file ‘test_relations‘ for an explanation of what's being tested
below."""

from utils import Fixture, runtests

from model_examples import Car, Brand, Manufacturer, Driver, Key
from heinzel.core import models

models.register([Manufacturer, Brand, Car, Driver, Key])



class Populate(Fixture):
	def runTest(self):	
		vwgruppe = Manufacturer(name="VWGruppe")
		vwgruppe.save()
		
		vw = Brand(name="VW")
		vw.save()
		vw.manufacturer = vwgruppe
		
		golf = Car(name="Golf")
		golf.save()
		golf.brand = vw
		
		bulli = Car(name="Bulli")
		bulli.save()
		bulli.brand = vw
		
		kaefer = Car(name=u"Käfer")
		kaefer.save()
		kaefer.brand = vw


class Get(Fixture):
	def runTest(self):
		
	
		vwgruppe = Manufacturer(name="VWGruppe")
		vwgruppe.save()

		vw = Brand(name="VW")
		vw.save()
		vw.manufacturer = vwgruppe
		
		golf = Car(name="Golf")
		golf.save()
		golf.brand = vw
		
		bulli = Car(name="Bulli")
		bulli.save()
		bulli.brand = vw
		
		kaefer = Car(name=u"Käfer")
		kaefer.save()
		kaefer.brand = vw

		# db setup complete

		self.assert_(vw is Brand.objects.get(name="VW"))
		
		self.assert_(kaefer.brand is vw)	

		self.assert_(kaefer.brand.car_set[-1] is kaefer)
		self.assert_(kaefer.brand.car_set[-1].brand is vw)
		self.assert_(kaefer.brand.manufacturer is vwgruppe)
		self.assert_(kaefer.brand.car_set[0].brand.manufacturer is vwgruppe)
		
		self.assert_(vwgruppe.brand_set[0] is vw)
		self.assert_(vwgruppe.brand_set[0].car_set[1] is bulli)
		self.assert_(vwgruppe.brand_set[0].car_set[1].brand.manufacturer is vwgruppe)
		

class Set(Fixture):
	def runTest(self):
		vwgruppe = Manufacturer(name="VWGruppe")
		vwgruppe.save()
		
		vw = Brand(name="VW")
		vw.save()
		vw.manufacturer = vwgruppe	
		
		golf = Car(name="Golf")
		golf.save()
		golf.brand = vw
		
		bulli = Car(name="Bulli")
		bulli.save()
		bulli.brand = vw
		
		kaefer = Car(name=u"Käfer")
		kaefer.save()
		kaefer.brand = vw

		# db setup complete

		# When setting a different foreign key, the formerly set foreign key
		# will be removed from the ReverseForeignKeyManager as well.
		# -> Make a new potential foreign key instance
		audi = Brand(name="Audi")
		audi.save()
		
		# Set the new foreign key on the ForeignKeyManager
		kaefer.brand = audi
		
		self.assert_(kaefer.brand is audi)
		self.assert_(kaefer not in vw.car_set)
		
		# golf and bulli are still part of vw.car_set
		self.assert_(golf in vw.car_set)
		self.assert_(bulli in vw.car_set)
		
		# Setting cars on a ReverseForeignKeyManager first removes all
		# entries from the relation, then adds the desired cars to brand.
		vw.car_set = [kaefer]
		
		# vw is now kaefer's brand again ...
		self.assert_(kaefer.brand is vw)
		self.assert_(kaefer in vw.car_set)
		
		# The other cars have been removed from the relation ...
		self.assert_(golf.brand is None)
		self.assert_(bulli.brand is None)
		
		# ... and Brand 'audi' is not related to car kaefer anymore, because a
		# Car can only have one Brand.
		self.assert_(len(audi.car_set) == 0)
		
		# You can use the ReverseForeignKeyManager.set method explicitly.
		audi.car_set.set([bulli, golf])
		
		self.assert_(bulli in audi.car_set)
		self.assert_(golf in audi.car_set)
		self.assert_(bulli.brand is audi)
		self.assert_(golf.brand is audi)


class Add(Fixture):
	def runTest(self):
		vwgruppe = Manufacturer(name="VWGruppe")
		vwgruppe.save()
		
		vw = Brand(name="VW")
		vw.save()
		vw.manufacturer = vwgruppe
		
		golf = Car(name="Golf")
		golf.save()
		
		
		bulli = Car(name="Bulli")
		bulli.save()
		
		
		kaefer = Car(name=u"Käfer")
		kaefer.save()
		
		# db setup complete
		
		# Adding on foreign key relationships only works in the reverse
		# direction:
		# Car.brand only ever holds one Brand instance, only setting is
		# supported.
		# But Brand.car_set can hold multiple Cars, so adding works here.
		vw.car_set.add([golf, kaefer, bulli])
		
		self.assert_(golf in vw.car_set)
		self.assert_(kaefer in vw.car_set)
		self.assert_(bulli in vw.car_set)
		
		self.assert_(golf.brand is vw)
		self.assert_(bulli.brand is vw)
		self.assert_(kaefer.brand is vw)
		

class Delete(Fixture):
	"""Delete all related items from the relationship."""
	
	def runTest(self):
		vwgruppe = Manufacturer(name="VWGruppe")
		vwgruppe.save()
		
		vw = Brand(name="VW")
		vw.save()
		vw.manufacturer = vwgruppe
		
		golf = Car(name="Golf")
		golf.save()
		golf.brand = vw
		
		bulli = Car(name="Bulli")
		bulli.save()
		bulli.brand = vw
		
		kaefer = Car(name=u"Käfer")
		kaefer.save()
		kaefer.brand = vw

		# db setup complete
		
		# delete
		del golf.brand
		
		self.assert_(golf.brand is None)
		self.assert_(golf not in vw.car_set)
		
		del vw.car_set
		self.assert_(bulli.brand is None)
		self.assert_(kaefer.brand is None)
		self.assert_(bulli not in vw.car_set)
		self.assert_(kaefer not in vw.car_set)


class Remove(Fixture):
	def runTest(self):
		vwgruppe = Manufacturer(name="VWGruppe")
		vwgruppe.save()
		
		vw = Brand(name="VW")
		vw.save()
		vw.manufacturer = vwgruppe
		
		golf = Car(name="Golf")
		golf.save()
		golf.brand = vw
		
		bulli = Car(name="Bulli")
		bulli.save()
		bulli.brand = vw
		
		kaefer = Car(name=u"Käfer")
		kaefer.save()
		kaefer.brand = vw
		
		# Removing only works ReverseForeignKeyManagers. Instances-to-be-
		# removed will be removed from the relationship.
		vw.car_set.remove([golf])
		
		self.assert_(golf not in vw.car_set)
		self.assert_(golf.brand is None)
		
		self.assert_(list(vw.car_set) == [bulli, kaefer])
		


if __name__ == "__main__":
	alltests = (
		Populate,
		Get,
		Set,
		Add,
		Delete,
		Remove,
	)

	runtests(tests=alltests, verbosity=3)
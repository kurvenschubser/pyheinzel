# -*- coding: utf-8 -*-

from heinzel.core import models
from heinzel.core import exceptions
from heinzel.tests.utils import Fixture, runtests


from model_examples import Car, Brand, Manufacturer, Driver, Key


models.register([Manufacturer, Brand, Car, Driver, Key])


class BasicAssumptions(Fixture):
	def runTest(self):

		bmwgroup = Manufacturer(name="Bayerische Motoren Werke AG")
		bmwgroup.save()
		
		bmw = Brand(name="BMW")
		bmw.save()
		
		bmw.manufacturer = bmwgroup
		
		bmw3er = Car(name="3er")
		bmw7er = Car(name="7er")
		bmwX3 = Car(name="X3")
		
		bmw3er.save()
		bmw7er.save()
		bmwX3.save()
		
		bmw3er.brand = bmw
		bmw7er.brand = bmw
		bmwX3.brand = bmw
		
		daimlergroup = Manufacturer(name="Daimler AG")
		daimlergroup.save()
		
		benz = Brand(name="Mercedes Benz")
		benz.save()
		
		benz.manufacturer = daimlergroup
		
		benzT = Car(name="T Modell")
		benzGLK = Car(name="GLK")
		benzSLK = Car(name="SLK")
		
		benzT.save()
		benzGLK.save()
		benzSLK.save()
		
		benzT.brand = benz
		benzGLK.brand = benz
		benzSLK.brand = benz
		
		
		harry = Driver(first_name="Harry", last_name="Klein")
		ayrton = Driver(first_name="Ayrton", last_name="Senna")
		
		harry.save()
		ayrton.save()
		
		harry.cars = [benzT, bmw3er, bmwX3]
		ayrton.cars.add([benzGLK, benzSLK, bmw7er, bmwX3])
		
		benzTkey = Key(serial=12)
		benzTkey.save()
		
		bmwX3key = Key(serial=10039)
		bmwX3key.save()
		
		benzTkey.owner = harry
		bmwX3key.owner = ayrton


class all(Fixture):
	def runTest(self):
		bmwgroup = Manufacturer(name="Bayerische Motoren Werke AG")
		bmwgroup.save()
		
		bmw = Brand(name="BMW")
		bmw.save()
		
		bmw.manufacturer = bmwgroup
		
		bmw3er = Car(name="3er")
		bmw7er = Car(name="7er")
		bmwX3 = Car(name="X3")
		
		bmw3er.save()
		bmw7er.save()
		bmwX3.save()
		
		bmw3er.brand = bmw
		bmw7er.brand = bmw
		bmwX3.brand = bmw
		
		daimlergroup = Manufacturer(name="Daimler AG")
		daimlergroup.save()
		
		benz = Brand(name="Mercedes Benz")
		benz.save()
		
		benz.manufacturer = daimlergroup
		
		benzT = Car(name="T Modell")
		benzGLK = Car(name="GLK")
		benzSLK = Car(name="SLK")
		
		benzT.save()
		benzGLK.save()
		benzSLK.save()
		
		benzT.brand = benz
		benzGLK.brand = benz
		benzSLK.brand = benz
		
		
		harry = Driver(first_name="Harry", last_name="Klein")
		ayrton = Driver(first_name="Ayrton", last_name="Senna")
		
		harry.save()
		ayrton.save()
		
		harry.cars = [benzT, bmw3er, bmwX3]
		ayrton.cars.add([benzGLK, benzSLK, bmw7er, bmwX3])
		
		benzTkey = Key(serial=12)
		benzTkey.save()
		
		bmwX3key = Key(serial=10039)
		bmwX3key.save()
		
		benzTkey.owner = harry
		bmwX3key.owner = ayrton
		
		#db setup complete
		
		# all returns all instances of a Model
		allcars = list(Car.objects.all())
		
		self.assert_(allcars == [bmw3er, bmw7er, bmwX3, benzT, benzGLK, benzSLK])
		
		alldrivers = list(Driver.objects.all())
		
		self.assert_(alldrivers == [harry, ayrton])


class filter(Fixture):
	"""
	The Manager.filter method facilitates searching the database with 
	filtering conditions. Available filters are:

		startswith
		endswith
		contains
		gt
		gte
		lt
		lte
		exact
		in
		between
	"""
	
	def runTest(self):
		bmwgroup = Manufacturer(name="Bayerische Motoren Werke AG")
		bmwgroup.save()
		
		bmw = Brand(name="BMW")
		bmw.save()
		
		bmw.manufacturer = bmwgroup
		
		bmw3er = Car(name="3er")
		bmw7er = Car(name="7er")
		bmwX3 = Car(name="X3")
		
		bmw3er.save()
		bmw7er.save()
		bmwX3.save()
		
		bmw3er.brand = bmw
		bmw7er.brand = bmw
		bmwX3.brand = bmw
		
		daimlergroup = Manufacturer(name="Daimler AG")
		daimlergroup.save()
		
		benz = Brand(name="Mercedes Benz")
		benz.save()
		
		benz.manufacturer = daimlergroup
		
		benzT = Car(name="T Modell")
		benzGLK = Car(name="GLK")
		benzSLK = Car(name="SLK")
		
		benzT.save()
		benzGLK.save()
		benzSLK.save()
		
		benzT.brand = benz
		benzGLK.brand = benz
		benzSLK.brand = benz
		
		
		harry = Driver(first_name="Harry", last_name="Klein")
		ayrton = Driver(first_name="Ayrton", last_name="Senna")
		
		harry.save()
		ayrton.save()
		
		harry.cars = [benzT, bmw3er, bmwX3]
		ayrton.cars.add([benzGLK, benzSLK, bmw7er, bmwX3])
		
		benzTkey = Key(serial=12)
		benzTkey.save()
		
		bmwX3key = Key(serial=10039)
		bmwX3key.save()
		
		benzTkey.owner = harry
		bmwX3key.owner = ayrton
		
		keys = []
		
		for x in range(10):
			k = Key(serial=x)
			k.save()
			keys.append(k)

		
		drivernames = (
			("Mina", "da Silva Sanches"),
			("Gundula", "Gause"), 
			("Sandra", "Maischberger"), 
			("Bruno", "Gaspard"), 
			("Hermi", "Tock"), 
			("Willi", "Gunther"),
			("Gisbert", "Geier")
		)
		
		drivers = []
		
		for f, l in drivernames:
			d = Driver(first_name=f, last_name=l)
			d.save()
			drivers.append(d)
			
		#db setup complete
		
		# make a search for certain attributes of a Model
		# startswith
		qs = Driver.objects.filter(last_name__startswith="G")
		self.assert_(list(qs) == [drivers[1], drivers[3], drivers[5], drivers[6]])
		
		# endswith
		qs = Car.objects.filter(name__endswith="er")
		self.assert_(list(qs) == [bmw3er, bmw7er])
		self.assert_(list(qs)[0].name == "3er")
		self.assert_(list(qs)[1].name == "7er")
		
		# contains
		qs = Driver.objects.filter(last_name__contains="aspa")
		self.assert_(list(qs) == [drivers[3]] and list(qs)[0].first_name == "Bruno")
		
		# gt
		qs = Key.objects.filter(serial__gt=8)
		self.assert_(list(qs) == [benzTkey, bmwX3key, keys[9]])
		
		# gte
		qs = Key.objects.filter(serial__gte=8)
		self.assert_(list(qs) == [benzTkey, bmwX3key, keys[8], keys[9]])
		
		# lt
		qs = Key.objects.filter(serial__lt=3)
		self.assert_(list(qs) == [keys[0], keys[1], keys[2]])

		# lte
		qs = Key.objects.filter(serial__lte=3)
		self.assert_(list(qs) == [keys[0], keys[1], keys[2], keys[3]])
		
		# exact
		qs = Car.objects.filter(name__exact="3er")
		self.assert_(list(qs) == [bmw3er])
		
		# in
		qs = Key.objects.filter(serial__in=(1,3,5))
		self.assert_(list(qs) == [keys[1], keys[3], keys[5]])
		
		# between
		qs = Key.objects.filter(serial__between=(3, 1))
		self.assert_(list(qs) == [keys[2]])
		
		qs = Key.objects.filter(serial__between=(3, 5))
		self.assert_(list(qs) == [keys[4]])
		


class exclude(Fixture):
	def runTest(self):
		pass


class get(Fixture):
	def runTest(self):
		pass


class create(Fixture):
	def runTest(self):
		pass


class get_or_create(Fixture):
	def runTest(self):
		pass


class rollback(Fixture):
	def runTest(self):
		pass


if __name__ == "__main__":
	alltests = (
		all,
		#filter,
		# exclude,
		# get,
		# create,
		# get_or_create,
		
		
		#! implement
		# rollback,
		
	)

	runtests(tests=alltests, verbosity=3)
import datetime


from utils import Fixture, runtests

from heinzel.core import models
from heinzel.core.utils import datetime_localize


class Car(models.Model):
	name = models.TextField(max_length=100, initial="Bug")
	depreciation_total = models.FloatField(initial=0.0)
	build_date = models.DatetimeField(initial=datetime.datetime.now)
	last_checkup = models.DatetimeField()
	
	#in the future, cars will have their own IP address, says everybody.
	ip_address = models.IPv6Field()
	
	


models.register([Car])


class TestFieldInitial(Fixture):
	def runTest(self):
		bug = Car().save()[0]
		self.assert_(bug.name == "Bug")


class TestFloatFieldInitial(Fixture):
	def runTest(self):
		bug = Car().save()[0]		
		self.assert_(bug.depreciation_total == 0.0)


class TestDatetimeField(Fixture):
	def runTest(self):
		now = datetime.datetime.now()
		earlier = datetime.datetime(1975, 3, 12, 9,53, 57)

		jag = Car(
			name="Jaguar",
			build_date=earlier,
			last_checkup=now
		)
		jag.save()

		def compdates(dt1, dt2):
			return dt1 == dt2

		# A TypeError will be raised because earlier is not timezone aware
		# whereas jag.build_date was implicitly localized automatically.
		# They are not the same objects!
		self.assertRaises(TypeError, compdates, jag.build_date, earlier)
		self.assert_(jag.build_date is not earlier)

		# Make a new datetime object that is timezone aware
		aware_earlier = datetime_localize(earlier)
		
		# Now they can be compared
		self.assert_(jag.build_date == aware_earlier)

		self.assert_(jag.last_checkup == datetime_localize(now))
		
		compjag = Car.objects.get(id=jag.id)

		self.assert_(compjag.last_checkup == datetime_localize(now))
		
		# Test initial autosetting of a datetime field
		compdt1 = datetime_localize(datetime.datetime.now())
		corv = Car(name="Corvette")
		compdt2 = datetime_localize(datetime.datetime.now())

		self.assert_(compdt1 < corv.build_date < compdt2)


class TestIPv6Field(Fixture):
	def runTest(self):
		import socket
		c = Car(ip_address="::1")	# localhost in IPv6
		c.save()
		
		compc = Car.objects.get(id=c.id)

		self.assert_(compc.ip_address == "::1")


if __name__ == "__main__":
	alltests = (
		TestFieldInitial,
		TestFloatFieldInitial,
		TestDatetimeField,
		TestIPv6Field
	)

	runtests(tests=alltests, verbosity=3)
# -*- coding: utf-8 -*-

from heinzel.tests.utils import Fixture, runtests
from heinzel.core.exceptions import DoesNotExist, SQLSyntaxError

from heinzel.core.sql.dml import Q
from heinzel.core.connection import db

from heinzel.core import utils

from heinzel.tests.model_examples import Car, Brand, Manufacturer, Driver, Key
from heinzel.core import models


models.register([Car, Brand, Manufacturer, Driver, Key])


class TestFkCrossJoin(Fixture):
	"""
	Test raw sql for foreign key cross joins.
	Problem: returns wrong results when the foreign key is not set.
	"""

	def runTest(self):
		vw, created = Brand.objects.create(name="VW")
		bmw, created = Brand.objects.create(name="Bmw")
		audi, created = Brand.objects.create(name="Audi")

		bulli, created = Car.objects.create(name="Bulli")
		golf, created = Car.objects.create(name="Golf")
		kaefer, created = Car.objects.create(name=u"Käfer")
		_3er, created = Car.objects.create(name="3er")
		a8, created = Car.objects.create(name="A8")

		# To make sure, the join also returns data that has not been related,
		# only set one relation

		# bulli.brand = vw
		# golf.brand = vw
		# kaefer.brand = vw
		# _3er.brand = bmw
		a8.brand = audi

		# conforms to
		# ‘‘Car.objects.filter(Q(brand__id=3) | Q(name__in=['Bulli']))’’
		# Output should be [(1, "Bulli"), (5, "A8")]
		select_stmt = """
			select 
				cars.id, cars.name
			from
				cars,
				brands
			where
				(cars.brand_id = brands.id
				and brands.id = 3)
				or cars.name in ('Bulli')
		"""

		db.cursor.execute(select_stmt)

		# Wrong result. Boo!
		self.assert_(set(db.cursor.fetchall()) 
			== set([(5, "A8"), (1, "Bulli"), (1, "Bulli"), (1, "Bulli")])
		)


class TestFkInnerJoin(Fixture):
	"""
	Test raw sql for foreign key inner joins.
	Use inner joins to link brands to cars.
	Problem: doesn't yield right results when foreign key is not set.
	"""

	def runTest(self):
		vw, created = Brand.objects.create(name="VW")
		bmw, created = Brand.objects.create(name="Bmw")
		audi, created = Brand.objects.create(name="Audi")

		bulli, created = Car.objects.create(name="Bulli")
		golf, created = Car.objects.create(name="Golf")
		kaefer, created = Car.objects.create(name=u"Käfer")
		_3er, created = Car.objects.create(name="3er")
		a8, created = Car.objects.create(name="A8")

		# To make sure, the join also returns data that has not been related,
		# only set one relation.

		# bulli.brand = vw
		# golf.brand = vw
		# kaefer.brand = vw
		# _3er.brand = bmw
		a8.brand = audi

		# conforms to
		# ‘‘Car.objects.filter(Q(brand__id=3) | Q(name__in=['Bulli']))’’
		# Output should be [(1, "Bulli"), (5, "A8")]
		select_stmt = """
			select 
				cars.id, cars.name
			from
				cars inner join brands on cars.brand_id = brands.id
			where
				brands.id = 3
				or cars.name in ('Bulli')
		"""

		db.cursor.execute(select_stmt)

		# Another wrong result. How sad!
		self.assert_(db.cursor.fetchall() == [(5, "A8")])


class TestFkOuterJoin(Fixture):
	"""
	Test raw sql for foreign key inner joins.
	Use outer joins to link brands to cars. Yields the right results even 
	when there are empty fields for the relation (i.e. brand_id = null).
	"""

	def runTest(self):
		vw, created = Brand.objects.create(name="VW")
		bmw, created = Brand.objects.create(name="Bmw")
		audi, created = Brand.objects.create(name="Audi")

		bulli, created = Car.objects.create(name="Bulli")
		golf, created = Car.objects.create(name="Golf")
		kaefer, created = Car.objects.create(name=u"Käfer")
		_3er, created = Car.objects.create(name="3er")
		a8, created = Car.objects.create(name="A8")

		# To make sure, the join also returns data that has not been related,
		# only set one relation.

		# bulli.brand = vw
		# golf.brand = vw
		# kaefer.brand = vw
		# _3er.brand = bmw
		a8.brand = audi

		# conforms to
		# ‘‘Car.objects.filter(Q(brand__id=3) | Q(name__in=['Bulli']))’’
		# Output should be [(1, "Bulli"), (5, "A8")]
		select_stmt = """
			select 
				cars.id, cars.name
			from
				cars left outer join brands on cars.brand_id = brands.id
			where
				brands.id = 3
				or cars.name in ('Bulli')
		"""

		db.cursor.execute(select_stmt)

		# Finally the right results for this type of relation!
		self.assert_(db.cursor.fetchall() == [(1, "Bulli"), (5, "A8")])

		# Now test the QuerySet
		self.assert_(
			list(Car.objects.filter(Q(brand__id=3) | Q(name__in=['Bulli'])))
			== [bulli, a8]
		)



if __name__ == "__main__":
	alltests = (
		# TestFkCrossJoin,
		# TestFkInnerJoin,
		TestFkOuterJoin,
	)


	runtests(alltests, verbosity=3)

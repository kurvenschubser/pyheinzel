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



class QuerySetBasics(Fixture):
	"""
	Demonstrate properties of QuerySets.
	"""

	def runTest(self):
		# Make some datasets
		shell, created = Movie.objects.create(title="Ghost in the shell")
		ghosts, created = Movie.objects.create(title="Ghost Rider")
		akira, created = Movie.objects.create(title="Akira")
		northstar, created = Movie.objects.create(title="Fist of the north star")
		
		# QuerySets encapsulate queries to the database.
		# QuerySets are usually obtained via a model Manager, called
		# ‘objects‘ by default.
		movies = Movie.objects.all()
		
		# For other Manager methods, see heinzel.core.managers.Manager.
		
		# ‘movies‘ is an instance of queries.QuerySet.
		#self.assert_(isinstance(movies, QuerySet))
		
		# It only hits the database, when it is evaluated. Evaluation happens
		# on iterating over the QuerySet, that is, when it's __iter__ method
		# is called.
		for mov in movies:
			self.assert_(mov in [shell, ghosts, akira, northstar])
		
		# Evaluation happens by calling the following methods on the QuerySet
		# as well: ‘__str__‘, ‘__unicode__‘, ‘__getitem__‘, ‘__len__‘,
		# ‘__contains__‘, ‘__eq__‘ and ‘__ne__‘.
		self.assert_(list(Movie.objects.all()) == [shell, ghosts, akira, northstar])

		# You can refine a QuerySet like this:
		ghostmovies = movies.filter(title__startswith="Ghost")
		
		# For other possible filters, check out the Test ‘Filter‘.
		
		# Only movies whose title begins with 'Ghost' are looked up by the
		# new QuerySet
		self.assert_(list(ghostmovies) == [shell, ghosts])

		# QuerySets are unique.
		self.assert_(ghostmovies is not movies)
		
		# movies is still yields the same results as before making QuerySet
		# ‘ghostmovies‘.
		self.assert_(list(movies) == [shell, ghosts, akira, northstar])


class QuerySetUpdating(Fixture):
	"""
	Show that:
	Adding instances of a model may or may not alter existing QuerySets.
	"""

	def runTest(self):
		terminator, created = Movie(title="Terminator 2").save()
		totalrecall, created = Movie(title="Total Recall").save()
		magnolia, created  = Movie(title="Magnolia").save()

		movies = Movie.objects.all()
		fltrqs = Movie.objects.filter(title__contains="Term")

		# Eval QuerySets
		list_movies = list(movies)
		list_fltrqs = list(fltrqs)

		# Create a new Movie.
		akira = Movie(title="Akira")

		# list_movies is now set in stone and the recently instantiated
		# "Akira" movie does not alter it's content.
		self.assert_(list_movies == [terminator, totalrecall, magnolia])
		
		# But QuerySet 'movies' will now yield a different result, because
		# Movie 'akira' has already been put into the cache, making it
		# eligible for inclusion in any QuerySet result set if it fits
		# that QuerySet's filters.		
		self.assert_(list(movies) == [terminator, totalrecall, magnolia, akira])
		self.assert_(akira is movies[-1])

		# Of course, all of the above had no effect on the results of
		# the 'fltrqs' QuerySet.
		self.assert_(list_fltrqs == list(fltrqs))

		
class Filter(Fixture):
	"""
	Demonstrate usage of method QuerySet.filter.
	"""

	def runTest(self):
		# The ‘filter‘ method of a QuerySet reduces the result set from all
		# model instances of a particular Model.
		# It takes keyword arguments, whose keyword is parsed for a filter,
		# e.g.: Actor.objects.filter(name__startswith). ‘name‘ being the
		# field on the Model and ‘startswith‘ the name of the filter, joined
		# together by 2 underscores.
		woody, created = Actor.objects.create(name="Allen")
		helge, created = Actor.objects.create(name="Schneider")
		mia, created = Actor.objects.create(name="Farrow")
		arnold, created = Actor.objects.create(name="Schwarzenegger")
		lars, created = Actor.objects.create(name="Jung")
		sylvester, created = Actor.objects.create(name="Stallone")
		afra, created = Actor.objects.create(name="Krawumpke")
		rowan, created = Actor.objects.create(name="Atkinson")
		
		# Make a QuerySet for all instances
		actors = Actor.objects.all()
		
		# All actors are contained in it
		self.assert_(list(actors) == [woody, helge, mia, arnold,lars, sylvester, afra, rowan])
		
		# Now filter it for all names beginning with "S"
		sactors = actors.filter(name__beginswith="S")

		# See that it works ...
		self.assert_(list(sactors) == [helge, arnold, sylvester])
		
		# Try out some other filters ...
		self.assert_(list(actors.filter(name__endswith="er")) == [helge, arnold])
		self.assert_(list(actors.filter(name__contains="arrow")) == [mia])
		
		# The ‘in‘ filter takes an iterable of strings
		self.assert_(list(actors.filter(name__in=("Jung", "Stallone")))
						== [lars, sylvester])
		
		# ‘exact‘ is an alias for no specified filter
		self.assert_(list(actors.filter(name__exact="Krawumpke")) ==
						list(actors.filter(name="Krawumpke")))

		# ‘beginswith‘ is an alias for ‘startswith‘
		self.assert_(list(actors.filter(name__beginswith="A"))
						== list(actors.filter(name__startswith="A")))

		# like ‘in‘, ‘between‘ takes strings in it's indexable argument.
		# unlike ‘in‘ the arguments length must be 2.
		self.assert_(list(actors.filter(name__between=("Farrow", "Krawumpke")))
						== [mia, lars, afra])

		self.assert_(list(actors.filter(name__gt="Schneider")) == [arnold, sylvester])
		self.assert_(list(actors.filter(name__gte="Schneider")) == [helge, arnold, sylvester])		
		self.assert_(list(actors.filter(name__lt="Farrow")) == [woody, rowan])
		self.assert_(list(actors.filter(name__lte="Farrow")) == [woody, mia, rowan])
		
		# As seen above, ‘gt‘, ‘gte‘, ‘lt‘, ‘lte‘, ‘between‘ and ‘in‘ can be
		# used for string comparisons, although in most cases one would
		# probably be using those for numeric comparison, so let's make
		# some more datasets that can be better tested for numbers.
		soap, created = Item.objects.create(name="Super Soap", price=0.99, stock=100)
		bread, created = Item.objects.create(name="Farmer's delight", price=0.49, stock=10)
		beer, created = Item.objects.create(name="Pilsener", price=0.89, stock=100000)
		cukes, created = Item.objects.create(name="Cucumbers", price=1.69, stock=30)
		
		items = Item.objects.all()
		
		self.assert_(list(items.filter(price__gt=0.89)) == [soap, cukes])
		self.assert_(list(items.filter(price__gte=0.89)) == [soap, beer, cukes])
		self.assert_(list(items.filter(price__lt=0.89)) == [bread])
		self.assert_(list(items.filter(price__lte=0.89)) == [bread, beer])
		self.assert_(list(items.filter(price__in=(0.99, 0.89, 0.5))) == [soap, beer])
		self.assert_(list(items.filter(price__between=(0.5, 1.0))) == [soap, beer])


class Exclude(Fixture):
	"""Demonstrate method QuerySet.exclude"""

	def runTest(self):
		# Method QuerySet.exclude works exactly like method QuerySet.filter,
		# except that any instances found through the filter statements
		# are stripped from the result set.
		
		# Make some datasets
		terminator, created = Movie(title="Terminator 2").save()
		texas, created = Movie(title=u"Texas, Doc Snyder hält die Welt in Atem").save()
		inception, created = Movie(title="Inception").save()
		starwars, created = Movie(title="Star Wars").save()
		cube, created = Movie(title="The Cube").save()
		fightclub, created = Movie(title="Fight Club").save()

		# Exclude Movie "Inception" from the results.
		self.assert_(list(Movie.objects.exclude(title="Inception")) \
					== [terminator, texas, starwars, cube, fightclub])
		
		# Exclude Movie nr. 2 from the result set.
		self.assert_(list(Movie.objects.exclude(pk=2)) \
					== [terminator, inception, starwars, cube, fightclub])

		self.assert_(list(Movie.objects.exclude(pk__in=(1, 2)))
					== [inception, starwars, cube,fightclub])

		self.assert_(list(Movie.objects.exclude(title__contains="ception"))
					== [terminator, texas, starwars, cube, fightclub])
		
		self.assert_(list(Movie.objects.exclude(pk__lte=4)) == [cube, fightclub])
		

class OrderBy(Fixture):
	def runTest(self):
		soap, created = Item.objects.create(name="Super Soap", price=0.99, stock=100)
		bread, created = Item.objects.create(name="Farmer's delight", price=0.49, stock=10)
		beer, created = Item.objects.create(name="Pilsener", price=0.89, stock=100000)
		cukes, created = Item.objects.create(name="Cucumbers", price=1.69, stock=30)
		
		items = Item.objects.all()
		
		# The default ordering is by a model's primary key field.
		self.assert_([soap.pk, bread.pk, beer.pk, cukes.pk] == range(1, 5))
		self.assert_(list(items) == [soap, bread, beer, cukes])

		# The ordering can be changed by calling QuerySet.orderby(orderterm)
		# where orderterm can be a string of any field name. If a minus sign
		# is the string's first character, the order will be descending, else
		# it will be ascending.
		self.assert_(list(items.orderby("price")) == [bread, beer, soap, cukes])
		self.assert_(list(items.orderby("-price")) == list(reversed([bread, beer, soap, cukes])))
		self.assert_(list(items.orderby("name")) == [cukes, bread, beer, soap])
		self.assert_(list(items.orderby("-name")) == list(reversed([cukes, bread, beer, soap])))
		
		# using ‘‘None‘‘ as ordering resets all orderings to the default *pk*.
		self.assert_(list(items.orderby(None)) == [soap, bread, beer, cukes])


class Aggregate(Fixture):
	"""
	Aggregations are functions that are applied to a specific column of all
	rows of a query result. One might want to know, e.g., the highest value
	of the annual earnings of a shop or the mean income of all employees
	etc.
	"""

	def runTest(self):
		soap, created = Item.objects.create(name="Super Soap", price=0.99, stock=100)
		noodles, created = Item.objects.create(name="Fine Noodles", price=0.65, stock=100)
		bread, created = Item.objects.create(name="Farmer's delight", price=0.49, stock=10)
		beer, created = Item.objects.create(name="Pilsener", price=0.89, stock=100000)
		cukes, created = Item.objects.create(name="Cucumbers", price=1.69, stock=30)
		
		# An aggregation returns a dict with the computed values.
		self.assert_(Item.objects.all().aggregate(Max("price"))
						== {"Max__price": 1.69})
		
		# By default, the dict key looks like ‘aggregationname__fieldname‘,
		# like above, but that can be changed by using keyword arguments:
		self.assert_(Item.objects.all().aggregate(price_maximum=Max("price"))
						== {"price_maximum": 1.69})
		
		# Multiple aggregations:		
		self.assert_(Item.objects.all().aggregate(Max("price"), Min("stock"), Sum("price"))
						== {"Max__price": 1.69, "Min__stock": 10, "Sum__price": 4.71})

		# Further aggregate functions:
		self.assert_(Item.objects.all().aggregate(Count("stock"))
						== {"Count__stock": 5})

		# Avg gives kind of funky results, but the differences to the true
		# average is very small (probably a rounding issue with floats)
		self.assert_(
			abs(Item.objects.all().aggregate(Avg("price"))["Avg__price"]
				- 4.71/5
				< 0.00000001
			)
		)
		

class Annotate(Fixture):
	def runTest(self):
		pass
		

class Limit(Fixture):
	def runTest(self):
		figurine, created = Item.objects.create(name="Figurine of Fertility")
		sword, created = Item.objects.create(name="Handy sword")
		healingherb, created = Item.objects.create(name="Healing herb")
		staff, created = Item.objects.create(name="Light wandering staff")
		bag, created = Item.objects.create(name="Rugged merchant bag")
		rope, created = Item.objects.create(name="Hemp rope")
		torch, created = Item.objects.create(name="Torch")
		
		# limit 5
		self.assert_(list(Item.objects.all().limit(5))
						== [figurine, sword, healingherb, staff, bag])

		# limit 2, offset 5
		self.assert_(list(Item.objects.all().limit(2, 5))
						== [rope, torch])

		# offset 4
		self.assert_(list(Item.objects.all().limit(offset=4))
						== [bag, rope, torch])


class Select(Fixture):
	"""Select directly hits the db, returning a list of raw value dicts for 
	the given field names. Any data in the cache will not be considered, 
	unless it has been saved before."""

	def runTest(self):
		figurine, created = Item.objects.create(name="Figurine of Fertility")
		sword, created = Item.objects.create(name="Handy sword")
		healingherb, created = Item.objects.create(name="Healing herb")
		
		self.assert_(Item.objects.all().select("name", "id")
			== [{"name": "Figurine of Fertility", "id": 1},
				{"name": "Handy sword", "id": 2},
				{"name": "Healing herb", "id": 3}]
		)


#! TODO: test with relation spanning queries.
class Distinct(Fixture):
	def runTest(self):
		mov1 = Movie(title="Some Movie").save()[0]
		mov2 = Movie(title="Some Movie").save()[0]
		mov3 = Movie(title="Some Movie").save()[0]
		mov4 = Movie(title="Some other movie").save()[0]

		# As of now, method QuerySet.select, through it's use of method
		# QuerySet.as_dict, bypasses the cache, directly pulling values from
		# the db. This means, that all queried rows must exist in the db,
		# any instances, that are supposed to be included in the query must 
		# have been saved.
		self.assert_(list(Movie.objects.all().distinct().select("title"))
				== [{"title": "Some Movie"}, {"title": "Some other movie"}])


class Reset(Fixture):
	pass




if __name__ == "__main__":
	alltests = (
		QuerySetBasics,
		QuerySetUpdating,
		Filter,
		Exclude,
		OrderBy,
		Aggregate,
		Annotate,
		Limit,
		Select,
		Distinct,
		# Reset,
		# Raw,
		# AsDict,
		# Clone
	)

	runtests(alltests, verbosity=3)

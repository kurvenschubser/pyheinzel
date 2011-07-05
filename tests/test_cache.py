# -*- coding: utf-8 -*-

import unittest, os

from heinzel.core import exceptions
from utils import Fixture, runtests
from heinzel import settings

from heinzel.core.queries import storage as store

# Import the models.
from model_examples import (Picture, Tag, Actor, Movie, Car, Brand,
									Manufacturer, Driver, Key, Item)

# Register models, so their relations can be set up and syncdb can do its job.
from heinzel.core import models
models.register([Picture, Tag, Actor, Movie, Item])




class CullTest(Fixture):
	"""
	The cache culls entries once it has reached it's max size.
	"""
	
	def setUp(self):
		store._cache.max_size = 10
		super(CullTest, self).setUp()

	def tearDown(self):
		store._cache.max_size = settings.MAX_CACHE
		super(CullTest, self).tearDown()

	def runTest(self):		
		max_size = 10
		# in order to guarantee right results for the test, settings.MAX_CACHE
		# must be set to max_size
		self.assert_(store._cache.max_size == max_size)
	
		# make some data
		pic0 = Picture(path="/some/path/0")
		pic0.save()

		pic1 = Picture(path="/some/path/1")
		pic1.save()
			
		for i in range(2, max_size):
			p = Picture(path="/some/path/%i" % i)
			p.save()

		# exactly max_size entries in the cache
		self.assert_(len(store._cache._order) 
						== len(store._cache._instances)
						== max_size)

		# access in-cache instances 2 to 10 to prevent them being culled 
		# when below more instances are added ...

		# ... first access the second instance ...
		self.assert_(Picture.objects.get(path="/some/path/1") is pic1)

		# ... then the others twice. The 'others' access rating
		# (access count based) is now higher than
		# the second instance's than the first instance's. Of course,
		# this depends on a Most Recently Used caching scenario, so
		# any other culling method breaks this test.
		pics2to10qs = Picture.objects.filter(id__between=(3, 10))

		self.assert_(list(pics2to10qs)
						== list(Picture.objects.exclude(id__in=(1, 2))))

		# list for later use
		pics_2to10_list = list(pics2to10qs) 

		# now add some instances to force culling of cache entries
		pic10 = Picture(path="/some/path/%i" % max_size)
		pic10.save()

		# cache did not overflow
		self.assert_(len(store._cache._order) 
						== len(store._cache._instances)
						== max_size)

		# pic10 has been cached ...
		self.assert_(pic10 in store._cache._instances.values())

		# print store._cache._order[pic0._inst_info]

		# ... while pic0 has been culled and ...
		self.assert_(pic0 not in store._cache._instances.values())

		# ... pic1 is still cached
		self.assert_(pic1 in store._cache._instances.values())

		# test again for another added instance
		pic11 = Picture(path="/some/path/%i" % (max_size + 1))
		pic11.save()

		# pic[max_size + 1] has been cached ...
		self.assert_(pic11 in store._cache._instances.values())

		# ... while pic1 has been culled and ...
		self.assert_(pic1 not in store._cache._instances.values())

		# ... pic2 is still cached
		self.assert_(pics_2to10_list[0].path == "/some/path/2")
		self.assert_(pics_2to10_list[0] in store._cache._instances.values())

		pics_2to12_list = pics_2to10_list + [pic10, pic11]

		self.assert_([o.id for o in pics_2to12_list] == range(3, 13))

		self.assert_(set([o.id for o in pics_2to12_list])
					== set([o.id for o in store._cache._instances.values()]))

		# Now re-cache pic0 by looking it up.
		self.assert_(Picture.objects.get(id=1) is pic0)

		# see that pic2 was displaced by pic0		
		self.assert_(pics_2to10_list[0] not in store._cache._instances.values())

		pics_0_3to12 = [pic0] + pics_2to10_list[1:] + [pic10, pic11]
	
		self.assert_([o.id for o in pics_0_3to12] == [1] + range(4, 13))

		self.assert_(set([o.id for o in pics_0_3to12])
					== set([o.id for o in store._cache._instances.values()]))


class Offset(Fixture):
	"""
	Make sure the cache is consistent when cached instances are being replaced
	by new ones when Cache.max_size is reached.
	"""

	def setUp(self):
		store._cache.max_size = 1000
		super(Offset, self).setUp()

		for i in xrange(2000):
			Movie.objects.create(title="movie %i" %i)

	def tearDown(self):
		store._cache.max_size = settings.MAX_CACHE
		super(Offset, self).tearDown()

	def runTest(self):			
		qs = Movie.objects.filter(id__between=(1, 1001))
		list_qs = list(qs)

		print Movie.objects.all()[:1001]
		
		self.assert_(list_qs == Movie.objects.all()[:1001])

		qs2 = Movie.objects.filter(id__between=(1, 1002))
		list_qs2 = list(qs2)

		self.assert_(list_qs2 == Movie.objects.all()[:1002])

		self.assert_(
			list(Movie.objects.filter(id__between=(900, 1910)))
			==
			Movie.objects.all()[899:1910]
		)


if __name__ == "__main__":
	alltests = (
		CullTest,
		Offset,
	)

	runtests(tests=alltests, verbosity=3)
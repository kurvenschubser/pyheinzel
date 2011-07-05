# encoding: utf-8


from utils import Fixture, runtests
from heinzel.core.exceptions import DoesNotExist, DatabaseSanityError
from heinzel.core import utils

from model_examples import (Actor, Movie, UniqueTitleMovie, Car, Brand,
	Manufacturer, Driver, Key)

from heinzel.core import models


models.register([Actor, Movie, UniqueTitleMovie])


# only imported for verifying QuerySet results
from heinzel.core.queries import storage as store
from heinzel.core.info import get_inst_info



class Debug(Fixture):
	def runTest(self):
		print "-------------------------hi-------------------"
		for i in xrange(20):
			m = Movie(title="Debug %s" %i)
			m.save()

		qs = Movie.objects.filter(title__startswith="Debug")
	
		
		self.assert_(len(qs) == 20 == len(list(Movie.objects)))

		
class BasicAssumptions(Fixture):
	"""
	Show:
	1. Basic assumptions about the store's behaviour.
	"""
		
	def runTest(self):
		# Create some Movie data-sets.
		terminator = Movie(title="Terminator 2")

		terminator.save()

		totalrecall, created, = Movie(title="Total Recall").save()
		twins, created  = Movie(title="Twins").save()

		movies = Movie.objects.all()

		# evaluate the query, hit the store/database.
		movies_list = list(movies)

		# the instances have been set as expected.
		self.assert_([terminator, totalrecall, twins] == movies_list)

		self.assert_(set(movies) == set(store._cache._instances.values()))

		# now make a QuerySet for only one instance of the above Movie instances.
		fltrqs = Movie.objects.filter(title__contains="Term")

		# now eval it.
		term_movies = list(fltrqs)

		# see if the instances have been set as expected.
		self.assert_([terminator] == term_movies)

		# misc
		inf = get_inst_info(terminator)

		self.assert_(list(fltrqs)[0] is terminator)
		self.assert_(store._cache._instances[inf] is terminator)

		# add a little confusion ...
		list(movies)

		self.assert_(list(fltrqs)[0] is terminator is movies[0])

		# after all this experimenting, make sure there are no excess instances
		# in the store
		self.assert_(len(store._cache._instances) == 3)


class SavingInstances(Fixture):		
	def runTest(self):
		# Create some Movie data-sets.
		terminator = Movie(title="Terminator 2")
		
		inf = get_inst_info(terminator)

		# Before an instance is saved it is put in the QuerySet's 
		# store. It has to be in either store._dirty or store._cache
		# to be kept alive.
		self.assert_(terminator is store._alive[(inf.model_info.model, inf.get_pk_as_key())].get_inst())
		
		# ... and marked dirty (i.e. altered, unsaved).
		self.assert_(terminator is store._dirty[inf])
		
		# It has not been put in the database store yet
		self.assert_(terminator not in store._cache._instances.values())
		
		# Now save.
		terminator.save()
		
		# Instance is still an alive (in-memory) object
		self.assert_(terminator is store._alive[(inf.model_info.model, inf.get_pk_as_key())].get_inst())

		self.assert_(len(store._alive) == 1)

		# Instance is not dirty anymore ...
		self.assert_(not store._dirty)

		# ... and is now in the database store. 
		self.assert_(terminator in store._cache._instances.values())
		self.assert_(terminator is store._cache._instances[inf])
		self.assert_(len(store._cache._instances) == 1)


class DeletingInstances(Fixture):
	"""
	Show that:
	Instances whose delete method has been called, are deleted from the 
	database and removed from the db store. If the instance is to be cached
	again, call ‘‘Model.save‘‘.
	"""

	def runTest(self):
		magnolia, created = Movie(title="Magnolia").save()
		
		# instance is in the db section of the store, because it was saved
		self.assert_(magnolia in store._cache._instances.values())
		
		# it is not in the dirty section of the store
		self.assert_(magnolia not in store._dirty.values())
		
		# it can be found by a query
		self.assert_(magnolia is Movie.objects.get(title="Magnolia"))
		
		self.assert_(magnolia not in store._dirty.values())
		
		# now call delete on it
		magnolia.delete()
		
		# check raw values from database
		self.assert_(Movie.objects.filter(title="Magnolia").as_dict() == {})

		# it is not in the database store anymore
		self.assert_(magnolia not in store._cache._instances.values())
		
		# it is also removed from the dirty store
		self.assert_(magnolia not in store._dirty.values())
		
		# it can't be found via query
		self.assertRaises(DoesNotExist, Movie.objects.get, **{"title": "Magnolia"})


class InstancesAreIdentical(Fixture):
	"""
	Show that:
	1. No duplication of model instances once they are saved.
	"""

	def runTest(self):
		# Create some Movie data-sets.
		terminator, created = Movie(title="Terminator 2").save()
		totalrecall, created, = Movie(title="Total Recall").save()
		twins, created  = Movie(title="Twins").save()
		
		movies = Movie.objects.all()
		fltrqs = Movie.objects.filter(title__contains="Term")

		# check that the queries yield identical Movie instances.		
		self.assert_(list(fltrqs)[0] is terminator)
		
		self.assert_(movies[0] is terminator)
		self.assert_(list(movies)[0] is terminator)

		self.assert_(movies[0] is fltrqs[0] is terminator)
		
		# now make a different QuerySet that looks up all Movie instances,
		# but with other filters.
		newqs = Movie.objects.filter(title__startswith="T")
		
		# eval QuerySet
		list(newqs)

		# Still the same terminator instance
		self.assert_(newqs[0] is terminator is movies[0])
		
		self.assert_(utils.zipcmp(movies, Movie.objects.filter(title__startswith="T")))


class TestDistinct(Fixture):
	def runTest(self):
		m1,_ = Movie(title="Same Title").save()
		m2,_ = Movie(title="Same Title").save()
		
		qs = Movie.objects.filter(title="Same Title")
		qs.distinct("title")


class Rollback(Fixture):
	"""
	Show that:
	1. Any changes on all objects in the store, that haven't been saved in the
	database will be undone by calling store.rollback.
	"""

	def runTest(self):
		pass


class HistoryReset(Fixture):
	"""
	Reset any changes to an objects field to the values they were in when it was
	first instantiated.
	"""

	def runTest(self):
		pass


class HistoryUndo(Fixture):
	"""
	Reverse one step of the change history of an object.
	"""
	
	def runTest(self): pass


class HistoryRedo(Fixture):
	"""
	Repeat a change that has previously been undone.
	"""
	
	def runTest(self): pass


class SavedObjectsHistoryDeleted(Fixture):
	"""
	Show that:
	1. When an object is saved, it's change history will be deleted.
	"""
	
	def runTest(self): pass




if __name__ == "__main__":
	alltests = (
		BasicAssumptions,
		SavingInstances,
		DeletingInstances,
		InstancesAreIdentical,
	)

	runtests(alltests, verbosity=3)

# -*- coding: utf-8 -*-

"""Please see file ‘test_relations‘ for an explanation of what's being tested
below."""

from utils import Fixture, runtests

from model_examples import Actor, Movie, Car, Brand, Manufacturer, Driver, Key
from heinzel.core import models, exceptions


models.register([Actor, Movie])
 



class populate(Fixture):
	def runTest(self):
		terminator, created = Movie(title="Terminator 2").save()
		totalrecall, created, = Movie(title="Total Recall").save()
		twins, created  = Movie(title="Twins").save()

		arnold, created= Actor(name="Schwarzenegger").save()
		danny, created = Actor(name="De Vito").save()

		arnold.acted_in = [terminator, totalrecall, twins]
		danny.acted_in = [twins]

		# setup finished
		del terminator, totalrecall, twins, arnold, danny

		arnold = Actor.objects.get(name="Schwarzenegger")
		danny = Actor.objects.get(name="De Vito")

		movies = Movie.objects
		twins = Movie.objects.get(title="Twins")

	
		self.assert_(list(arnold.acted_in) == list(movies))
		self.assert_(arnold.acted_in[0] == Movie.objects.get(title="Terminator 2"))

		self.assert_(list(danny.acted_in) == [Movie.objects.get(title="Twins")])		

		self.assert_(list(Actor.objects) == [arnold, danny])
		self.assert_(list(Actor.objects) == list(reversed([danny, arnold])))
		self.assert_(list(movies) == list(arnold.acted_in))

class traverse(Fixture):
	def runTest(self):
		terminator, created = Movie(title="Terminator 2").save()
		totalrecall, created, = Movie(title="Total Recall").save()
		twins, created  = Movie(title="Twins").save()
		
		arnold, created= Actor(name="Schwarzenegger").save()
		danny, created = Actor(name="De Vito").save()
		
		arnold.acted_in = [terminator, totalrecall, twins]
		danny.acted_in = [twins]

		# setup finished
		del terminator, totalrecall, twins, arnold, danny
		
		arnold = Actor.objects.get(name="Schwarzenegger")
		danny = Actor.objects.get(name="De Vito")

		movies = Movie.objects.all()
		twins = Movie.objects.get(title="Twins")

		self.assert_(arnold.acted_in[2].actor_set == twins.actor_set)
		self.assert_(arnold.acted_in[0].actor_set[0] is arnold)
	
		self.assert_(twins.actor_set[1].acted_in[0] is twins)

class get_set_delete(Fixture):
	def runTest(self):
		terminator, created = Movie(title="Terminator 2").save()
		totalrecall, created, = Movie(title="Total Recall").save()
		twins, created  = Movie(title="Twins").save()
		
		arnold, created= Actor(name="Schwarzenegger").save()
		danny, created = Actor(name="De Vito").save()
		
		arnold.acted_in = [terminator, totalrecall, twins]
		danny.acted_in = [twins]

		# setup finished

		arnold = Actor.objects.get(name="Schwarzenegger")

		predator, created = Movie.objects.get_or_create(title="Predator")

		arnold.acted_in.add([predator])

		self.assert_(len(list(Movie.objects)) == 4)

		self.assert_(list(arnold.acted_in) == list(Movie.objects.all()))
		
		self.assert_(arnold.acted_in.all() == Movie.objects.all())
		
		arnold.acted_in = None

		self.assert_(list(arnold.acted_in) == [])

		arnold.acted_in = list(Movie.objects)
		self.assert_(arnold.acted_in.all() == Movie.objects.all())

		del arnold.acted_in
		self.assert_(list(arnold.acted_in) == [])

		comp_arnold = Actor.objects.get(name="Schwarzenegger")
		self.assert_(list(comp_arnold.acted_in) == [] == list(arnold.acted_in))
		
		# Re-add movies
		arnold.acted_in.add([terminator, totalrecall, twins, predator])
		self.assert_(list(arnold.acted_in.all()) == [terminator, totalrecall, twins, predator])
		
		# Mess around a little: duplicate values should not be allowed
		#arnold.acted_in.add([terminator, totalrecall, twins, predator])
		
		
		# Remove
		arnold.acted_in.remove([twins])
		self.assert_(list(arnold.acted_in) == [terminator, totalrecall, predator])
		self.assert_(list(Actor.objects.get(name="Schwarzenegger").acted_in.all()) == [terminator, totalrecall, predator])
		self.assert_(list(Movie.objects.get(title="Twins").actor_set) == [danny])
		
		# Delete
		arnold.acted_in.delete()
		self.assert_(list(arnold.acted_in) == [])
		self.assert_(list(Actor.objects.get(name="Schwarzenegger").acted_in.all()) == [])
		self.assert_(list(Movie.objects.get(title="Terminator 2").actor_set) == [])
		self.assert_(list(Movie.objects.get(title="Total Recall").actor_set) == [])
		
		# Re-set titles in different order...
		arniesmovies = [predator, totalrecall, twins, terminator]
		arnold.acted_in = arniesmovies
		
		# ... but that doesn't change the order of the QuerySet result set, 
		# because that is by default ordered by the pk of the Model that the
		# RelationManager points to.
		self.assert_(Actor.objects.get(name="Schwarzenegger").acted_in.all() == Movie.objects.all())
		self.assert_(list(Movie.objects.get(title="Twins").actor_set.all()) == [arnold, danny])
		
		# When setting a sequence that evaluates to False, simply delete 
		# all related entries
		arnold.acted_in.set([])

		self.assert_(list(Actor.objects.get(name="Schwarzenegger").acted_in.all())
						== [])
		
		# When adding a sequence that evaluates to False, do nothing.
		arnold.acted_in.add([])
		self.assert_(list(Actor.objects.get(name="Schwarzenegger").acted_in.all())
						== [])
		
		# Re-set movies
		arnold.acted_in = arniesmovies[:2]
		self.assert_((list(Actor.objects.get(name="Schwarzenegger").acted_in.all())
						== [totalrecall, predator]))
		
		# try again to add with empty sequence... 
		arnold.acted_in.add([])
		
		# ... and see that that doesn't have any effect on the relation.
		self.assert_((list(Actor.objects.get(name="Schwarzenegger").acted_in.all())
						== [totalrecall, predator]))

if __name__ == "__main__":
	alltests = (
		populate,
		traverse,
		get_set_delete,
	)

	runtests(alltests, verbosity=3)
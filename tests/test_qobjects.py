# -*- coding: utf-8 -*-

from utils import Fixture, runtests
from heinzel.core.exceptions import DoesNotExist, SQLSyntaxError
from heinzel.core import utils


from model_examples import Actor, Movie

from heinzel.core.sql.dml import Q
from heinzel.core import models


models.register([Actor, Movie])


class TestQ_AND(Fixture):
	def runTest(self):
		spacey, created = Actor.objects.create(name="Spacey")
		deniro, created = Actor.objects.create(name="De Niro")
		moore, created = Actor.objects.create(name="Moore")
		weaver, created = Actor.objects.create(name="Weaver")
		henriksen, created = Actor.objects.create(name="Henriksen")
		reno, created = Actor.objects.create(name="Reno")
		
		suspects, created = Movie.objects.create(title="The Usual Suspects")
		ronin, created = Movie.objects.create(title="Ronin")
		magnolia, created = Movie.objects.create(title="Magnolia")
		aliens, created = Movie.objects.create(title="Alien")
		
		spacey.acted_in.add([suspects])
		deniro.acted_in.add([ronin])
		reno.acted_in.add([ronin])
		moore.acted_in.add([magnolia])
		weaver.acted_in.add([aliens])
		henriksen.acted_in.add([aliens])


		qs = Actor.objects.filter(Q(name="Weaver") & Q(id=4))

		self.assert_(list(qs) == [weaver])


class TestQ_OR(Fixture):

	def runTest(self):
		spacey, created = Actor.objects.create(name="Spacey")
		deniro, created = Actor.objects.create(name="De Niro")
		moore, created = Actor.objects.create(name="Moore")
		weaver, created = Actor.objects.create(name="Weaver")
		henriksen, created = Actor.objects.create(name="Henriksen")
		reno, created = Actor.objects.create(name="Reno")
		
		suspects, created = Movie.objects.create(title="The Usual Suspects")
		ronin, created = Movie.objects.create(title="Ronin")
		magnolia, created = Movie.objects.create(title="Magnolia")
		aliens, created = Movie.objects.create(title="Alien")
		
		spacey.acted_in.add([suspects])
		deniro.acted_in.add([ronin])
		reno.acted_in.add([ronin])
		moore.acted_in.add([magnolia])
		weaver.acted_in.add([aliens])
		henriksen.acted_in.add([aliens])
		

		self.assert_(list(Actor.objects.filter(
				Q(name="Weaver") | Q(name="De Niro")
			))
			== [deniro, weaver]
		)


class TestQ_NOT(Fixture):
	def runTest(self):
		spacey, created = Actor.objects.create(name="Spacey")
		deniro, created = Actor.objects.create(name="De Niro")
		moore, created = Actor.objects.create(name="Moore")
		weaver, created = Actor.objects.create(name="Weaver")
		henriksen, created = Actor.objects.create(name="Henriksen")
		reno, created = Actor.objects.create(name="Reno")
		streep, created = Actor.objects.create(name="Streep")
		cooper, created = Actor.objects.create(name="Cooper")

		suspects, created = Movie.objects.create(title="The Usual Suspects")
		ronin, created = Movie.objects.create(title="Ronin")
		magnolia, created = Movie.objects.create(title="Magnolia")
		aliens, created = Movie.objects.create(title="Alien")
		adaptation, created = Movie.objects.create(title="Adaptation")
		bourne, created = Movie.objects.create(title="The Bourne Identity")


		spacey.acted_in.add([suspects])
		deniro.acted_in.add([ronin])
		reno.acted_in.add([ronin])
		moore.acted_in.add([magnolia])
		weaver.acted_in.add([aliens])
		henriksen.acted_in.add([aliens])
		streep.acted_in.add([adaptation])
		cooper.acted_in.add([adaptation, bourne])



		# Negating
		self.assert_(list(Actor.objects.filter(
				~Q(name="Weaver")
			))
			== [spacey, deniro, moore, henriksen, reno, streep, cooper]
		)


class TestQ_AND_NOT(Fixture):
	def runTest(self):
		spacey, created = Actor.objects.create(name="Spacey")
		deniro, created = Actor.objects.create(name="De Niro")
		moore, created = Actor.objects.create(name="Moore")
		weaver, created = Actor.objects.create(name="Weaver")
		henriksen, created = Actor.objects.create(name="Henriksen")
		reno, created = Actor.objects.create(name="Reno")
		
		suspects, created = Movie.objects.create(title="The Usual Suspects")
		ronin, created = Movie.objects.create(title="Ronin")
		magnolia, created = Movie.objects.create(title="Magnolia")
		aliens, created = Movie.objects.create(title="Alien")
		
		spacey.acted_in.add([suspects])
		deniro.acted_in.add([ronin])
		reno.acted_in.add([ronin])
		moore.acted_in.add([magnolia])
		weaver.acted_in.add([aliens])
		henriksen.acted_in.add([aliens])


		self.assert_(list(Actor.objects.filter(
				Q(name="Weaver") & ~Q(name="De Niro")
			))
			== [weaver]
		)


class TestQ_OR_NOT(Fixture):
	def runTest(self):
		spacey, created = Actor.objects.create(name="Spacey")
		deniro, created = Actor.objects.create(name="De Niro")
		moore, created = Actor.objects.create(name="Moore")
		weaver, created = Actor.objects.create(name="Weaver")
		henriksen, created = Actor.objects.create(name="Henriksen")
		reno, created = Actor.objects.create(name="Reno")
		
		suspects, created = Movie.objects.create(title="The Usual Suspects")
		ronin, created = Movie.objects.create(title="Ronin")
		magnolia, created = Movie.objects.create(title="Magnolia")
		aliens, created = Movie.objects.create(title="Alien")
		
		spacey.acted_in.add([suspects])
		deniro.acted_in.add([ronin])
		reno.acted_in.add([ronin])
		moore.acted_in.add([magnolia])
		weaver.acted_in.add([aliens])
		henriksen.acted_in.add([aliens])
		

		self.assert_(Actor.objects.filter(
				Q(name="Weaver") | ~Q(name="De Niro")
			)
			== Actor.objects.exclude(name="De Niro")
		)


class TestQ(Fixture):
	"""
	Show that:
	heinzel.core.sql.dml.Q objects provide a way to chain QuerySet 
	filters using bitwise operators. Operators are:
	|		OR'ing,
	&		AND'ing,
	~		NOT'ing.
	"""

	def runTest(self):
		spacey, created = Actor.objects.create(name="Spacey")
		deniro, created = Actor.objects.create(name="De Niro")
		moore, created = Actor.objects.create(name="Moore")
		weaver, created = Actor.objects.create(name="Weaver")
		henriksen, created = Actor.objects.create(name="Henriksen")
		reno, created = Actor.objects.create(name="Reno")
		streep, created = Actor.objects.create(name="Streep")
		cooper, created = Actor.objects.create(name="Cooper")

		suspects, created = Movie.objects.create(title="The Usual Suspects")
		ronin, created = Movie.objects.create(title="Ronin")
		magnolia, created = Movie.objects.create(title="Magnolia")
		aliens, created = Movie.objects.create(title="Alien")
		adaptation, created = Movie.objects.create(title="Adaptation")
		bourne, created = Movie.objects.create(title="The Bourne Identity")


		spacey.acted_in.add([suspects])
		deniro.acted_in.add([ronin])
		reno.acted_in.add([ronin])
		moore.acted_in.add([magnolia])
		weaver.acted_in.add([aliens])
		henriksen.acted_in.add([aliens])
		streep.acted_in.add([adaptation])
		cooper.acted_in.add([adaptation, bourne])

		## Same as normal filtering with keyword
		self.assert_(
			(	list(Actor.objects.filter(
					Q(name__in=["Spacey", "Weaver", "Streep", "Cooper"])
				))
				== [spacey, weaver, streep, cooper]
			)
		)


		## Giving multiple Q objects to the filter method is the same as AND'ing
		self.assert_(list(Actor.objects.filter(
				Q(name="Spacey"), Q(acted_in__title__contains="Suspects")
			))
			== [spacey]
		)


		## '~' takes precedence over '&' takes precedence over '|', according 
		## to the are the standard Python operator precedences.		
		self.assert_(list(Actor.objects.filter(
				Q(name="Moore") | Q(acted_in=aliens.pk) & Q(id__gte=5)
			))
			== [moore, henriksen]
		)
		
		## If you want to order the precedence chain, you can group Q objects 
		## using brackets.
		self.assert_(list(Actor.objects.filter(
				(Q(name="Moore") | Q(acted_in=aliens.pk)) & Q(id__gte=5)
			))
			== [henriksen]
		)

		## 
		self.assert_(list(Actor.objects.filter(
				Q(name="Moore") | (Q(acted_in=aliens.pk) & Q(id__gte=5))
			))
			== [moore, henriksen]
		)

		## Q objects work with the QuerySet.exclude method as well
		self.assert_(list(Actor.objects.exclude(
					(Q(acted_in__in=[aliens.pk, magnolia.pk, ronin.pk])
					| ~Q(acted_in=bourne.pk))
				)
			)
			== [cooper]
		)


if __name__ == "__main__":
	alltests = (
		TestQ_AND,
		TestQ_OR,
		TestQ_NOT,
		TestQ_AND_NOT,
		TestQ_OR_NOT,
		TestQ,
	)


	runtests(alltests, verbosity=3)

# -*- coding: utf-8 -*-

import os
import unittest

try:
	import cProfile as profile
except ImportError, e:
	import profile

import pstats


from heinzel.core import models
from heinzel.core import exceptions
from utils import Fixture, runtests, stopwatch

# Import the models.
from model_examples import (Actor, Movie)

# Register models, so their relations can be set up and syncdb can do its job.
models.register([Actor, Movie])


def setup():
	# Setup db
	if os.path.exists(os.path.abspath("test.db")):
		os.remove("test.db")

	from heinzel.maintenance import syncdb
	syncdb(models.registry, "test.db")


def tear_down():
	# Teardown db
	from heinzel.core import connection
	conn = connection.connect()
	conn.close()

	from heinzel.core.queries import storage as store
	store.clear()

	if os.path.exists(os.path.abspath("test.db")):
		os.remove("test.db")


if __name__ == "__main__":
	setup()
	
	n = 10000

	def populate():
		for i in xrange(n):
			Actor.objects.create(name="actor_obj_%i" % i)

	profile.run("populate()", "populate.profile")

	def filtermany():
		list(Actor.objects.filter(id__between=(1, 2002)))

	profile.run("filtermany()", "filtermany.profile")

	def filtermany2():
		list(Actor.objects.filter(id__between=(1, 2002)))

	profile.run("filtermany2()", "filtermany2.profile")


	def filterone2():
		list(Actor.objects.filter(name="actor_obj_500"))

	profile.run("filterone2()", "filterone2.profile")

	
	tear_down()

	
	p = pstats.Stats("populate.profile")
	p.strip_dirs().sort_stats("cumulative", "time").print_stats(20)

	p = pstats.Stats("filtermany.profile")
	p.strip_dirs().sort_stats("cumulative", "time").print_stats(20)

	p = pstats.Stats("filtermany2.profile")
	p.strip_dirs().sort_stats("cumulative", "time").print_stats(20)
	

	# p = pstats.Stats("filterone2.profile")
	# p.strip_dirs().sort_stats("cumulative", "time").print_stats(20)
	


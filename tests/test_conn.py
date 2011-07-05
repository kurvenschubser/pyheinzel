# -*- coding: utf-8 -*-

import os
import unittest

# use a different dbname
from heinzel import settings
settings.DBNAME = "othername.db"


from heinzel.core import models
from heinzel.core import exceptions
from utils import Fixture, runtests, stopwatch

# Import the models.
from model_examples import (Actor, Movie)

# Register models, so their relations can be set up and syncdb can do its job.
models.register([Actor, Movie])




class ConnTest(Fixture):
	def runTest(self):
		for i in xrange(100):
			Actor.objects.create(name="actor_%i" % i)
		


if __name__ == "__main__":
	alltests = (
		ConnTest,
	)

	runtests(tests=alltests, verbosity=3)
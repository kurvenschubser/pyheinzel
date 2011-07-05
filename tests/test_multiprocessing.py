# -*- coding: utf-8 -*-
import os
import time

from utils import Fixture, runtests
from heinzel.core.exceptions import DoesNotExist, SQLSyntaxError
from heinzel.core import utils


from model_examples import Actor, Movie

from heinzel.core.sql.dml import Q
from heinzel.core import models


models.register([Actor, Movie])


class TestMultiProcess(Fixture):
	def runTest(self):
		import multiprocessing
		
		class Worker(multiprocessing.Process):
			def __init__(self, n=100):
				multiprocessing.Process.__init__(self)
				self.n = n
				self._stop = False

			def run(self):
				self.i = 0
				while not self._stop and self.n and self.n > self.i:
					self.action()
					self.i += 1
					print self, self.pid, os.getpid(), os.getppid()
					print self._stop, self.n, self.i
					print not self._stop, self.n and self.n > self.i
					print
					#time.sleep(1)

			def action(self):
				Actor.objects.create(name="actor_%i" % self.i)

		InsertWorker = Worker

		class SelectWorker(Worker):
			def action(self):
				list(Actor.objects.filter(name__startswith="actor"))
		
		
			
					
					
					

		workers = [SelectWorker(n=200), InsertWorker(n=200), 
					SelectWorker(n=200), InsertWorker(n=200),
					SelectWorker(n=200), InsertWorker(n=200),
					SelectWorker(n=200), InsertWorker(n=200),
					SelectWorker(n=200), InsertWorker(n=200),]

		for w in workers:
			w.daemon=True
			w.start()

		Actor.objects.create(name="fooactor")
		print Actor.objects.get(name="fooactor")
		
		workersjoined = 0
		for w in workers:
			w.join()
			workersjoined += 1
			print "worker joined()", w, workersjoined


		
			
				


if __name__ == "__main__":
	alltests = (
		TestMultiProcess,
	)


	runtests(alltests, verbosity=3)


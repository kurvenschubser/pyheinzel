# -*- coding: utf8 -*-

from __future__ import division

from datetime import datetime
import operator

from heinzel import settings
from heinzel.core.info import get_inst_info


class MRUCacheEntry(object):
	"""Caution: extremely slow!"""

	def __init__(self):
		self.timestamp = datetime.now()
		self.accesses = 0

	def __repr__(self):
		return (u"<%s: timestamp=%s, accesses=%s>" % (self.__class__.__name__,
										self.timestamp, self.accesses))

	def __eq__(self, other):
		return self.timestamp == other.timestamp

	def __ne__(self, other):
		return not self.__eq__(other)

	def __gt__(self, other):
		now = datetime.now()
		self_age = (self.timestamp - now).microseconds
		other_age = (other.timestamp - now).microseconds

		return self_age < other_age

	def __le__(self, other):
		return not self.__gt__(other)

	def __lt__(self, other):
		now = datetime.now()
		self_age = (self.timestamp - now).microseconds
		other_age = (other.timestamp - now).microseconds

		return self_age > other_age

	def __ge__(self, other):
		return not self.__lt__(other)

	def touch(self):
		self.timestamp = datetime.now()
		self.accesses += 1


class History(dict):"Record changes to data attributes of Model instances."


class RichComparisonCache(object):
	"""Takes a type implementing the rich comparisons interface as 
	entry_class, using it for determining which instances need to be culled.
	To speed up culling, parameter ‘‘cull_n‘‘ determines how many entries will
	be culled on every culling step, reducing the overall calls to the cull 
	method."""

	def __init__(self, max_size=1000, cull_n=4, entry_class=MRUCacheEntry):
		self.max_size = max_size
		self.cull_n = cull_n
		self.entry_class = entry_class
		self._entries = {}
		self._instances = {}

	def __contains__(self, item):
		return item in self._instances

	def add(self, inst_info):
		self._instances[inst_info] = inst_info.get_inst()
		self._entries[inst_info] = self.entry_class()

		if self.filling_level() > 1.0:
			self.cull_expendables()
		
	def touch(self, inst_info):
		return self._entries[inst_info].touch()

	def remove(self, inst_info):
		self._entries.pop(inst_info)
		self._instances.pop(inst_info)

	def clear(self):
		self._entries.clear()
		self._instances.clear()

	def filling_level(self):
		return len(self._instances) / self.max_size

	def cull_expendables(self):
		getter = operator.itemgetter(1)
		sortlist = sorted(self._entries.items(), key=getter)

		while self.filling_level() > 1.0:
			for i in xrange(self.cull_n):
				self.remove(sortlist[-1][0])
				sortlist.pop()


class MRUCache(object):
	def __init__(self, max_size=1000, cull_n=1):
		"""Caution, setting *cull_n* to something other than 1 is untested.
		"""

		self.max_size = max_size
		self.cull_n = cull_n

		self._instances = {}
		self._order = []

	def __contains__(self, inst_info):
		return inst_info in self._instances

	def add(self, inst_info):
	
		assert (inst_info.get_inst() is not None), (inst_info.vals,)
	
		if inst_info in self._order:
			self.touch(inst_info)
		else:
			self._order.append(inst_info)
			self._instances[inst_info] = inst_info.get_inst()

			while self.filling_level() > 1.0:
				for i in xrange(self.cull_n):
					self.cull_expendables()

	def touch(self, inst_info):
		self._order.append(
			self._order.pop(self._order.index(inst_info))
		)

	def remove(self, inst_info):
		try:
			self._order.pop(self._order.index(inst_info))
			self._instances.pop(inst_info)
		except:
			print self.filling_level()
			print [inf.get_inst() for inf in self._order], self._instances.values()
			raise

	def clear(self):
		del self._order[:]
		self._instances.clear()

	def filling_level(self):
		return len(self._order) / float(self.max_size)

	def cull_expendables(self):
		self.remove(self._order[0])

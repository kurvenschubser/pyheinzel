from datetime import datetime, tzinfo, timedelta
import time
from re import sub, match
from itertools import izip
from copy import deepcopy
import pytz




######################## --- Decorators/Wrappers --- #########################
def deferred_model_loading(func):
	"""When applied to an empty method, (def foo(self): pass), this decorator
		looks for an attribute on the class named ’’ '_' + foo ’’. If it does
		not exist, it will create it. If it does exist and it is of type str
		or unicode (basestring), it will look for an object of that name in
		models.registry which will be imported for the purpose. This process 
		only happens on first access of the attribute, then the looked up 
		object will be set on the decorated attribute ’’ '_' + foo ’’, if
		everything goes according to plan. Finally the decorated method will be
		made an attribute on the class."""

	attrname = "_" + func.__name__
	
	def fget(inst):
		attrvalue = inst.__dict__.get(attrname, None)
		
		if not attrvalue:
			inst.__dict__[attrname] = "foo"
			attrvalue = inst.__dict__.get(attrname)
			return attrvalue

		if isinstance(attrvalue, basestring):
			if attrvalue == 'self':
				attrvalue = inst.__dict__.get("model")
				inst.__dict__[attrname] = attrvalue
				return attrvalue

			try:
				from heinzel.core.models import registry as model_registry
			except ImportError, e:
				raise

			for m in model_registry:
				if m.__name__ == attrvalue:
					inst.__dict__[attrname] = m
					return m

			raise ImportError("Could not find related_model '%s' via deferred loading." %attrvalue)

		return inst.__dict__[attrname]

	def fset(inst, value):
		inst.__dict__[attrvalue] = value

	return property(fset, fget)


########################## --- Datastructures --- ############################

class OrderedDict(object):
	"""
	'dict'-like behaviour, but new pairs are appended to existing values,
	when they haven't been set before and replace existing values if their
	keys are equal.
	"""

	def __init__(self, iterable=None, **kwargs):
		self.update(iterable, **kwargs)
		self._indexed_keys = []
		self._indexed_values = []

	def __str__(self):
		return "OrderedDict {%s}" % ", ".join(["%s: %s" % (k, v) for k, v in self.iteritems()])

	def __len__(self):
		assert len(self._indexed_keys) == len(self._indexed_values)
		return len(self._indexed_keys)

	def __nonzero__(self):
		return bool(len(self))

	def __contains__(self, item):
		return item in self.iterkeys()

	def __getitem__(self, item):
		"""‘‘item‘‘ is interpreted as the key for a certain value from
		self._indexed_values except when it is a slice object. This way you can
		use an (int or long or float) as dictionary key, but not as an index
		to the values. If you want to return an object based on it's index,
		you can use self.values()[i]."""

		if isinstance(item, slice):
			return self._indexed_values[item]

		try:
			return self._indexed_values[self._indexed_keys.index(item)]
		except (IndexError, ValueError):
			raise KeyError("OrderedDict %s does not hold item '%s'." %(self, item))

	def clear(self):
		self._indexed_keys = []
		self._indexed_values = []

	def keys(self):
		return self._indexed_keys[:]

	def values(self):
		return self._indexed_values[:]

	def items(self):
		return zip(self._indexed_keys, self._indexed_values)

	def iterkeys(self):
		return iter(self._indexed_keys)

	def itervalues(self):
		return iter(self._indexed_values)

	def iteritems(self):
		return izip(self.iterkeys(), self.itervalues())

	def pop(self, key=None):
		return self.popitem(key)[1]

	def popitem(self, key=None):
		if key is None:
			try:
				return self._indexed_keys.pop(), self._indexed_values.pop()
			except IndexError:
				raise KeyError("KeyError: pop from empty %s." %self.__class__.__name__)

		try:
			i = self._indexed_keys.index(key)
		except ValueError:
			raise KeyError("KeyError: '%s' not in %s." %(key, self.__class__.__name__))

		self._indexed_keys.pop(i)

		try:
			return key, self._indexed_values.pop(i)
		except IndexError:
			raise KeyError("KeyError: '%s' not in %s." %(key, self.__class__.__name__))

	def _add_iter(self, iterable):
		"""Items in iterable are (key, value) pairs. They will be assigned an
		index, so as to be able to return pairs based on the order they were
		added."""

		for k, v in iterable:
			
			# If key is present already, overwrite it's value.
			if k in self._indexed_keys:
				j = self._indexed_keys.index(k)
				self._indexed_values[j] = v
			# Otherwise append a new (key, value) pair
			else:
				self._indexed_keys.append(k)
				self._indexed_values.append(v)

	def update(self, iterable=None, **kwargs):
		if iterable is not None:
			self._add_iter(iterable)
		self._add_iter(kwargs.iteritems())
				

class SortedDict(dict):
	def __init__(self, **kwargs):
		dict.__init__(self, **kwargs)
	
	def keys(self):
		return sorted(super(SortedDict, self).keys())
	
	def values(self):
		return [self[k] for k in self.keys()]
	
	def items(self):
		return zip(self.keys(), self.values())

	def iterkeys(self):
		for k in self.keys():
			yield k

	def itervalues(self):
		for k in self.iterkeys():
			yield self[k]

	def iteritems(self):
		return izip(self.iterkeys(), self.itervalues())


class AccumulatorDict(dict):
	"""
	When setting, will append value of pair inside list for the key.
	"""

	def __init__(self, *args, **kwargs):
		self._add_iter(((a, None) for a in args))
		self._add_iter(kwargs.iteritems())

	def _add_iter(self, iterable):
		for k, v in iterable:			
			self.setdefault(k, []).append(v)

	def update(self, **kwargs):
		self._add_iter(kwargs.iteritems())

	def add_tuple(self, iterable):
		self._add_iter(iterable)


class Node(object):
	AND = 'AND'
	OR = 'OR'
	NOT = "NOT"
	connector = AND
	
	def __init__(self, children=[], connector=None, negate=False, parent=None):
		self.children = list(children)
		self.connector = connector or self.connector
		self.negate = negate

	def __str__(self):
		return unicode(self)

	def __unicode__(self):
		return (u"<%s conn=%s, negate=%s:[%s]>" %(
			self.__class__.__name__, self.connector, str(self.negate),
			", ".join([str(ch) for ch in self.children]))
		)

	def __len__(self):
		return len(self.children)

	def __iter__(self):
		return (ch for ch in self.children)

	def __contains__(self, item):
		return item in self.children

	def __nonzero__(self):
		return bool(self.children)

	def __deepcopy__(self, memo):		
		children = [deepcopy(ch, memo) for ch in self.children]
		conn = deepcopy(self.connector, memo)
		negate = deepcopy(self.negate, memo)
		return Node(children, conn, negate)

	def append(self, node, conn=None):
		
		if not node:
			raise Exception("Why add an empty node?")
		
		if not conn:
			conn = self.connector

		if not isinstance(node, Node):
			self.children.append(node)
			return

		if node is self:
			print node, self
			raise Exception("'node' is self: self=%s" % self)

		if node in self.get_branches() and conn == self.connector:
			return

		if not getattr(node, "connector", None):
			self.extend(node)
			return

		if self.connector == node.connector == conn and not node.negate:
			self.extend(node)
		else:			
			clone = deepcopy(self, {})
			self.children = [Node([clone, node], conn)]
			self.negate = False
			

	def extend(self, iterable):
		self.children.extend(iterable)

	def clear(self):
		del self.children[:]

	def get_branches(self):
		all = []
		for ch in self:
			if isinstance(ch, Node):
				all.append(ch)
		return all
	
	def get_leaves(self):
		all = []
		for ch in self:
			if not isinstance(ch, Node):
				all.append(ch)
		return all

	def render(self):
		bits = []
		for ch in self.children:
			bits.append(ch.render())

		bits = filter(None, bits)

		return "".join((
			"NOT "*self.negate,
			"("*((len(bits) > 1) or self.negate),
			(" %s " %self.connector).join(bits),
			")"*((len(bits) > 1) or self.negate)
		))



################################ --- MISC --- ################################

def quicksort(iterable):
	if len(iterable) <= 1:
		return iterable
	pivot = iterable.pop()
	left  = [element for element in iterable if element <  pivot]
	right = [element for element in iterable if element >= pivot]
	return quicksort(left) + [pivot] + quicksort(right)


def zipcmp(iter1, iter2, func=lambda tup: tup[0] is tup[1]):
	assert len(iter1) == len(iter2)
	return len(filter(None, map(func, zip(iter1, iter2)))) == len(iter1)


def import_helper(pkg, obj=None):
	# usage: cls = import_helper('pkgA.pkgB.pkgC', 'objA')
	
	if obj is None:
		m = __import__(pkg, {}, {}, ())
		return m
	
	m = __import__(pkg, {}, {}, [obj])
	return getattr(m, obj)


def flatten(container):
	"""A generator to extract the elements from nested iterables, good for 
		filling a flat container with them."""
	for elem in container:
		if getattr(elem, "__iter__", None) is not None:
			for e in flatten(elem):
				yield e
		else:
			yield elem

def recurse(node):
	all = []
	for branch in node.get_branches():
		all.extend(recurse(branch))
	all.extend(node.get_leaves())
	return all


###################### SQLite Stuff ########################
##                                                        ##

def escape_sql(val):
	val = unicode(val)
	for quotable in r"/|&{}#@^~\\":
		val = val.replace(quotable, r"'%r'" % quotable)
	return val


TIMEFORMAT = "%Y-%m-%d %H:%M:%S.%f"


def datetime_localize(dt, tzname=None):
	"""Make datetime object *dt* timezone aware. If *tzname* is given,
	the timezone will be constructed from it, otherwise, system time 
	is taken. If *dt* is timezone aware already, an exception will be 
	raised.
	"""

	if tzname:
		tz = pytz.timezone(tzname)
	else:
		tz = pytz.timezone(time.tzname[0])
	return tz.localize(dt)


def datetime_make_naive(dt):
	return dt.replace(tzinfo=None)


def datetime_set_tzinfo_by_name(dt, tzname):
	tz = pytz.timezone(tzname)
	if not dt.tzinfo == tz:
		dt = dt.replace(tzinfo=tz)
	return dt


def adapt_datetime_to_string(dt):
	"""Prepares a datetime instance for sqlite storing. If an instance 
	has	no timezone info (*dt.tzinfo*) the locale's timezone will be set.
	"""

	if dt.tzinfo is None:
		dt = datetime_localize(dt)
	return (dt - dt.utcoffset()).strftime(TIMEFORMAT)


def convert_string_to_datetime(instr):
	"""Parse a datetime object from *instr*. The *instr* is assumed
	to be a UTC datetime.
	"""

	dt = datetime.strptime(instr, TIMEFORMAT)

	# first, make it a local timezone-aware object
	dt = datetime_localize(dt)

	# then correct for utcoffset
	return dt + dt.utcoffset()


def escape(instr):
	if not isinstance(instr, basestring):
		return instr
	return sub(r'%', r'%%', instr)



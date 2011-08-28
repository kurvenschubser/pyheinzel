# -*- coding: utf8 -*-

import sys
from copy import deepcopy
from weakref import WeakValueDictionary
from operator import itemgetter
import itertools

from heinzel import settings
from heinzel.core import connection
from heinzel.core import signals
from heinzel.core.sql.dml import (
	SelectQuery, Select, WhereLeaf, Count
)
from heinzel.core.cache import MRUCache
from heinzel.core.info import get_inst_info
from heinzel.core.exceptions import DoesNotExist
from heinzel.core.constants import *



class QuerySetIterator(object):
	def __init__(self, query, store):
		self.query = query
		self.store = store

	def __getitem__(self, item):
		if isinstance(item, (int, long)):
			return list(self._gen(item, item+1))[0]
		if isinstance(item, slice):
			return list(self._gen(item.start, item.stop, item.step))

	def __iter__(self):
		return iter(self._gen())

	def _gen(self, start=None, stop=None, step=None):
		start, stop, step = start or 0, stop or sys.maxint, step or 1

		aliases = self.query.get_selection_aliases()
		pkcol = self.query.model.pk.column_name

		## Save all dirty instances to get consistent results.
		for obj in self.store._dirty.values():
			obj.save()

		for row in self.query.execute().fetchall()[start:stop:step]:
			vars = dict(zip(aliases, row))

			if not (self.query.model, vars[pkcol]) in self.store._alive:
				inst = self.query.model(**vars)
				inf = get_inst_info(inst)
			else:
				inf = self.store._alive[(self.query.model, vars[pkcol])]
				if inf.get_inst() is None:
					## Initializing a new instance with __init__ automatically
					## sets a new InstanceInfo instance which is not useful 
					## here, since the instance info already exists.
					inst = object.__new__(inf.model_info.model)
					inf.set_inst(inst)
					inf._meta["was-reloaded"] = True
				if inf._meta["was-reloaded"] or inf._meta["force-sync"]:
					inf.update(vars)

			self.store._cache.add(inf)
			yield inf.get_inst()

		# Remove any objects in this process that were deleted in other
		# processes.
		else:
			# Delete all self.query.model instances from the cache.
			# There is probably a more efficient way of cleaning the
			# cache (more selectively), but it seems not worth the 
			# effort atm.
			for m, pk in self.store._alive.keys():
				if isinstance(m, self.query.model):
					inf = self.store._alive[(m, pk)]
					if inf.get_inst() is not None:
						signals.fire("model-pre-delete", inf.get_inst(), True)
						signals.fire("model-post-delete", inf.get_inst(), True)
			


class Storage(object):
	def __init__(self, cache=None):
		# {(InstanceInfo(instance).model_info.model, instance.pk): InstanceInfo, ...}}
		self._alive = WeakValueDictionary()

		# {InstanceInfo(instance): instance, ...}}
		self._dirty = {}

		if cache is not None:
			self._cache = cache
		else:
			self._cache = MRUCache(settings.MAX_CACHE)

		signals.register(
			(
				"instance-deleted",
	
				"start-tracking-changes",
				"stop-tracking-changes",
	
				"model-pre-init",
				"model-post-init",
				"model-pre-save",
				"model-post-save",
				"model-pre-delete",
				"model-post-delete",
				"model-pre-update",
				"model-post-update",
				
				# "model-history-reset",
				# "model-history-redo",
				# "model-history-undo",
				
				"relation-pre-get",
				"relation-post-get",
				"relation-pre-set",
				"relation-post-set",
				"relation-pre-delete",
				"relation-post-delete",
				"relation-pre-add",
				"relation-post-add",
				"relation-pre-remove",
				"relation-post-remove",

				"model-do-cache",
				"model-do-not-cache",
			),
			self
		)
		signals.register_with_callback("cache-rollback", self, "rollback")

	def get(self, query):
		return QuerySetIterator(query, self)

	def clear(self):
		self._dirty.clear()
		self._alive.clear()
		self._cache.clear()

	def set_dirty(self, inst_info):
		self._dirty[inst_info] = inst_info.get_inst()

	def cache(self, inf):
		self._alive.pop((inf.model_info.model, inf._lazypkval), None)
		self._alive[(inf.model_info.model, inf.get_pk_as_key())] = inf
		self._cache.add(inf)

	def uncache(self, inf):
		if inf in self._cache:
			self._cache.remove(inf)

		self._dirty.pop(inf, None)
		self._alive.pop((inf.model_info.model, inf.get_pk_as_key()), None)
		self._alive.pop((inf.model_info.model, inf._lazypkval), None)

	### signals ###

	#??? what is this used for?
	def instance_deleted(self, inst_info):
		print "instance_deleted", inst_info

	def model_pre_init(self, instance, **kwargs):
		signals.fire("stop-tracking-changes", instance=instance)

	def model_post_init(self, instance, **kwargs):
		inf = get_inst_info(instance)
		signals.fire("start-tracking-changes", instance=instance)
		self._alive[(inf.model_info.model, inf.get_pk_as_key())] = inf

		# If instance was not initialized with a value for primary key,
		# then it has not been saved yet and goes into self._dirty.
		if instance.pk is None:
			self.set_dirty(inf)

	def start_tracking_changes(self, instance):
		get_inst_info(instance)._meta["track-changes"] = True

	def stop_tracking_changes(self, instance):
		get_inst_info(instance)._meta["track-changes"] = False

	def model_pre_save(self, instance):
		pass

	def model_post_save(self, instance, created):
		inf = get_inst_info(instance)
		if not inf._meta["do-cache"]:
			return

		self.cache(inf)
		self._dirty.pop(inf, None)

		# On calling Model.delete, tracking of changes is stopped, so start
		# tracking now.
		signals.fire("start-tracking-changes", instance=instance)

	def model_pre_update(self, instance, value, fieldname):
		# instance._inst_info.record_change(fieldname, value)
		pass

	def model_post_update(self, instance, value, fieldname):
		inf = get_inst_info(instance)

		if not inf in self._dirty:
			self.set_dirty(inf)

	def model_pre_delete(self, instance):
		signals.fire("stop-tracking-changes", instance=instance)

	def model_post_delete(self, instance, deleted):
		if not deleted:
			return

		inf = get_inst_info(instance)

		self.uncache(inf)

		instance.id = None

	def model_do_cache(self, instance):
		inf = get_inst_info(instance)
		self.cache(inf)
		self.set_dirty(inf)
		inf._meta["do-cache"] = True
		signals.fire("start-tracking-changes", instance=instance)

	def model_do_not_cache(self, instance):
		inf = get_inst_info(instance)
		self.uncache(inf)
		inf._meta["do-cache"] = False
		signals.fire("stop-tracking-changes", instance=instance)

	def model_history_reset(self, instance, **kwargs):
		raise NotImplementedError

	def model_history_undo(self, instance, fieldname, **kwargs):
		raise NotImplementedError

	def model_history_redo(self, instance, fieldname, **kwargs):
		raise NotImplementedError

	def relation_pre_get(self, manager, **kwargs):
		pass
	
	def relation_post_get(self, manager, **kwargs):
		pass

	def relation_pre_set(self, manager, values, **kwargs):
		pass
	
	def relation_post_set(self, manager, values, **kwargs):
		pass

	def relation_pre_delete(self, manager, **kwargs):
		pass

	def relation_post_delete(self, manager, **kwargs):
		pass

	def relation_pre_add(self, manager, values, **kwargs):
		pass

	def relation_post_add(self, manager, values, **kwargs):
		pass

	def relation_pre_remove(self, manager, values, **kwargs):
		pass

	def relation_post_remove(self, manager, values, **kwargs):
		pass

storage = Storage()



class BaseQuerySet(object):
	def __init__(self, model, store=None, query=None, db=None):
		self.model = model
		self.store = store or storage
		self.query = query or SelectQuery(model, db)
		self.db = db or connection.connect()

	def __str__(self):
		return unicode(self).encode(settings.DEFAULT_ENCODING)
	
	def __unicode__(self):
		return unicode(map(str, self.eval()))

	def __repr__(self):
		return str(map(str, self.eval()))

	def __eq__(self, other):
		return type(self) == type(other)\
			and list(self.eval()) == list(other.eval())

	def __ne__(self, other):
		return not self.__eq__(other)

	def __iter__(self):
		return (inst for inst in self.eval())

	def __getitem__(self, item):
		return self.eval()[item]

	def __contains__(self, item):
		return item in self.eval()

	def __len__(self):
		return len(list(self.eval()))

	def filter(self, *qobjs, **filters):
		clone = self._clone()
		clone.query._filter(False, qobjs, filters)
		return clone

	def exclude(self, *qobjs, **filters):
		clone = self._clone()
		clone.query._filter(True, qobjs, filters)
		return clone

	def orderby(self, token=None):
		clone = self._clone()
		clone.query.orderby(token)
		return clone

	def limit(self, by=None, offset=None):
		clone = self._clone()
		clone.query.limit(by, offset)
		return clone

	def count(self, db_column):
		clone = self._clone()
		clone.query.selection_node.clear()
		clone.query.annotation_node.clear()
		clone.query.orderby_node.clear()
		clone.query.limit_node.clear()
		clone.query._aggregate((Count(db_column),), {})
		return clone.query.execute().fetchall()[0][0]
		
	#? implement: is there a valid use case for a reset method?
	def reset(self):
		raise NotImplementedError

	#! fix: since aggregate uses method 'as_dict', it hits the database for
	# raw values, bypassing the cache. it should pull the values from the cache.
	def aggregate(self, *args, **kwargs):
		clone = self._clone()
		clone.query._aggregate(args, kwargs)		
		return clone.as_dict()[0]

	def annotate(self, *args, **kwargs):
		clone = self._clone()
		clone.query._annotate(args, kwargs)
		return clone

	def select(self, *args, **kwargs):
		clone = self._clone()
		clone.query._aggregate(
			map(Select, args), 
			dict([(k, Select(v)) for k, v in kwargs.items()])
		)
		return clone.as_dict()

	def distinct(self):
		clone = self._clone()
		clone.query._distinct = True
		return clone

	def raw(self, stmt=None, values={}):
		if stmt:
			return self.store._db.execute(stmt, values)
		elif not stmt and values:
			raise Exception(
				"%s.raw() got values without a statement" \
					% self.__class__.__name__
			)
		return self.query.execute().fetchall()

	def as_dict(self):
		keys = self.query.get_selection_aliases()
		raw_values = self.raw()
		if not raw_values:
			return {}

		assert len(keys) == len(raw_values[0]), str(raw_values)

		dlist = []

		for values in raw_values:
			dlist.append(dict(zip(keys, values)))

		return dlist

	def evaluate(self):
		return self.store.get(self.query)
	eval = evaluate

	def _clone(self):
		query = deepcopy(self.query, {})
		return type(self)(query.model, self.store, query, self.db)

QuerySet = BaseQuerySet

# Relations between different models are described here generically
#
#
#	example: Car(Model)
#			brand = ForeignKeyField(Brand)
#	->
#	SELECT * FROM car_table, brand_table WHERE car_table.id = brand_table.car_id
#
#
from heinzel.core import connection
from heinzel.core import signals
from heinzel.core.exceptions import ValidationError
from heinzel.core.sql.ddl import link_table_name
from heinzel.core.sql.dml import (DeleteQuery, UpdateQuery,
	LinkerTableInsertQuery, LinkerTableDeleteQuery, LinkerTableDeleteAllQuery,
	ForeignKeyUpdateQuery)
from heinzel.core.descriptors import (RelationDescriptor, DeferredLoading)
from heinzel.core.queries import QuerySet

from heinzel.core.constants import FK, M2M, O2O, MODES


class Relation(object):

	related_model = DeferredLoading("_related_model")

	def __init__(self, model, related_model, identifier, reverse_identifier, mode):

		#! implement: recursive relations
		if related_model == "self" or model == related_model:
			raise NotImplementedError(
				("Recursive relations not (yet) supported: model='%s', "
				"related_model='%s'." %(model, related_model))
			)

		self.model = model
		self.related_model = related_model
		self.identifier = identifier
		self.reverse_identifier = reverse_identifier
		self.mode = mode
		
		if self.mode == FK:
			self._reverse_manager = ReverseForeignKeyManager(self)				
			self._forward_manager = ForeignKeyManager(self)

		if self.mode == M2M:
			self._forward_manager = ManyToManyManager(self)
			self._reverse_manager = ManyToManyManager(self)

		if self.mode == O2O:
			self._forward_manager = OneToOneManager(self)
			self._reverse_manager = OneToOneManager(self)

	def __str__(self):
		return unicode(self)

	def __unicode__(self):
		return ("<Relation instance at 0x%x. model=%s, related_model=%s, "
				"identifier=%s, reverse_identifier='%s', mode=%s>"
					%(id(self), self.model, self.related_model,
						self.identifier, self.reverse_identifier, self.mode)
				)

	def __eq__(self, other):
		return (	type(self) == type(other)
				and self.mode == other.mode
				and (
						(
							self.model == other.model
							and self.related_model == other.related_model
							and self.identifier == other.identifier
							and self.reverse_identifier == other.reverse_identifier
						)
					or 
						(
							self.model == other.related_model
							and self.related_model == other.model
							and self.identifier == other.reverse_identifier
							and self.reverse_identifier == other.identifier
						)
					)
				)

	def __ne__(self, other):
		return not self.__eq__(other)

	def __hash__(self):
		try:
			return self._hash
		except AttributeError:
			try:
				self._hash = hash(self._hash_string)
			except AttributeError:
				if isinstance(self.related_model, basestring):
					related_model_name = self.related_model
				else:
					related_model_name = self.related_model.__name__

				self._hash_string = "_".join(
					(	
						self.model.__name__,
						related_model_name,
						self.identifier,
						self.reverse_identifier,
						str(self.mode)
					)
				)
				self._hash = hash(self._hash_string)
		return self._hash

	def get_manager_for_instance(self, inst, identifier):
		if not self.has_identity(type(inst), identifier):
			raise Exception(
				"Wrong setup for RelationManager pertaining to %s: inst=%s, identifier=%s, 1=%s, 2=%s"
				% (self, inst, identifier, self.identifier == identifier, self.model == type(inst))
			)

		if self.is_reverse_by_identifier(identifier):
			mngr = self._reverse_manager
		else:
			mngr = self._forward_manager

		return mngr.setup(inst, identifier)

	def has_model(self, model):
		try:
			return model == self.model or model == self.related_model
		except ImportError, e:
			# will be raised by ‘descriptors.DeferredLoading'.
			raise ImportError(
				"Could not verify that RelationDescriptor %s.%s belongs to "
				"Relation %s: %s" % (model, self, e)
			)
			return False

	def has_identity(self, model, identifier):
		try:
			return (((model == self.model) and (identifier == self.identifier))
					or ((model == self.related_model) and (identifier == self.reverse_identifier)))
		except ImportError, e:
			# will be raised by ‘descriptors.DeferredLoading'.
			raise ImportError(
				"Could not verify that RelationDescriptor %s.%s belongs to "
				"Relation %s: %s" % (model, identifier, self, e)
			)

	def is_reverse_by_model(self, model):
		assert ((model == self.model) or (model == self.related_model))
		return model == self.related_model
	
	def is_reverse_by_identifier(self, identifier):
		assert identifier in (self.identifier, self.reverse_identifier)
		return identifier == self.reverse_identifier

	def is_self_related(self):
		return self.model == self.related_model

	def _get_identifier_for_model(self, model):
		if self.is_reverse_by_model(model):
			return self.reverse_identifier
		return self.identifier

	def _get_reverse_identifier_for_model(self, model):
		if self.is_reverse_by_model(model):
			return self.identifier
		return self.reverse_identifier

	def _get_other_identifier(self, identifier):
		if self.is_reverse_by_identifier(identifier):
			return self.identifier
		return self.reverse_identifier

	def _get_other_model(self, model):
		if self.is_reverse_by_model(model):
			return self.model
		return self.related_model


class RelationRegistry(set):
	def __init__(self, relations=[]):
		super(RelationRegistry, self).__init__(relations)

	def append(self, relation):
		if isinstance(relation, Relation) and not relation in self:
			super(RelationRegistry, self).add(relation)

	def get_identifiers(self):
		ids = []
		for r in self:
			ids.append(r.identifier)
			ids.append(r.reverse_identifier)
		return ids

	def get_relation_by_identity(self, model, identifier):
		for r in self:
			if r.has_identity(model, identifier):
				return r

	def get_relations_for_model(self, model):
		for r in self:
			if r.has_model(model):
				yield r

	def get_fields_for_model(self, model):
		fields = []
		for r in self.get_relations_for_model(model):
			fields.append(r._get_identifier_for_model(model))
		return fields

	def add_new(self, model, related_model, identifier, reverse_identifier,
																		mode):
		super(RelationRegistry, self).add(
			Relation(
				model, related_model, identifier, reverse_identifier, mode
			)
		)


registry = RelationRegistry()


class BaseRelationManager(object):

	def __init__(self, relation, db=None):
		self.relation = relation
		self.db = db or connection.connect()

	def __str__(self):
		return str(list(self.all()))

	def __len__(self):
		return len(self.get_query_set())

	def __iter__(self):
		return iter(self.get_query_set())

	def __contains__(self, item):
		return item in self.get_query_set()

	def __getitem__(self, item):
		return self.get_query_set().__getitem__(item)

	def set(self, values):
		'''Set ‘‘values‘‘ to be the new related items, erasing any others.'''
		
		# assert self.relation.has_model(type(values[0])), (str(values[0]),
				# str(type(values[0])), str(self.relation.model),
				# str(self.relation.related_model))

		signals.fire("relation-pre-set", manager=self, values=values)
		self._set(values)
		signals.fire("relation-post-set", manager=self, values=values)

	def delete(self):
		'''For removing all items from the relation.'''

		signals.fire("relation-pre-delete", manager=self)
		self._delete()
		signals.fire("relation-post-delete", manager=self)

	def add(self, values):
		'''For adding ‘‘values‘‘ to the already related items.'''

		# assert self.relation.has_model(type(values[0])), (str(values[0]),
				# str(type(values[0])), str(self.relation.model),
				# str(self.relation.related_model))

		signals.fire("relation-pre-add", manager=self, values=values)
		self._add(values)
		signals.fire("relation-post-add", manager=self, values=values)

	def remove(self, values):
		'''For removing ‘‘values‘‘ from the relation.'''

		
		# assert self.relation.has_model(type(values[0])), (str(values[0]),
				# str(type(values[0])), str(self.relation.model),
				# str(self.relation.related_model))

		signals.fire("relation-pre-remove", manager=self, values=values)
		self._remove(values)
		signals.fire("relation-post-remove", manager=self, values=values)

	@property
	def identifier(self):
		# return self.relation._get_identifier_for_model(self.model)
		return self._identifier

	@property
	def reverse_identifier(self):
		# return self.relation._get_reverse_identifier_for_model(self.model)
		return self.relation._get_other_identifier(self.identifier)

	@property
	def points_to(self):
		return self.relation._get_other_model(self.model)

	def get_query_set(self):
		return self.points_to.objects.filter(
			**{self.reverse_identifier: self.owner.pk}
		)
	get = all = get_query_set

	def setup(self, inst, identifier):
		self.owner = inst
		self.model = type(inst)
		self._identifier = identifier
		return self

	def _set(self, values):
		"""Override"""
		pass

	def _delete(self):
		"""Override"""
		pass

	def _add(self):
		"""Override."""
		pass

	def _remove(self):
		"""Override."""
		pass

		
	#? implement: Currently, only model instances with an id != None are accepted as keys to 
	# related models, to prevent any unsaved instances to be used as keys.
	# Make it accept any datatype as key to other model, as long
	# as that datatype can be used as such. E.g. if an int is given as key,
	# and the primary key of the related_model is of type int, accept that as key.
	# This would require modifying the triggers for the database, that currently prevent this.
	def _type_check(self, inst):

		# if isinstance(newval, mngr.points_to):
			# v = newval.pk
		# elif newval is None:
			# v = None
		# elif isinstance(newval, mngr.points_to.pk.get_type()):
			# v = newval
		# else:
			# raise Exception(
				# "Need either a Model instance or None or instance "
				# "of mngr.points_to.pk.get_type(). Got %s." %v
			# )


		if not isinstance(inst, self.points_to):
			raise ValidationError(
				u"%s: need an instance of %s, got %s" %(
				self.__class__.__name__, self.points_to, inst)
			)


class ManyToManyManager(BaseRelationManager):
	def __init__(self, relation):
		BaseRelationManager.__init__(self, relation)

	def _set(self, values):
		self._delete()
		self._add(values)

	def _delete(self):
		if not getattr(self.owner, 'id', None):
			raise AttributeError(
				"The owner of this relation manager does not have an id. Has "
				"it been saved yet?"
			)

		q = LinkerTableDeleteAllQuery(self.relation, self.owner,
											self.identifier, self.db)
		q.execute()
		q.commit()

	def _add(self, values):
		if not values:
			return

		if getattr(self.owner, 'id', None) is None:
			raise AttributeError(
				"The owner of this relation manager does not have an id. Has "
				"it been saved yet?"
			)

		for v in values:
			if not getattr(v, "id", None):
				raise AttributeError(
					"This instance does not have an id. Has it been saved "
					"yet?"
				)

			self._type_check(v)

		q = LinkerTableInsertQuery(self.relation, self.owner, self.identifier,
															values, self.db)
		q.execute()
		q.commit()


	def _remove(self, values):
		if getattr(self.owner, 'id', None) is None:
			raise AttributeError(
				"The owner of this relation manager does not have an id. Has "
				"it been saved yet?"
			)

		for v in values:
			if not getattr(v, "id", None):
				raise AttributeError(
					"This instance does not have an id. Has "
					"it been saved yet?"
				)

			self._type_check(v)

		q = LinkerTableDeleteQuery(self.relation, self.owner, self.identifier,
															values, self.db)
		q.execute()
		q.commit()


class OneToOneManager(ManyToManyManager):
	def __init__(self, relation):
		ManyToManyManager.__init__(self, relation)

	def _set(self, values):
		assert len(values) == 1, 'RelationManager %s expected 0 or 1 value to be added to instance cache, got %s' %(self, len(values))

		# Since this manager represents a one-to-one relation, entries in the
		# linker table are unique. To maintain uniqueness, it is not enough to
		# delete the entry on self.owner's side of the linker table. The
		# entry of the instance-to-be-set (values[0]) has to be deleted as 
		# well.
		self._delete()
		
		owner = self.owner
		ident = self.identifier

		rev_mngr = self.relation.get_manager_for_instance(values[0], 
											self.reverse_identifier)
		rev_mngr._delete()
		
		
		# print self.owner, self.owner.id, self.identifier, rev_mngr.owner, rev_mngr.owner.id, rev_mngr.identifier, rev_mngr is self, rev_mngr.owner is self.owner, self.owner is owner
		# raw_input("OneToOneManager._set")
		
		self.setup(owner, ident)

		# print "o2o", values, values[0].id, self.owner, self.identifier, self.reverse_identifier, rev_mngr.owner, rev_mngr.identifier, rev_mngr.reverse_identifier
		self._add(values)

	def _delete(self):
		if not getattr(self.owner, 'id', None):
			raise AttributeError("The owner of this relation manager does not have an id. Has it been saved yet?")

		q = LinkerTableDeleteAllQuery(self.relation, self.owner,
											self.identifier, self.db)
		q.execute()
		q.commit()

	def _remove(self):
		raise NotImplemented


class ForeignKeyManager(BaseRelationManager):
	def __init__(self, relation):
		BaseRelationManager.__init__(self, relation)

	def _set(self, values):
		assert len(values) == 1, 'RelationManager %s expected 1 value to be added to instance cache, got %s' %(self, len(values))
		inst = values[0]
		
		# if inst in self.all():
		# 	return

		self._type_check(inst)

		q = ForeignKeyUpdateQuery(self.owner, self.identifier, inst.pk, self.db)
		q.execute()
		q.commit()

	_add = _set

	def _delete(self):
		q = ForeignKeyUpdateQuery(self.owner, self.identifier, None, self.db)
		q.execute()
		q.commit()

	def _remove(self):
		raise NotImplemented


class ReverseForeignKeyManager(BaseRelationManager):
	def __init__(self, relation):
		BaseRelationManager.__init__(self, relation)

	def _set(self, values):
		self._delete()

		for v in values:
			mngr = self.relation.get_manager_for_instance(v, self.reverse_identifier)
			mngr._set((self.owner,))

	def _add(self, values):
		for v in values:
			mngr = self.relation.get_manager_for_instance(v, self.reverse_identifier)
			mngr._add((self.owner,))

	def _delete(self):
		for v in self.get_query_set():
			mngr = self.relation.get_manager_for_instance(v, self.reverse_identifier)
			mngr._delete()

	def _remove(self, values):
		for v in values:
			mngr = self.relation.get_manager_for_instance(v, self.reverse_identifier)
			mngr._delete()

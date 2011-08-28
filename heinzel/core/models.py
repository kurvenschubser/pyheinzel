import sys
from itertools import izip

from heinzel.core import connection
from heinzel.core import signals
from heinzel.core import relations
from heinzel.core.managers import Manager
from heinzel.core.fields import *
from heinzel.core.queries import BaseQuerySet
from heinzel.core.sql.dml import (SelectQuery, InsertQuery, DeleteQuery,
	UpdateQuery, Q)

from heinzel.core.descriptors import (PrimaryKeyDescriptor, 
	DataFieldDescriptor, RelationDescriptor)

from heinzel.core.exceptions import (SQLSyntaxError, ValidationError, 
	DatabaseSanityError)

from heinzel import settings


# All models that need database access need to be put inside this list. 
# E.g. `import models; models.register([YourModel1, YourModel2])`.
#? TODO: Wrap in class
registry = []


def setup_relations():
	for m in registry:
		for r in list(relations.registry.get_relations_for_model(m)):
			other_m = r._get_other_model(m)
			if not other_m in registry:
				raise ValidationError(
					"Model has not been registered with models.registry! "
					"Model: %s. Relation: %s." %(other_m, r)
				)
			
			# Relation to self
			if other_m is m:
				# after this if, the next ident will be the reverse_identifier
				# of the relation if other_m is m
				ident = r.identifier
				desc = RelationDescriptor(r, ident)
				setattr(m, ident, desc)
				
			m._relations.append(r)
			ident = r._get_identifier_for_model(m)
			desc = RelationDescriptor(r, ident)
			setattr(m, ident, desc)


def register(models):
	for m in models:
		if m not in registry:
			registry.append(m)
	setup_relations()


class ModelBase(type):
	def __new__(cls, name, bases, attrs):
		new_class = super(ModelBase, cls).__new__(cls, name, bases, attrs)

		if name == "Model":
			#print "bailing out early..."
			return new_class

		m = Manager()
		m.contribute_to_class(new_class, "objects")

		# Don't forget to ’’setup_relations’’ after all Models have been constructed
		new_class._relations = relations.RelationRegistry()

		new_class.pk = PrimaryKeyDescriptor()

		#register fields
		new_class._fields = dict([(k, v) for k, v in new_class.__dict__.items() if isinstance(v, Field)])

		try:	
			pk = new_class.get_primary_key()
		except:
			new_class._fields["id"] = IntegerField(primary_key=True)
			new_class._primary_key = "id"

		if new_class._primary_key != "id":
			new_class._fields["id"] = IntegerField(primary_key=False, auto_increment=True)


		# Register Relations, set Descriptors for data fields (non-RelationFields) and 
		# set related_names on those fields
		for fname, f in new_class._fields.items():
			if isinstance(f, RelationField):
				f.set_related_name(new_class)

				if isinstance(f, ForeignKeyField):
					f.column_name = f.column_name or fname + "_id"
					mode = relations.FK
				elif isinstance(f, ManyToManyField):
					mode = relations.M2M
				elif isinstance(f, OneToOneField):
					mode = relations.O2O

				relations.registry.add_new(new_class, f.related_model, fname, f.related_name, mode)
			else:
				f.column_name = f.column_name or fname
				
				# overwrite fields on class with datafield descriptors for the fields.
				setattr(new_class, fname, DataFieldDescriptor(fname))

			f.name = fname

		# Has to be set after the other Fields got their column_name and name
		new_class._fields["pk"] = new_class._fields[new_class._primary_key]
		
		
		return new_class


class Model(object):

	__metaclass__ = ModelBase

	def __init__(self, **kwargs):

		signals.fire("model-pre-init", instance=self, kwargs=kwargs)

		for fname, f in self.fields().items():
			if f.attrs.get("initial") is not None:
				if callable(f.attrs["initial"]):
					value = f.attrs["initial"]()
				else:
					value = f.attrs["initial"]
				setattr(self, fname, value)

		# Set any Field and non-Field parameters on this instance
		for name, value in kwargs.items():
			if name in self._relations.get_identifiers():
				raise TypeError("'%s' refers to a RelationManager. "\
						"RelationManagers can't be set on instantiating, "\
						"because at that point, the instance has not been "\
						"created and so has no id with which to link it to %s."\
						% (name, value))

			setattr(self, name, value)

		signals.fire("model-post-init", instance=self, kwargs=kwargs)

	def __new__(cls, **kwargs):
		return super(Model, cls).__new__(cls)

	def __setattr__(self, name, value):
		field = self.get_field_by_column_name(name)
		if field:
			name = field.name
		super(Model, self).__setattr__(name, value)

	def __getattr__(self, name):
		if name in self.__dict__:
			return self.__dict__[name]
			
		field = self.get_field_by_column_name(name)
		if field:
			o = getattr(self, field.name)
			if isinstance(o, Model):
				return o.pk
			return o

		raise AttributeError("%s doesn't have attribute '%s'." %(self, name))

	def __str__(self):
		if getattr(self, "__unicode__", None):
			# return unicode(self).encode(settings.DEFAULT_ENCODING)
			return unicode(self).encode(settings.DEFAULT_ENCODING)
		return repr(self)

	def __unicode__(self):
		return u"<%s instance at 0x%x>" %(self.__class__.__name__, 
											id(self))


	def __eq__(self, other):
		if self.pk is None or other.pk is None:
			# If any instance has no pk value, compare by identity.
			return self is other
		return type(self) == type(other) and self.pk == other.pk

	def __ne__(self, other):
		return not self.__eq__(other)	

	@classmethod
	def fields(cls):
		return cls._fields

	@classmethod
	def many_related(cls):
		return dict([(k, v) for k, v in cls.fields().items()
			if isinstance(v, (ManyToManyField, OneToOneField))]
		)

	@classmethod
	def non_many_related(cls):
		return dict([(k, v) for k, v in cls.fields().items()
			if k not in cls.many_related()]
		)

	@classmethod
	def related(cls):
		return dict(
			[(k, v) for k, v in cls.fields().items() 
				if isinstance(v, RelationField)]
		)

	@classmethod
	def non_related(cls):
		return dict(
			[(k, v) for k, v in cls.fields().items()
				if k not in cls.related()]
		)

	@classmethod
	def foreignkeys(cls):
		return dict([(k, v) for k, v in cls.fields().items()
			if isinstance(v, ForeignKeyField)]
		)

	@classmethod
	def get_column_names(cls):
		"""
		The column names on the model's table. Since through the 'pk'
		Field alias there are duplicate entries, make it a set.
		"""
		
		ret = set([v.column_name for v in cls.non_many_related().values()])
		return ret 

	def get_column_values(self):
		"""The values on this instance to be inserted (or updated) in the
			database."""
		return self.get_column_names_values().values()

	def get_column_names_values(self):
		"""Return a dict of all non many related fields' column_names as keys
			and the instance's values on these fields as values."""

		return dict([(k, getattr(self, k)) for k in self.get_column_names()])

	def get_field_names_values(self):
		d = {}
		for k in self.non_many_related():
			attr = getattr(self, k)
			if isinstance(attr, Model):
				attr = attr.pk
			if attr is not None:
				d.update(k=attr)
		return d

	@classmethod
	def get_field_by_column_name(cls, name):
		for f in cls.fields().values():
			if f.column_name == name:
				return f

	def get_unique_fields(self):
		d = {}
		for k, v in self.non_many_related().items():
			if v.primary_key or v.unique:
				d.update(k=v)
		return d
	
	def get_non_unique_fields(self):
		uniques = self.get_unique_fields().values()
		d = {}
		for k, v in self.non_many_related().items():
			if not v in uniques:
				d.update(k=v)
		return d

	def get_non_related_field_names_values(self):
		d = dict(
			((k, getattr(self, k)) for k in self.non_related())
		)
		return d

	def save(self):
		"""When overriding this method, do not forget to call the Model.save()
		method and to return a tuple of (instance, created), where created
		means, it the instance was newly INSERTED into the database.
		"""

		signals.fire("model-pre-save", instance=self)
		inst, created = self._save()
		signals.fire("model-post-save", instance=self, created=created)
		return inst, created

	def _save(self):
		"""Here we save an instance of a model to the database. If the instance
		does not have a value for it's 'id' field, an entry will be
		INSERTed. 'created' will then be set to True.
		When an entry already exists for the given values and given any
		unique constraints, try to update that entry with any non-unique
		columns. In case of an update, 'created' will be False.
		"""

		if not self.id:
			## If this particular instance has no id, try to insert it into the
			## database.

			iq = InsertQuery(self)
			res = iq.execute()
			self.id = res.lastrowid
			iq.commit()
			created = True

			## Now that the row was successfully updated or it was 
			## determined that an update was not necessary, get that row's
			## id and put it into self

			## Get all fields that are not RelationFields and whose instance
			## value is not None. RelationFields get created afterwards, so 
			## they can't be included in the search for the “id“ of self at
			## this point.
			# searchvals = self.get_non_related_field_names_values()
			
			## We need to look for the instance's id, so exclude those values 
			## from the where clause.
			# searchvals.pop("pk")
			# searchvals.pop(self.fields()["pk"].name)
			
			# id_qs = type(self).objects.filter(**searchvals)
			# results = id_qs.select("id")


			## This should only be one...
			# if len(results) != 1:
				# print id_qs.query
				# print results
				# raise Exception("Model._save: Something wrong on selecting id")

			# if not isinstance(results[0]["id"], int):
				# raise Exception("Need exactly one result for 'id' query while "
					# "updating model instance %s. Found %s:" % (self, len(self.id), results))

			# self.id = results[0]["id"]

		else:
			## if it already has an id, try to update it.
			try:
				uq = UpdateQuery(self)
				res = uq.execute()
				uq.commit()
			except:
				raise 
			
			created = False

		return self, created

	def delete(self, force_delete=False):
		signals.fire("model-pre-delete", instance=self)
		instance, deleted = self._delete()
		signals.fire("model-post-delete", instance=self, deleted=deleted)
		return instance, deleted

	def _delete(self):
		if self.pk:
			dq = DeleteQuery(type(self), {type(self).pk.column_name: self.pk})
			dq.execute()
			dq.commit()
			deleted = True
		else:
			deleted = False
		return self, deleted

	def uncache(self):
		signals.fire("model-do-not-cache", instance=self)

	def reset(self, fieldname=None):
		"""Roll back all changes to one or all of self's data fields. The 
		data fields will have the values as if they were freshly 
		instantiated. To roll back all data fields, leave ‘‘fieldname‘‘ 
		set to 'None'.
		"""

		raise NotImplementedError

	def undo(self, fieldname=None):
		"""Undo the last change to a data field. 
		"""

		raise NotImplementedError

	def redo(self, fieldname=None):
		"""Undo the last undo.
		"""

		raise NotImplementedError

	@classmethod
	def get_primary_key(cls):
		"""
		Returns the primary key of the model as a string.
		If there is more than one field with the 'primary_key' property
		set to 'True', an exception will be raised. Same holds if there
		is no field with 'primary_key' set to 'True'.
		"""

		if not getattr(cls, "_primary_key", None):
			r = []
			for n, v in cls.fields().items():
				if v.primary_key:
					r.append(n)
			if len(r) == 1:
				cls._primary_key = r[0]
			elif len(r) > 1:
				raise Exception("Model %s has more than 1 primary key: %s" %(cls, l))
			else:
				raise Exception("Model %s has no primary key!" %cls)
		return cls._primary_key

	@classmethod
	def tablename(cls):
		"""
		The tablename returned here is being used in the SQL generation.
		"""
		
		return getattr(cls, "_tablename", None) or cls.__name__.lower() + "s"

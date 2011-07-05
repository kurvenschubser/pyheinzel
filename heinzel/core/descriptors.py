from heinzel.core import signals

from heinzel.core.info import get_inst_info
from heinzel.core.constants import FK, M2M, O2O



class DeferredLoading(object):

	def __init__(self, fieldname, fallback=True):
		self.fieldname = fieldname
		self.fallback = fallback

	def __get__(self, inst, cls):
		obj = getattr(inst, self.fieldname, None)

		if isinstance(obj, basestring):
			try:
				from heinzel.core.models import registry as model_registry
			except ImportError, e:
				raise

			if obj == 'self':
				if getattr(inst, "model", None) is not None:
					# DeferredLoading descriptors sit on Relation instances.
					# Those are easily identifiable through their 
					# ‘model‘ attribute, which is what we're looking for.
					# print "obj == self", inst.model
					# raw_input()
					setattr(inst, self.fieldname, inst.model)
				else:
					for m in model_registry:
						# DeferredLoading descriptors sit on RelationField 
						# instances as well, which are unambiguously 
						# identifiable by identity.
						
						# print "DeferredLoading", m, id(inst), map(id, m.fields.values())
						# raw_input()
						if inst in m._fields.values():
							setattr(inst, self.fieldname, m)
							break

			for m in model_registry:
				if m.__name__ == obj:
					setattr(inst, self.fieldname, m)
					break

			if not self.fallback:
				raise ImportError(
					"Could not find object '%s' via deferred loading."
					"type(inst)=%s, id(inst)=%i" % (obj, type(inst), id(inst))
				)
			
			# print "DeferredLoading end", getattr(inst, self.fieldname)
			# raw_input()
		
		return getattr(inst, self.fieldname)

	def __set__(self, inst, val):
		setattr(inst, self.fieldname, val)


class PrimaryKeyDescriptor(object):
	def __get__(self, inst, cls):
		if inst is not None:
			return getattr(inst, cls.get_primary_key())
		return cls._fields[cls.get_primary_key()]

	def __set__(self, inst, val):
		setattr(inst, inst.get_primary_key(), val)

	def __delete__(self, inst):
		setattr(inst, inst.get_primary_key(), None)


class DataFieldDescriptor(object):
	def __init__(self, name):
		self.name = name

	def __get__(self, inst, cls):
		if inst is None:
			raise Exception("no access of %s via class!" %self)

		return get_inst_info(inst).get(self.name)

	def __set__(self, inst, val):
		inst_info = get_inst_info(inst)

		if inst_info._meta["track-changes"]:
			signals.fire("model-pre-update", instance=inst,
						value=inst_info.get(self.name), fieldname=self.name)

		field = type(inst).fields()[self.name]
		val = field.to_python(val)
		inst_info[field.column_name] = val

		if inst_info._meta["track-changes"]:
			signals.fire("model-post-update", instance=inst, value=val,
													fieldname=self.name)

	def __delete__(self, inst):
		self.__set__(inst, None)


class RelationDescriptor(object):
	def __init__(self, relation, identifier):
		self.relation = relation
		self.identifier = identifier

	def __get__(self, inst, cls):
		if inst is None:
			raise Exception("no access of %s via class!" %self)

		mngr = self.relation.get_manager_for_instance(inst, self.identifier)

		if ((self.relation.mode == FK
				and not self.relation.is_reverse_by_model(mngr.model))
				or self.relation.mode == O2O):

			res = list(mngr.all())
			if not res:
				return None
			if len(res) == 1:
				return res[0]
			if len(res) > 1:
				raise ValueError(
					"RelationDescriptor for Relation of mode '%s' wants to "
					"return more than one value: %s."
					%(self.relation.mode, len(res))
				)
		else:
			return mngr

	def __set__(self, inst, val):
		mngr = self.relation.get_manager_for_instance(inst, self.identifier)

		if not val:
			return mngr.delete()

		if getattr(val, '__iter__', None) is None:
			val = (val,)

		# In case of a foreign key or one-to-one relation, only one
		# value is going to be set on the manager.
		if ((self.relation.mode == FK
			and not self.relation.is_reverse_by_model(type(inst)))
			or self.relation.mode == O2O):

			if len(val) != 1:
				raise ValueError(
					"Need exactly one value to set on ForeignKeyField or "
					"OneToOneField, got %s." %len(values)
				)

		return mngr.set(val)

	def __delete__(self, inst):
		return self.__set__(inst, None)

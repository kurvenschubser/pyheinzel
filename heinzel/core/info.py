# info.py
"""
Store information about a Model instance, to be used as cache key.
"""

from weakref import ref

from heinzel.core import signals


def get_inst_info(inst):
	try:
		return inst.__dict__["_inst_info"]
	except KeyError:
		InstanceInfo(inst)
	return inst._inst_info


def get_model_info(model):
	try:
		return model.__dict__["_model_info"]
	except KeyError:
		model._model_info = ModelInfo(model)
	return model._model_info


class ModelInfo(object):
	def __init__(self, model):
		self.model = model

		self.pkname = model.pk.name
		self.pkcol = model.pk.column_name

		self.field_to_col_names = dict((f.name, f.column_name) 
											for f in model.fields().values())
		self.field_to_col_names["pk"] = self.field_to_col_names[self.pkname]
		self.db_columns = self.field_to_col_names.values()


class InstanceInfo(object):
	def __init__(self, inst):
		self.model_info = get_model_info(type(inst))
		self.set_inst(inst)
		self._lazypkval = object()
		self._vars = {}
		self._meta = {
			# is this really needed?
			"was-reloaded": False,
			# Force synchronization of this info's model instance field
			# values. This is useful to set to True in a multi-process
			# setup, where otherwise inconsistent field values across 
			# processes will occur.
			"force-sync": True,
			# If False, this instance's model instance will not be 
			# kept in any Storage instance.
			"do-cache": True,
		}

	def __getitem__(self, name):
		name = self.model_info.field_to_col_names.get(name, name)
		return self._vars[name]

	def __setitem__(self, name, value):
		name = self.model_info.field_to_col_names.get(name, name)
		self._vars[name] = value

	def update(self, *dicts, **kw):
		nd = {}
		if dicts:
			for d in dicts:
				nd.update(d)
		if kw:
			nd.update(kw)
		for k in nd:
			self[k] = nd[k]

	def get(self, name, alternative=None):
		try:
			return self[name]
		except KeyError:
			return alternative

	def get_pk_as_key(self):
		return self.get("pk", self._lazypkval)

	def get_inst(self):
		return self._wref()

	def set_inst(self, inst):
		assert isinstance(inst, self.model_info.model)
		inst._inst_info = self
		self._wref = ref(inst, self._on_instance_delete)

	def _on_instance_delete(self, wref):
		pass


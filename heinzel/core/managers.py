from heinzel.core import signals
from heinzel.core.queries import QuerySet
from heinzel.core.exceptions import DoesNotExist, MultipleEntriesError




class Manager(object):
	
	def __init__(self):
		self.model = None
	
	def __str__(self):
		return str(self.get_query_set())

	def __get__(self, instance, owner):
		if instance is not None:
			raise AttributeError(
				("A 'Manager' instance may not be used on instances of a "
				" 'Model' class. Invoke it from the class instead.")
			)
		return self

	def __iter__(self):
		return (obj for obj in self.get_query_set().eval())

	def contribute_to_class(self, model, name):
		self.model = model
		setattr(model, name, self)

	def get_query_set(self):
		return QuerySet(model=self.model)

	def filter(self, *qobjs, **filters):
		return self.get_query_set().filter(*qobjs, **filters)

	def exclude(self, *qobjs, **filters):
		return self.get_query_set().exclude(*qobjs, **filters)
	
	def all(self):
		return self.get_query_set()

	def get(self, *qobjs, **filters):
		objs = list(self.filter(*qobjs, **filters).eval())

		if not objs:
			raise DoesNotExist(self.model, filters)
		if len(objs) > 1:
			raise MultipleEntriesError(self.model, filters)

		return objs[0]

	def create(self, **kwargs):
		return self.model(**kwargs).save()

	def get_or_create(self, **kwargs):		
		try:
			return self.get(**kwargs), False
		except DoesNotExist:
			return self.create(**kwargs)

	def rollback(self):
		signals.fire("cache-rollback")

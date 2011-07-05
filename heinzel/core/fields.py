import os
import re
from datetime import datetime
import socket

from heinzel import settings
from heinzel.core.descriptors import DeferredLoading
from heinzel.core.exceptions import ValidationError
from heinzel.core import utils


__all__ = ["Field", "TextField", "BufferField", "IntegerField", "BooleanField",
	"FloatField", "DatetimeField", "LongField", "RegexField", "ISBNField", 
	"IPv6Field", "HostNameField", "FilePathField", "ImagePathField", 
	"RelationField", "ForeignKeyField", "ManyToManyField", "OneToOneField"]


class Field(object):
	"""Base class for the validation of input values of a Model instance.
	Ensures that input to a Model's attribute passes validation defined in the
	Field's `to_python` method.
	"""

	_typ = None

	def __init__(self, initial=None, primary_key=False, auto_increment=False, 
				null=True, default=None, unique=False, max_length=None, 
				column_name="", db_default=None):

		self.initial = initial
		self.primary_key = primary_key
		self.auto_increment = auto_increment
		self.null = null
		self.default = default
		self.unique = unique
		self.max_length = max_length
		self.column_name = column_name

		# To be set on Model construction, will be overwritten with the 
		# identifier's name for the Field in the Model definition.
		self.name = ""

		if self.primary_key:
			#self.unique = True
			pass

		if self.null and self.default:
			pass

	def __str__(self):
		return "<%s>" %self.__class__.__name__

	def to_python(self, value):
		"""Subclasses should override this method."""

		return value

	def __new__(cls, *args, **kwargs):
		return super(Field, cls).__new__(cls)
		
	@property
	def attrs(self):
		return self.__dict__
	
	def get_type(self):
		return self._typ


class TextField(Field):
	_typ = unicode
	
	def to_python(self, value):
		value = super(TextField, self).to_python(value)
		if value is None:
			return value

		if self.max_length and self.max_length < len(value):
			raise ValidationError(("Value '%s' for field %s is too "
				" long: max_length==%s, len(value)==%s") \
					% (value, self, self.max_length, len(value)))

		try:
			return self.get_type()(value)
		except UnicodeDecodeError, e:
			raise
		except:
			raise


class BufferField(TextField):
	_typ = buffer

	def to_python(self, value):
		value = super(BufferField, self).to_python(value)
		if value is None:
			return value
		
		if self.max_length and self.max_length < len(value):
			raise ValidationError(("Value '%s' for field %s is too "
				" long: max_length==%s, len(value)==%s") \
					% (value, self, self.max_length, len(value)))
		return self.get_type()(value)



class IntegerField(Field):
	_typ = int
	
	def to_python(self, value):
		value = super(IntegerField, self).to_python(value)
		if value is None:
			return value

		try:
			return self.get_type()(value)
		except ValueError:
			raise TypeError("%s needs input that can be converted to '%s'." \
				%(self, self.get_type()))


class BooleanField(IntegerField):
	_typ = bool


class FloatField(Field):
	_typ = float
	
	def to_python(self, value):
		value = super(FloatField, self).to_python(value)
		if value is None:
			return value

		try:
			return self.get_type()(value)
		except ValueError:
			raise TypeError("%s needs input that can be converted to 'float'." %self)


class DatetimeField(Field):
	_typ = datetime

	def to_python(self, value):
		"""The DEFAULT constraint specifies a default value to use when doing 
		an INSERT. The value may be NULL, a string constant, a number, or a 
		constant expression enclosed in parentheses. The default value may also
		be one of the special case-independant keywords CURRENT_TIME, 
		CURRENT_DATE or CURRENT_TIMESTAMP. If the value is NULL, a string
		constant or number, it is literally inserted into the column whenever
		an INSERT statement that does not specify a value for the column is
		executed. If the value is CURRENT_TIME, CURRENT_DATE or 
		CURRENT_TIMESTAMP, then the current UTC date and/or time is inserted
		into the columns. For CURRENT_TIME, the format is HH:MM:SS. For 
		CURRENT_DATE, YYYY-MM-DD. The format for CURRENT_TIMESTAMP is
		"YYYY-MM-DD HH:MM:SS"."""
		# self.auto_now_date self.auto_now_time, self.auto_now_datetime = self.auto_now
		# django: auto_now: bei jedem speichern wird die zeit angepasst.
		# auto_now_add: nur beim ersten speichern wird zeit gesetzt.

		value = super(DatetimeField, self).to_python(value)
		if value is None:
			return value

		if not isinstance(value, self.get_type()):
			raise ValidationError(
				("Need an instance of '%s', got value '%s' which is of type "
					"'%s'.") %(self.get_type(), value, type(value))
			)
		if not value.tzinfo:
			value = utils.datetime_localize(value)
		return value


class LongField(Field):
	_typ = long


class RegexField(TextField):
	def __init__(self, regex=None, *args, **kwargs):
		"""*regex* a regular expression object."""

		super(RegexField, self).__init__(*args, **kwargs)
		if regex is not None:
			self.regex = regex

	def to_python(self, data):
		data = super(RegexField, self).to_python(data)
		match = self.regex.search(data)
		if match is None:
			raise ValidationError(
				"Input does not conform to regular expression '%s': '%s'." \
					%(self.regex.pattern, data)
			)
		return data


class ISBNField(RegexField):
	# Additional logic is required for checking the validity of the last bit
	# See http://www.isbn.org/standards/home/isbn/international/html/usm4.htm
	regex = re.compile(
		"^ISBN\s(?=[-0-9xX ]{13}$)(?:[0-9]+[- ]){3}[0-9]*[xX0-9]$"
	)


class IPv6Field(Field):
	_typ = unicode
	def to_python(self, value):	
		if value is None or value == "":
			return value
		try:
			socket.inet_pton(socket.AF_INET6, value)
		except socket.error:
			raise ValidationError("Not a valid IPv6 address: '%s'." % value)
		return self.get_type()(value)


class HostNameField(RegexField):
	regex = re.compile("""
		^(([a-zA-Z]|[a-zA-Z][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*
		([A-Za-z]|[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9])$
		""",
		re.VERBOSE
	)


class FilePathField(TextField):
	def __init__(self, overwrite=True, basepath=os.getcwd(), *args, **kwargs):
		super(type(self), self).__init__(*args, **kwargs)

		self.overwrite = overwrite
		self.basepath = basepath
		self.max_length = 255

		def to_python(self, value):
			value = super(type(self), self).to_python(value)
			path = os.path.join(self.basepath, value)
			if os.path.exists(path) and not self.overwrite:
				raise ValidationError(path, self, "Path already exists. Set "\
										"FileField.overwrite=True to ignore.")
			return path


class ImagePathField(FilePathField):
	pass


class RelationField(Field):
	"""A reference from one model to another. The other model goes into
	`related_model`."""

	related_model = DeferredLoading("_related_model")

	def __init__(self, related_model, related_name="", on_delete="cascade",
					null=False):
		Field.__init__(self, null=null)
		self.related_model = related_model
		self.related_name = related_name
		self.on_delete = on_delete

	def set_related_name(self, model):
		self.related_name = self.related_name\
							or settings.RELATED_NAME_PREFIX +\
								model.__name__.lower() +\
								settings.RELATED_NAME_POSTFIX

	def __str__(self):
		return "<%s>" %self.__class__.__name__


class ForeignKeyField(RelationField):	
	def __init__(self, related_model, related_name="", on_delete="cascade",
					null=True, column_name=""):
		RelationField.__init__(self, related_model, related_name, on_delete, null)
		self.column_name = column_name


class ManyToManyField(RelationField):
	def __init__(self, related_model, related_name="", through=None,
						on_delete="cascade", null=True):
		"""
		on_delete and null do not work/are not implemented for m2m
		relationships yet.
		TODO: check if they should work and implement them.
		"""
		RelationField.__init__(self, related_model, related_name)
		self.through = through


class OneToOneField(RelationField):
	def __init__(self, related_model, related_name="", through=None,
						on_delete="cascade", null=True):
		"""
		on_delete and null do not work/are not implemented for m2m
		relationships yet.
		TODO: check if they should work and implement them.
		"""
		
		RelationField.__init__(self, related_model, related_name)
		self.through = through

	def set_related_name(self, model):
		self.related_name = self.related_name or model.__name__.lower()

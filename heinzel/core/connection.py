try:
	import sqlite3 as sqlite
except ImportError:
	from pysqlite2 import dbapi2 as sqlite

import os
from datetime import datetime

from heinzel import settings

from heinzel.core import utils
from heinzel.core.exceptions import DatabaseError, \
					DatabaseSanityError, SQLSyntaxError


sqlite.register_adapter(datetime, utils.adapt_datetime_to_string)
sqlite.register_converter("DATETIME", utils.convert_string_to_datetime)


class Table(object):
	def __init__(self, name, columns):
		self.name = name
		self.columns = columns

	def __str__(self):
		return ("<Table object at %i: name=%s, columns=%s>" 
				% (id(self), self.name, self.columns))

	def __iter__(self):
		return (c for c in self.columns)

	def get_index(self, column):
		"""Takes a string and returns the index of the column with that
		string as name.
		"""

		return self.columns.index(column)


class Database(object):
	def __init__(self):
		self.dbname = settings.DBNAME
		self.conn = None
		self.cursor = None
		self.table_registry = {}
		self.verbose = False
		self.connect(commit=False)
		

	def __repr__(self):
		return "<%s instance at %i: dbname=%s>" % (self.__class__.__name__,
													id(self), self.dbname)

	def connect(self, dbname=None, commit=True):
		if self.conn:
			if commit:
				self.commit()
			self.close()

		if dbname is not None:
			self.dbname = dbname

		self.conn = sqlite.connect(self.dbname, 
			detect_types=sqlite.PARSE_DECLTYPES)

		self.cursor = self.conn.cursor()
		self.register_tables()

	def execute(self, stmt, values=()):
		try:
			return self.cursor.execute(stmt, values)
			
			# if stmt[:6].lower() in ("select",):
				# return self.cursor.execute(stmt, values)
			# elif stmt[:6].lower() in ("insert", "delete", "update", "create"):
				# c = self.cursor.execute(stmt, values)
				# self.commit()
				# self.close()
				# return c

		except sqlite.IntegrityError, e:
			msg = e.args[0].lower()
			if "foreign key constraint" in msg:
				raise DatabaseSanityError("A trigger prevents operation on "
					"the table. If a field is set to null=False, an "
					"insert/update on this database column must never "
					"be null. Set null=True on the model and re-create "
					"or alter the table so that the column can be "
					"'null' to mitigate this. " + str(e))

			if "column" in msg and "is not unique" in msg:
				raise DatabaseSanityError("Can't save '%s' "
					"because of 'unique' constraint: %r, message='%s'."
					% (self, type(e), msg)
				)
		except sqlite.OperationalError, e:
			msg = e.args[0].lower()
			if "syntax error" in msg:
				raise SQLSyntaxError((stmt, values))
			if "database is locked" in msg:
				raise DatabaseError(msg + ". " + str((stmt, values)))
			raise

		except Exception, e:
			# print 'Database.execute:', e
			# print stmt, ", ", values
			#raw_input("db.execute")
			#print self.cursor.connection.total_changes

			raise

		finally:
			if self.verbose:
				print os.getpid(), os.getppid(), os.getuid()
				print stmt, values
			

	def executemany(self, stmt, values=()):
		try:
			# print stmt, values
			return self.cursor.executemany(stmt, values)
		except Exception, e:
			print 'Error', e
			print stmt, values
			#raw_input("db.executemany")
			print self.cursor.connection.total_changes
			raise

	def commit(self):
		self.conn.commit()

	def close(self):
		self.cursor = None
		self.conn.close()
		self.conn = None

	def raw_sql(self, stmt, values=[]):
		if isinstance(stmt, basestring):
			return self.cursor.execute(stmt, values)

	def register_tables(self):
		for t in self.get_db_tablenames():
			self.table_registry[t] = Table(t, self.get_db_columns_for_table(t))

	def get_db_tablenames(self):
		self.execute("SELECT name FROM sqlite_master WHERE type='table'")
		return[i[0] for i in self.cursor.fetchall()]

	def get_db_columns_for_table(self, table):
		self.execute("SELECT * FROM %s" % table)
		return [i[0] for i in self.cursor.description]

	def table_exists(self, model):
		return self.execute(
			"select * from sqlite_master where (type='table' and name='%s')" % \
			model.tablename()
		).fetchone()

	def validate_table(self, model):
		"""Todo: validate relations too."""

		column_names = model.get_column_names()

		cursor_desc = self.get_db_columns_for_table(model.tablename())

		for colname in cursor_desc:
			if not colname in column_names:
				raise DatabaseSanityError(
					"Table `%s` is invalid: column `%s` not in "
					"%s.get_column_names(): `%s`!"
					%(model.tablename(), colname, model, column_names)
				)

		for colname in column_names:	
			if not colname in cursor_desc:
				raise DatabaseSanityError("Table `%s` is invalid: column_name `%s` on model `%s` not in database columns: `%s`!" \
						%(model.tablename(), colname, model, cursor_desc))

		print "table `%s` for model `%s` validates." %(model.tablename(), model)


db = Database()


def connect(dbname=None):
	if dbname or db.conn is None:
		db.connect(dbname)
	return db

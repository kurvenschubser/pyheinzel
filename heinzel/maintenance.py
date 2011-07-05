from heinzel.core import connection
from heinzel.core import exceptions
from heinzel.core import relations
from heinzel.core.sql.ddl import (TableCreation,
	create_or_alter_relation_table, _sql_stmt__create_link_table)
	
from heinzel.core.sql.triggers import create_triggers

from heinzel import settings


def syncdb(models, dbname, force_create_table=True):
	"""This will create all necessary tables for the *models* in the database
	*dbname* and validate those tables.
	"""

	db = connection.connect(dbname)

	for m in models:
		if not db.table_exists(m):
			if force_create_table:
				sql = TableCreation(m).as_sql()
				
				try:
					msg = ("In %s: created table '%s' with statement '%s'." 
						% (db.dbname, m.tablename(), sql))
					db.execute(*sql)

				except Exception, e:
					msg = e
					raise
				finally:
					#logging.log(msg)
					print msg
			else:
				msg = ("Need to create table `%s`, but `force_create_table` is "
						"'False'" %m.tablename())
				#logging.log(msg)
				raise Exception(msg)
		else:
			print m.tablename() + ' already exists.'

	# Create linker tables for one-to-one and many-to-many relations and 
	# alter tables for one-to-many (foreign key) relations.

	# Filter out those relations that are unused by the registered models.
	to_be_installed = set()
	for rel in relations.registry:
		for m in models:
			if rel in m._relations:
				to_be_installed.add(rel)
				break

	for rel in to_be_installed:
		relsql = create_or_alter_relation_table(rel)
		try:
			msg = (
				"Created or altered table for relation '%s': %s."
				% (rel, relsql)
			)
			db.execute(relsql)

		except Exception, e:
			if "table" in str(e) and "already exists" in str(e):
				print e
			else:
				msg = (
					"Could not create or alter table for relation '%s': %s \n"
					"Exception message by DBMS: '%s'." %(rel, relsql, e)
				)
				raise exceptions.SQLSyntaxError(msg)
		finally:
			# logging.log(msg)
			print msg

	for rel in to_be_installed:
		trglist = create_triggers(rel)
		for trg in trglist:
			try:
				db.execute(trg)

				msg = "Created trigger for relation '%s': %s." % (rel, trg)
			except Exception, e:
				if "trigger" in str(e) and "already exists" in str(e):
					print e
				else:
					msg = ("Error on creating trigger for relation '%s': %s"
						%(rel, e))
					raise exceptions.SQLSyntaxError(msg)

	for m in models:
		db.validate_table(m)

	db.commit()
	db.close()
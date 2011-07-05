from heinzel.core import fields
from heinzel.core import constants
from heinzel.core.sql.ddl import link_table_name


def trigger_insert(ptable, rtable, keycol, nullable):
	#-- Foreign Key Preventing insert
	return """
		CREATE TRIGGER %s
		BEFORE INSERT ON [%s]
		FOR EACH ROW BEGIN
			SELECT RAISE(ROLLBACK, 'insert on table "%s" violates foreign key constraint "%s"')
			WHERE %s(SELECT id FROM %s WHERE id = NEW.%s_id) IS NULL;
		END
	""" %(	trigger_name("fki", ptable, rtable, keycol), ptable, ptable,
			trigger_name("fki", ptable, rtable, keycol),
			"NEW.%s_id IS NOT NULL AND " %keycol if nullable else "",
			rtable, keycol	)


def trigger_uniqueness(mode, ptable, rtable, pkeycol, lpkeycol, lrkeycol):
	'''Prevents inserts of exact equals into a M2M link table.'''
	trigger_name = "fkiuniq__" + link_table_name(mode, ptable, pkeycol, rtable)
	
	return """
			CREATE TRIGGER %s
			BEFORE INSERT ON %s
			FOR EACH ROW BEGIN
				SELECT RAISE(ROLLBACK, 'insert on table "%s" violates foreign key constraint "%s"')
				WHERE (SELECT id FROM %s WHERE %s_id = NEW.%s_id AND %s_id = NEW.%s_id) IS NOT NULL;
			END
		""" %(	trigger_name, link_table_name(mode, ptable, pkeycol, rtable),
				link_table_name(mode, ptable, pkeycol, rtable), trigger_name,
				link_table_name(mode, ptable, pkeycol, rtable), 
				lpkeycol,
				lpkeycol, 
				lrkeycol, 
				lrkeycol	)


def trigger_update(ptable, rtable, keycol, nullable):
	#-- Foreign key preventing update
	return """
		CREATE TRIGGER %s
		BEFORE UPDATE ON [%s]
		FOR EACH ROW BEGIN
			SELECT RAISE(ROLLBACK, 'insert on table "%s" violates foreign key constraint "%s"')
			WHERE %s(SELECT id FROM %s WHERE id = NEW.%s_id) IS NULL;
		END
	""" %(	trigger_name("fku", ptable, rtable, keycol), ptable, ptable, 
			trigger_name("fku", ptable, rtable, keycol),
			"NEW.%s_id IS NOT NULL AND " %keycol if nullable else "",
			rtable, keycol	)


def trigger_delete(ptable, rtable, keycol):
	#-- Foreign key constraint preventing delete
	return """
		CREATE TRIGGER %s
		BEFORE DELETE ON %s
		FOR EACH ROW BEGIN
			SELECT RAISE(ROLLBACK, 'delete on table "%s" violates foreign key constraint "%s"')
			WHERE (SELECT %s_id FROM %s WHERE %s_id = OLD.id) IS NOT NULL;
		END
	"""%(	trigger_name("fkd", ptable, rtable, keycol), rtable, rtable,
			trigger_name("fkd", ptable, rtable, keycol), keycol, ptable, 
			keycol	)

	
def trigger_delete_cascade(ptable, rtable, keycol):
	#-- Cascading Delete
	return """
		CREATE TRIGGER %s
		BEFORE DELETE ON %s
		FOR EACH ROW BEGIN
			DELETE FROM %s WHERE %s.%s_id = OLD.id;
		END
	"""%(	trigger_name("fkdc", ptable, rtable, keycol), rtable, ptable,
			ptable, keycol	)


def trigger_name(mode, ptable, rtable, keycol):
	# fki__cars__brand_id__brands__id
	return "%s__%s__%s_id__%s__id" % (	mode, ptable, keycol, rtable	)




def create_triggers(relation):
	"""
	A wrapper for TriggerGenFK and TriggerGenM2M.
	No triggers are required for one-to-one relations because they
	are already present in the linker table definition via the `UNIQUE`
	keyword. See `heinzel.core.sql.ddl._sql_stmt__create_link_table`.
	"""

	sql = []

	if relation.mode == constants.FK:
		sql.extend(
			TriggerGenFK(relation).create_triggers()
		)

	if relation.mode == constants.M2M:
		sql.extend(
			TriggerGenM2M(relation).create_triggers()
		)

	return sql

class TriggerGenFK(object):
	"""Here the triggers for enforcement of referential integrity are created."""
	def __init__(self, relation):
		self.relation = self.rel = relation

		self.nullable = self.rel.model.fields()[self.rel.identifier].null
		self.on_delete = self.rel.model.fields()[self.rel.identifier].on_delete

	def create_triggers(self):
		sql =  [
			trigger_insert(self.rel.model.tablename(),
				self.rel.related_model.tablename(),
				self.rel.identifier,
				self.nullable
			),
			trigger_update(self.rel.model.tablename(),
				self.rel.related_model.tablename(),
				self.rel.identifier,
				self.nullable
			)
		]
		
		if self.on_delete == "restrict":
			sql.append(trigger_delete(self.rel.model.tablename(),
								self.rel.related_model.tablename(),
								self.rel.identifier)
			)

		if self.on_delete == "cascade":
			sql.append(trigger_delete_cascade(self.rel.model.tablename(),
								self.rel.related_model.tablename(),
								self.rel.identifier)
			)

		return sql

class TriggerGenM2M(object):
	"""Here the triggers for enforcement of referential integrity are created."""
	def __init__(self, relation):
		self.relation = self.rel = relation

		self.link_table = link_table_name(constants.MODES[self.rel.mode],
							self.rel.model.tablename(), self.rel.identifier,
										self.rel.related_model.tablename())

		self.nullable = False	# nullable not allowed on many-related fields?

	def create_triggers(self):
		sql = [	trigger_insert(self.link_table, self.rel.model.tablename(),
					self.rel.reverse_identifier, self.nullable),
				trigger_insert(self.link_table, self.rel.related_model.tablename(),
					self.rel.identifier, self.nullable),
				trigger_uniqueness(constants.MODES[self.rel.mode], self.rel.model.tablename(),
					self.rel.related_model.tablename(), self.rel.identifier,
					self.rel.identifier,
					self.rel.reverse_identifier),
				trigger_update(self.link_table, self.rel.model.tablename(),
					self.rel.reverse_identifier, self.nullable),
				trigger_update(self.link_table, self.rel.related_model.tablename(),
					self.rel.identifier, self.nullable)	]

		# Since it would be kind of expensive, to search the whole db for any related
		# data, delete cascade is not implemented for M2M relations. Hence
		# the out-commenting... Only the 2 triggers for cascading delete on the linker
		# table will be generated.

		#if not self.pmodel.__dict__[self.rel.identifier].on_delete in ("restrict", "cascade"):
		#	raise Exception("Related field `%s` on model `%s` must have `on_delete` property set to either 'restrict' or 'cascade'."
		#						%(self.rel.identifier, self.pmodel))

		#if self.pmodel.__dict__[self.rel.identifier].on_delete == "restrict":
		#	l.append(trigger_delete(self.link_table, self.pmodel.tablename(),
		#								self.rel.identifier))
		#	l.append(trigger_delete(self.link_table, self.rel.related_model.tablename(),
		#								self.rel.reverse_identifier))

		#if self.pmodel.__dict__[self.rel.identifier].on_delete == "cascade":
		#	l.append(trigger_delete_cascade(self.link_table, self.pmodel.tablename(),
		#								self.rel.identifier))
		#	l.append(trigger_delete_cascade(self.link_table, self.rel.related_model.tablename(),
		#								self.rel.reverse_identifier))
		
		sql.append(trigger_delete_cascade(self.link_table, self.rel.model.tablename(),
										self.rel.reverse_identifier))
		sql.append(trigger_delete_cascade(self.link_table, self.rel.related_model.tablename(),
										self.rel.identifier))
		return sql

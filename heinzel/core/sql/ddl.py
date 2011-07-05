from datetime import datetime

from heinzel.core import connection
from heinzel.core import constants


type_map = {	None:		"null",
				str:		"TEXT",
				unicode: 	"TEXT",
				int: 		"INTEGER",
				long: 		"INTEGER",
				bool:		"BOOL",
				float: 		"REAL",
				buffer: 	"BLOB",
				datetime:	"DATETIME"	}


def link_table_name(mode, ptable, keycol, rtable):
	return "%s__%s__%s__%s" %(mode, ptable, keycol, rtable)


class TableCreation(object):
	def __init__(self, model):
		self.model = model

	def as_sql(self):

		sql = []
		for name, field in sorted(self.model.non_related().items()):
			if name == "pk":
				continue

			s1 = ["%(name)s %(type)s" %{"name": name, "type": type_map[field.get_type()]}]

			if field.max_length:
				s1.append("(" + unicode(field.max_length) + ")")
			if field.primary_key:
				s1.append("PRIMARY KEY")
			if field.unique:
				s1.append("UNIQUE")
			if field.auto_increment:
				s1.append("AUTOINCREMENT")
			if not field.null:
				s1.append("NOT NULL")
			else:
				if field.default:
					if isinstance(field.default, basestring):
						dflt = "'%s'" % field.default
					else:
						dflt = field.default
					s1.append("DEFAULT %s" % dflt)
			sql.append(" ".join(s1))

		return "CREATE TABLE %s (%s);" %(self.model.tablename(), ", ".join(sql)), ()


def create_or_alter_relation_table(relation):
	"""Here we create the sql for any linker tables or table columns to relate 
		the models."""

	if relation.mode == constants.FK:		
		# id fields are always of type int
		return (
			"ALTER TABLE %(table)s ADD %(name)s_id %(type)s" 
				% {"table": relation.model.tablename(),
					"name": relation.identifier,
					"type": type_map[int]}
		)

	else:
		# if rel.mode in (constants.M2M, constants.O2O)
		return _sql_stmt__create_link_table(relation)

def _sql_stmt__create_link_table(relation):
	'''Returns the sql for a linker table for many-to-many or one-to-one
	relationships between 2 models.
	'''

	return """
CREATE TABLE %s (
	id INTEGER PRIMARY KEY NOT NULL,
	%s_id INTEGER%s,
	%s_id INTEGER%s
)""" % (link_table_name(
			constants.MODES[relation.mode],
			relation.model.tablename(), 
			relation.identifier,
			relation.related_model.tablename()
			),
			relation.identifier,
			" UNIQUE" if relation.mode == constants.O2O else "",
			relation.reverse_identifier,
			" UNIQUE" if relation.mode == constants.O2O else ""	
		)

# -*- coding: utf-8 -*-

import sys
from copy import deepcopy
from hashlib import md5

from heinzel.core import fields
from heinzel.core import connection
from heinzel.core import exceptions
from heinzel.core import utils

from heinzel.core.sql.ddl import link_table_name, type_map
from heinzel.core.constants import *



def __one_token(escaped_list):
	return ":" + escaped_list[0][0]


def __unpack_as_many(values):
	return values


def __concat(values):
	b = []
	for v in values:
		val = unicode(v)
		if isinstance(v, (int, long, float)):
			b.append(val)
		else:
			b.append("'%s'" % val)
	return ", ".join(b)


# {filtername: (sql_opstr, placeholder_fn, unpack_fn, to_sql_fn)}
FILTERS = {
	# Apparently, Sqlite doesn't do case-insensitive matching on Unicode,
	# only on Ascii.
	"startswith": (
		u"LIKE %s",
		__one_token,
		__unpack_as_many,
		lambda val: val + u"%"
	),
	"endswith": (
		u"LIKE %s",
		__one_token,
		__unpack_as_many,
		lambda val: u"%" + val
	),
	"contains": (
		u"LIKE %s",
		__one_token,
		__unpack_as_many,
		lambda val: u"%" + val + u"%"
	),
	"gt": (
		u"> %s",
		__one_token,
		__unpack_as_many,
		None
	),
	"gte": (
		u">= %s",
		__one_token,
		__unpack_as_many,
		None
	),
	"lt": (
		u"< %s",
		__one_token,
		__unpack_as_many,
		None
	),
	"lte": (
		u"<= %s",
		__one_token,
		__unpack_as_many,
		None
	),
	"exact": (
		u"= %s",
		__one_token,
		__unpack_as_many,
		None
	),
	"in": (
		u"IN (%s)",
		lambda list_: ", ".join([":%s" % tup[0] for tup in list_]),
		__unpack_as_many,
		None
	),
	"between": (
		u"BETWEEN %s AND %s",
		lambda list_: (":" + list_[0][0], ":" + list_[1][0]),
		__unpack_as_many,
		None
	),
	#"regex": ("REGEX", lambda x: "(" + x + ")),
	#"year":,
	#"month":,
	#"day":,
}

# Aliases for filters
FILTERS["beginswith"] = FILTERS["startswith"]



def filter_factory(filtername):
	return Filter(filtername, *FILTERS[filtername])


class Filter(object):
	def __init__(self, name, opstr, placeholder_fn, unpack_fn, to_sql_fn):
		self.name = name
		self._opstr = opstr
		self._placeholder_fn = placeholder_fn
		self._unpack_fn = unpack_fn
		self._to_sql_fn = to_sql_fn

	def __deepcopy__(self, memo):
		return Filter(
			self.name,
			self._opstr,
			self._placeholder_fn,
			self._unpack_fn,
			self._to_sql_fn
		)

	def __eq__(self, other):
		return type(self) == type(other) and self.name == other.name

	def __ne__(self, other):
		return not self.__eq__(other)

	def render(self, table, column):
		return self._opstr \
				% self._placeholder_fn(self.get_values(table, column))

	def get_values(self, table, column):
		return [(self.escape_token(table, column, v), v) for v \
													in self._values]

	def set_values(self, values):
		self._values = []
		for v in self._unpack_fn(values):
			self._values.append(self.to_sql(v))

	def to_sql(self, value):
		"""
		Return a value for the dictionary, that is going to be passed to the
		cursor.execute method as values to be escaped by the database adapter.
		I.e.: cursor.execute("select * from foo where name LIKE :NAME", 
		{"NAME": value})
		"""

		if self._to_sql_fn is None:
			return value
		return self._to_sql_fn(value)

	def escape_token(self, table, column, value):
		return "%s__%s__%s__%i" % (table, column, self.name, id(value))


class BaseSelector(object):
	def __init__(self, field, fn="", alias=None):
		self.field = field
		self.function = self.fn = fn
		self.alias = alias
		if not self.alias:
			self.alias = self.field

Select = BaseSelector

class _Aggregator(BaseSelector):
	def __init__(self, field):
		BaseSelector.__init__(self, field, self.__class__.__name__, 
								self.__class__.__name__ + "__" + field)

def _aggregator_factory(name):
	return type(name, (_Aggregator,), {})

Max = _aggregator_factory("Max")
Min = _aggregator_factory("Min")
Count = _aggregator_factory("Count")
Avg = _aggregator_factory("Avg")
Sum = _aggregator_factory("Sum")


#! FIX: in __and__, __or__, __invert__ return clones
class Q(utils.Node):

	def __init__(self, **filters):
		if not filters:
			raise Exception("Need filter arguments for 'Q' object.")

		for k, v in filters.items():
			if getattr(v, "pk", None) is not None:
				raise NotImplementedError("Model instances as filter values are not yet supported.")
			

		utils.Node.__init__(self, filters.items(), self.AND, False)

	def __iter__(self):
		return (ch for ch in self.children)

	def __and__(self, other):
		self.append(other, self.AND)
		return self

	def __or__(self, other):
		self.append(other, self.OR)
		return self

	def __invert__(self):
		self.negate = not self.negate
		return self


class Parser(object):
	#? implement support for aliased fields parsing.

	def __init__(self, query):
		self.model = query.model
		self.query = query

	def lex(self, tokenstring):
		tokens = self.tokenize(tokenstring)

		if tokens[-1] in FILTERS:
			filtername = tokens.pop()
		else:
			filtername = "exact"

		filter = filter_factory(filtername)

		return tokens, filter

	def tokenize(self, tokens):
		return tokens.split("__")

	def parse_filters(self, negate, qobjs, filters):		
		#combine Q objects and filters
		if filters:
			qobjs += (Q(**filters),)

		if negate:
			for q in qobjs:
				~q

		if qobjs:
			qobj = qobjs[0]

		for q in qobjs[1:]:
			qobj & q

		return self._parse_q(qobj)

	def parse_selectors(self, args, kwargs):
		sel_leaves = []

		for selobj in self._combine_selectors(args, kwargs):			
			fields = self.tokenize(selobj.field)

			joins, (db_table, db_column) = self._traverse(fields)

			if db_table is db_column is None:
				raise Exception(
					"Error parsing fields '%s' on %s." % (fields, self.model)
				)

			for join in joins:
				if not join in self.query.joins_order:
					self.query.joins_order.append(join)

			if joins:
				# the crucial last join of joins might have been added
				# before this iteration of _parse_q and might already have
				# got a 'right_side_alias' different from this iteration's
				# joins' last join: Get the right join and take it's 
				# get_right_side_alias() as db_table.
				join = self.query.joins_order[
					self.query.joins_order.index(joins[-1])
				]

			elif self.query.joins_order:
				# no joins were encountered, but there might be previously
				# encountered ones.				
				join = self.query.joins_order[0]

			else:
				# there are no joins whatsoever, the value returned from 
				# :meth:‘Parser._traverse‘, *db_table*, is correct.
				join = None

			sel_leaves.append(
				SelectionLeaf(join, db_table, db_column, selobj.alias, selobj.fn)
			)

		return sel_leaves

	def _parse_q(self, qobject):
		"""
		Extract lookups from qobject to self.query._nodes, copy logical 
		structure of qobject to self.where_node.
		"""

		# copy logical structure of qobject to self.where_node.
		node = utils.Node(connector=qobject.connector, negate=qobject.negate)

		for leaf in qobject.get_leaves():
			k, v = leaf

			fields, filter = self.lex(k)

			joins, (db_table, db_column) = self._traverse(fields)

			if db_table is db_column is None:
				# this might set 'db_table' to the empty string
				(db_table, db_column) = self._filter_annotations(fields)

			for join in joins:
				if not join in self.query.joins_order:
					self.query.joins_order.append(join)

			if not db_table == "":
				# this is not an annotation
				if joins:
					# the crucial last join of joins might have been added
					# before this iteration of _parse_q and might already have
					# got a 'right_side_alias' different from this iteration's
					# joins' last join: Get the correct join to put it into
					# the WhereLeaf.
					join = self.query.joins_order[
						self.query.joins_order.index(joins[-1])
					]
				elif self.query.joins_order:
					join = self.query.joins_order[0]
				else:
					join = None
			else:
				join = None

			node.children.append(WhereLeaf(join, db_table, db_column, filter, v))

		for branch in qobject.get_branches():
			node.children.append(self._parse_q(branch))

		return node

	def _traverse(self, tokens):
		joins = []

		model = self.model
		for t in tokens:
			relation = model._relations.get_relation_by_identity(model, t)
			if relation:
				joins.append(Join(relation, t))

				if relation.is_reverse_by_model(model):
					model = relation.model
				else:
					model = relation.related_model
			else:
				attr = model.fields().get(t)

				if attr is None:
					attr = model.get_field_by_column_name(t)

				# Since this attribute is not a relation, it suffices to test
				# if it is a field.
				if attr in model.fields().values():
					db_table = model.tablename()
					db_column = attr.column_name
				else:
					# Maybe it's not a real field, but an annotation, set to
					# None to signify further processing is required.
					db_table = db_column = None

		# If there are only relations in the querystring, append a query to
		# look for 'pk' field on the last model.
		if len(tokens) == len(joins):
			db_table = model.tablename()
			db_column = model.pk.column_name

		return tuple(joins), (db_table, db_column)

	def _combine_selectors(self, args, kwargs):
		queue = []
		for selobj in args:
			queue.append(selobj)

		for alias, selobj in kwargs.items():
			selobj.alias = alias
			queue.append(selobj)

		return queue

	def _filter_annotations(self, fields):
		"""Looks for aliased columns. When control flow reaches this method,
		that means a field could not be found on the model. So here we look
		for any annotations."""

		raise NotImplementedError

		if len(fields) != 1:
			raise Exception("Expected 1 field, got %i: %s" %(len(fields), fields))

		for al in query.annotation_node:
			if al.alias == fields[0]:
				return ("", fields[0])

		raise Exception(
			"Error parsing fields '%s' on %s." % (fields, self.model)
		)


class BaseQuery(object):
	def __init__(self, model, db=None):
		self.model = model
		self.db_table = model.tablename()
		self.db = db or connection.connect()
		self.db_columns = self.db.table_registry[self.db_table].columns

	def execute(self):
		return self.db.execute(*self.as_sql())

	def commit(self):
		return self.db.commit()

	def as_sql(self):
		return self.render(), self.get_values()


class SelectQuery(BaseQuery):
	def __init__(self, model, db=None, parser_class=Parser):
		BaseQuery.__init__(self, model, db)

		self.joins_order = []

		self.parser_class = parser_class
		self.parser = parser_class(self)

		self.selection_node = utils.Node()
		self.annotation_node = utils.Node()
		self.where_node = utils.Node()
		self.orderby_node = utils.Node()
		self.limit_node = utils.Node()
		
		self._distinct = False

	def __str__(self):
		return (
			"<SelectQuery instance at %i: query='%s', values=%r>"
			% (id(self), self.render(), self.get_values())
		)

	def __deepcopy__(self, memo):
		clone = SelectQuery(self.model, self.db, self.parser_class)
	
		clone.joins_order = deepcopy(self.joins_order)

		clone.selection_node = deepcopy(self.selection_node, memo)
		clone.annotation_node = deepcopy(self.annotation_node, memo)
		clone.where_node = deepcopy(self.where_node, memo)
		clone.orderby_node = deepcopy(self.orderby_node, memo)
		clone.limit_node = deepcopy(self.limit_node, memo)
		clone._distinct = deepcopy(self._distinct, memo)

		return clone

	#? FIX: hashing the output of self.render() might not be the
	# best solution, since it contains info irrelevant to the result, e.g.
	# ordering.
	def __hash__(self):
		return int(md5(self.render()).hexdigest(), 16)

	def __eq__(self, other):
		return self.__hash__() == other.__hash__()

	def __ne__(self, other):
		return not self.__eq__(other)

	def orderby(self, token=None):
		if token is None:
			self.orderby_node.clear()
		else:
			obl = OrderByLeaf(self.model, token)
			if obl in self.orderby_node:
				self.orderby_node.children[
					self.orderby_node.children.index(obl)
				].toggle()
			else:
				self.orderby_node.append(obl)

	def limit(self, by=None, offset=None):
		self.limit_node.clear()
		leaf = LimitLeaf(by, offset)
		self.limit_node.append(leaf)

	def render(self):
		"""Recursively render the nested *self.where_node* structure."""

		sql = ["SELECT"]

		if self._distinct:
			sql.append("DISTINCT")

		has_order_nodes = bool(self.orderby_node)
		if not has_order_nodes:
			self.orderby("pk")

		self.update_nodes()

		sql.append(", ".join([n.render() for n in self.selection_node] +
								[n.render() for n in self.annotation_node]))

		# from part
		sql.append("FROM")
		
		for j in self.joins_order:
			sql.append(j.render())

		if not self.joins_order:
			sql.append(self.model.tablename())

		if self.where_node:
			sql.append("WHERE")
			sql.append(self.where_node.render())

		sql.append("ORDER BY")
		sql.append(", ".join([n.render() for n in self.orderby_node]))
		
		# there was no user specified ordering, so remove the 'pk' ordering
		# added above
		if not has_order_nodes:
			self.orderby_node.clear()

		if self.limit_node:
			sql.append("".join([n.render() for n in self.limit_node]))

		return u" ".join(sql)

	def get_values(self):
		"""Returns a dict of all WhereLeaf values to be passed to the database
		adapter for proper escaping."""

		d = {}
		for wl in utils.recurse(self.where_node):
			d.update(wl.get_values())
		return d

	def set_default_selectors(self):
		"""
		In case there were no :class:‘SelectionLeaf‘'s defined (through 
		:meth:‘~SelectQuery._aggregate‘ or :meth:‘~SelectQuery_annotate‘),
		set a :class:‘SelectionLeaf‘ for all fields of *self.model*.
		This is the common use case and corresponds	to a
		'select * from model.tablename()'.
		"""

		sel_leaves = self.parser.parse_selectors(
					map(Select, self.db_columns), {})

		self.selection_node.extend(sel_leaves)

	def get_selection_aliases(self):
		aliases = ([n.alias for n in self.selection_node] +
					[n.alias for n in self.annotation_node])
		if not aliases:
			self.set_default_selectors()
			aliases = ([n.alias for n in self.selection_node] +
						[n.alias for n in self.annotation_node])
		return aliases

	def update_nodes(self):
		"""
		Update any :class:‘SelectionLeaf‘'s *join* with the first join of
		*self.joins_order* if it doesn't already have a join.
		"""

		if not self.selection_node:
			self.set_default_selectors()

		if not self.joins_order:
			return

		for leaf in self.selection_node:
			if not leaf.join:
				leaf.join = self.joins_order[0]

		for leaf in self.annotation_node:
			if not leaf.join:
				leaf.join = self.joins_order[0]

		for leaf in utils.recurse(self.where_node):
			if not leaf.join and not leaf.db_table == "":
				leaf.join = self.joins_order[-1]

		orderby_table = self.joins_order[0].get_left_side_alias()
		for obl in self.orderby_node:
			obl.db_table = orderby_table

	def _filter(self, negate, qobjs, filters):
		self.where_node.append(self.parser.parse_filters(negate, qobjs,
																filters))

	def _aggregate(self, args, kwargs):
		self.selection_node.clear()
		sel_node = self.parser.parse_selectors(args, kwargs)
		self.selection_node.extend(sel_node)

	def _annotate(self, args, kwargs):
		sel_node = self.parser.parse_selectors(args, kwargs)
		self.annotation_node.extend(sel_node)


class InsertQuery(BaseQuery):
	"""Generates the SQL for persisting a model instance."""

	def __init__(self, inst, db=None):
		BaseQuery.__init__(self, type(inst), db)

		self.values = dict(
			[(col, inst._inst_info.get(col)) for col in self.db_columns]
		)

	def render(self):
		vals = [":" + col for col in self.db_columns]
		# vals = [":" + col for col in self.db_columns]
		return "INSERT INTO %s VALUES (%s)" %(self.db_table, ", ".join(vals))

	def as_sql(self):
		return self.render(), self.values


class DeleteQuery(BaseQuery):
	def __init__(self, model, where, db=None):
		BaseQuery.__init__(self, model, db)
		self.where = where

	def render(self):
		sql = ["DELETE FROM", self.db_table]
		if self.where:
			sql.append("WHERE %s" % " AND ".join(k + "=:" + k for k in self.where))
		return " ".join(sql)

	def as_sql(self):
		return self.render(), self.where


class UpdateQuery(BaseQuery):
	def __init__(self, inst, db=None):
		BaseQuery.__init__(self, type(inst), db)

		self.inst = inst
		self.values = inst.get_column_names_values()

	def render(self):
		sql = ["UPDATE", self.inst.tablename(), "SET"]
		sql.append(", ".join([k + "=:" + k for k in self.get_values()]))

		pk = self.inst.fields()["pk"].column_name
		sql.append("WHERE %s=:%s" %(pk, pk))
		return " ".join(sql)

	def get_values(self):
		return self.values


class ConditionalUpdateQuery(object):
	def __init__(self, inst):
		self.inst = inst
		self.uniques = inst.get_unique_fields()
		self.non_uniques = inst.get_non_unique_fields()

	def render(self):
		sql = ["UPDATE %s" % self.inst.tablename()]
		sql.append("SET %s" % ", ".join([v.column_name + "=:" + v.column_name for v in self.non_uniques.values()]))
		sql.append("WHERE %s" % " AND ".join([v.column_name + "=:" + v.column_name for v in self.uniques.values()]))
		return " ".join(sql)

	def as_sql(self):
		return self.render(), self.inst.get_column_names_values()


class LinkerTableInsertQuery(object):
	"""Generates the SQL to connect items in a linker table.
		This is used in the case of many-to-many and one-to-one
		relations.
		"""

	def __init__(self, relation, master, identifier, slaves, db=None):
		self.relation = relation

		self.master = master
		self.identifier = identifier
		
		assert (self.relation.has_identity(type(self.master), self.identifier))
		
		self.slaves = slaves

		self.db = db or connection.connect()

		self.table = link_table_name(
			MODES[self.relation.mode], self.relation.model.tablename(),
			self.relation.identifier, self.relation.related_model.tablename()
		)

		self.db_columns = self.db.table_registry[self.table].columns

	def execute(self):
		self.db.executemany(*self.as_sql())

	def commit(self):
		self.db.commit()

	def as_sql(self):	
		return self.render(), self.get_values()

	def render(self):	
		cols = ["null" if c.lower() == "id" else ":" + c for c in self.db_columns]
		return "INSERT INTO %s VALUES (%s)" %(self.table, ", ".join(cols))

	def get_values(self):
		"""Returns a list of dicts with the ids of the instances that are to
		be linked in self.table"""

		# if self.relation.is_reverse_by_identifier(self.identifier):
			# ident = self.identifier
			# rev_ident = self.relation._get_other_identifier(self.identifier)
		# else:
			# ident = self.relation._get_other_identifier(self.identifier)
			# rev_ident = self.identifier

		ident = self.identifier
		rev_ident = self.relation._get_other_identifier(self.identifier)

		ident += "_id"
		rev_ident += "_id"

		mstr_id = self.master.id
		return [dict(((ident, obj.id), (rev_ident, mstr_id))) for obj in self.slaves]


class LinkerTableDeleteQuery(object):
	def __init__(self, relation, master, identifier, slaves, db=None):
		self.relation = relation
		self.master = master
		self.identifier = identifier

		# slaves is a list of instances, whose relation to self.master will be
		# deleted from the linker table. If slaves is empty, all relations 
		# that self.master has to other instances in this linker table, will be 
		# deleted.
		self.slaves = slaves

		self.db = db or connection.connect()

		self.table = link_table_name(MODES[self.relation.mode],
			self.relation.model.tablename(), self.relation.identifier,
			self.relation.related_model.tablename()
		)

	def execute(self):
		self.db.execute(*self.as_sql())

	def commit(self):
		self.db.commit()

	def as_sql(self):
		return self.render(), {}

	def render(self):
		d = self.get_values()

		cols = [c + " IN (%s" %", ".join(map(str, d[c])) + ")" for c in d.keys()]
		return "DELETE FROM %s WHERE %s;" %(self.table, " AND ".join(cols))

	def get_values(self):
		# if self.relation.is_reverse_by_identifier(self.identifier):
			# ident = self.identifier
			# rev_ident = self.relation._get_other_identifier(self.identifier)
		# else:
			# ident = self.relation._get_other_identifier(self.identifier)
			# rev_ident = self.identifier 

		ident = self.identifier
		rev_ident = self.relation._get_other_identifier(self.identifier)
			
		d = {rev_ident + "_id": [self.master.id]}

		if not self.slaves:
			return d

		d[ident + "_id"] = [v.id for v in self.slaves]
		return d


class LinkerTableDeleteAllQuery(LinkerTableDeleteQuery):
	"""Deletes all references to the instance from the relation's linker table.
		"""

	def __init__(self, relation, inst, identifier, db=None):
		LinkerTableDeleteQuery.__init__(self, relation, inst, identifier, None, db)


class ForeignKeyUpdateQuery(BaseQuery):
	def __init__(self, inst, fkfield, newval, db=None):
		BaseQuery.__init__(self, type(inst), db)
		
		self.inst = inst
		
		self.values = {
			self.inst.fields()[fkfield].column_name: newval,
			self.inst.fields()["pk"].column_name: self.inst.pk,
		}

	def render(self):
		sql = ["UPDATE", self.inst.tablename(), "SET"]
		sql.append(", ".join([k + "=:" + k for k in self.get_values()]))

		pk = self.inst.fields()["pk"].column_name
		sql.append("WHERE %s=:%s" %(pk, pk))
		return " ".join(sql)

	def get_values(self):
		return self.values


class Join(object):
	def __init__(self, relation, identifier):
		self.rel = self.relation = relation
		self.ident = self.identifier = identifier

	def __eq__(self, other):
		return self.rel == other.rel and self.ident == other.ident

	def __ne__(self, other):
		return not self.__eq__(other)

	def render(self):
		if self.relation.mode in (M2M, O2O):
			# Many related mode

			link_table = link_table_name(
				MODES[self.relation.mode],
				self.relation.model.tablename(),
				self.relation.identifier,
				self.relation.related_model.tablename()
			)

			return "%s AS %s LEFT OUTER JOIN %s ON %s.id = %s.%s_id LEFT OUTER JOIN %s AS %s ON %s.%s_id = %s.id" % (
				self.get_left_side(),
				self.get_left_side_alias(),
				link_table,
				self.get_left_side_alias(),
				link_table,
				self.rel._get_other_identifier(self.identifier),
				self.get_right_side(),
				self.get_right_side_alias(),
				link_table,
				self.ident,
				self.get_right_side_alias()
			)
		else:
			# Foreign key mode

			if self.rel.is_reverse_by_identifier(self.ident):
				base_table = self.get_right_side_alias()
				fk_table = self.get_left_side_alias()
			else:
				base_table = self.get_left_side_alias()
				fk_table = self.get_right_side_alias()

			model_fields = self.rel.model.fields()

			fk_field_on_base_table = model_fields.get(
				self.rel.identifier,
				model_fields.get(self.rel.reverse_identifier)
			)

			assert (fk_field_on_base_table is not None), (self.ident, self.rel.model.fields(), self.rel.related_model.fields())

			return "%s AS %s LEFT OUTER JOIN %s AS %s ON %s.%s = %s.id" % (
				self.get_left_side(),
				self.get_left_side_alias(),
				self.get_right_side(),
				self.get_right_side_alias(),
				base_table,
				fk_field_on_base_table.column_name,
				fk_table
			)

	def get_left_side(self):
		if self.rel.is_reverse_by_identifier(self.ident):
			return self.rel.related_model.tablename()
		return self.rel.model.tablename()
		
	def get_left_side_alias(self):
		"""The alias for the left table of the join."""

		return "%s_%i" % (self.get_left_side(), id(self))

	def get_right_side(self):
		if self.rel.is_reverse_by_identifier(self.ident):
			return self.rel.model.tablename()
		return self.rel.related_model.tablename()

	def get_right_side_alias(self):
		"""The alias for the right table of the join."""
		
		return "%s_%i" % (self.get_right_side(), id(self))


class SelectionLeaf(object):
	def __init__(self, join, db_table, db_column, alias=None, function=""):
		self.join = join
		
		self.db_table = db_table
		self.db_column = db_column
		self.function = function
		self.alias = (alias or
			self.db_column + ("__" + self.function.lower())*bool(self.function)
		)

	def __unicode__(self):
		return u"<" + self.__class__.__name__ + ":" + self.render() + ">"

	def __eq__(self, other):
		return (
			type(self) == type(other)
			and self.join == other.join
			and self.db_table == other.db_table
			and self.db_column == other.db_column
			and self._alias == other._alias
			and self.function == other.function
		)

	def __ne__(self, other):
		return not self.__eq__(other)

	def __deepcopy__(self, memo):
		return SelectionLeaf(
			self.join,
			self.db_table,
			self.db_column,
			self.alias,
			self.function
		)

	def get_table_alias(self):
		if self.join is not None:
			return self.join.get_left_side_alias()
		else:
			return self.db_table

	def render(self):
		return self.function.upper() +\
				"("*bool(self.function) +\
				self.get_table_alias() + "." + self.db_column +\
				")"*bool(self.function) +\
				(" AS '" + self.alias + "'")*(self.alias != self.db_column)


class WhereLeaf(object):
	def __init__(self, join, db_table, db_column, filter, value):

		self.join = join

		self.db_table = db_table
		self.db_column = db_column

		if not isinstance(value, (list, tuple, set)):
			value = [value]
		
		self.values = [getattr(v, 'pk', None) or v for v in value]

		self.filter = filter
		self.filter.set_values(self.values)

	def __deepcopy__(self, memo):
		# only compound objects need to be deepcopied
		return WhereLeaf(
			self.join,				# no need for a deep copy
			self.db_table,			# not a compound object
			self.db_column,			# not a compound object
			deepcopy(self.filter),	# compound object
			self.values				# not a compound object
		)

	def __eq__(self, other):
		return (
			type(self) == type(other)
			and self.join == other.join
			and self.db_table == other.db_table
			and self.db_column == other.db_column
		)

	def __ne__(self, other):
		return not self.__eq__(other)

	def get_table_alias(self):
		if self.join is not None:
			if self.join.rel.model.tablename() == self.db_table:
				model = self.join.rel.model
			elif self.join.rel.related_model.tablename() == self.db_table:
				model = self.join.rel.related_model
			else:
				return self.db_table

			if self.join.rel.is_self_related():
				return self.join.get_right_side_alias()

			self.db_table = "%s_%i" % (model.tablename(), id(self.join))

		return self.db_table

	def get_values(self):
		return self.filter.get_values(self.get_table_alias(), self.db_column)
		
	def render(self):
		return ("%s%s%s %s" % (
				self.get_table_alias(),
				"."*bool(self.get_table_alias()),
				self.db_column,
				self.filter.render(
					self.get_table_alias() or "Annotated",
					self.db_column,
				)
			)
		)


class OrderByLeaf(object):
	def __init__(self, model, token):
		self.model = model
		self.db_table = model.tablename()

		if token[0] == "-":
			token = token[1:]
			self.desc = True
		else:
			self.desc = False

		self.token = token

		self.db_column = model.fields()[token].column_name

	def __eq__(self, other):
		return (type(self) == type(other)
				and	self.db_table == other.db_table
				and	self.db_column == other.db_column)

	def __ne__(self, other):
		return not self.__eq__(other)

	def __deepcopy__(self, memo):
		return OrderByLeaf(
			self.model,
			"-"*self.desc + self.db_column
		)

	def toggle(self):
		self.desc = not self.desc

	def render(self):
		return "%s.%s %s" %(self.db_table, self.db_column,
										"DESC" if self.desc else "ASC")


class LimitLeaf(object):
	def __init__(self, limit=None, offset=None):
		if limit is None:
			limit = sys.maxint
		self.limit = limit

		if offset is None:
			offset = 0
		self.offset = offset

	def __deepcopy__(self, memo):
		return LimitLeaf(self.limit, self.offset)

	def render(self):
		if self.limit:
			s = "LIMIT %s" % self.limit
		if self.offset:
			s += " OFFSET %s" % self.offset
		return s

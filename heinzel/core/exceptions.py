
class BaseException(Exception):
	msg = "An error occurred."
	def __init__(self, msg="", error=0):
		if msg:
			self.msg = msg
		self.error = error

	def __str__(self):
		return self.msg


class DatabaseError(BaseException):
	msg = "Some error during the operation of the DBMS."

class DatabaseSanityError(DatabaseError):
	msg = "Database setup is wrong somehow."


class SQLSyntaxError(DatabaseError):
	msg = "SQL statement somehow malformed."


class DoesNotExist(BaseException):
	def __init__(self, model=None, params=None, msg=None):
		self.model = model
		self.params = params
		if msg is None:
			msg = (u"Dataset for model '%s' with parameters '%s' does not "
					"exist." %(str(self.model), self.params))
		self.msg = msg			


class MultipleEntriesError(BaseException):
	def __init__(self, model=None, params=None, msg=None):
		self.model = model
		self.params = params
		if msg is None:
			msg = (
				u"More than one entry in the database of model '%s' that "
				"satisfies the query parameters '%s'!"
				%(str(self.model), self.params)
			)
		self.msg = msg


class ValidationError(BaseException):
	msg = "A validation error occurred."
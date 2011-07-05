# -*- coding: utf-8 -*-

"""Please see file ‘test_relations‘ for an explanation of what's being tested
below."""


from utils import Fixture, runtests

from model_examples import Book, ISBN
from heinzel.core import models

models.register([Book, ISBN])



class populate(Fixture):
	def runTest(self):
		redstar = Book(title="Red Star over China")
		redstar.save()
		
		star_isbn = ISBN(code="1234567890123")
		star_isbn.save()
		
		redstar.isbn = star_isbn
		
		xdhycd = Book(title=u"现代汉语词典")
		xdhycd.save()
		
		xdhycd_isbn = ISBN(code="4564564564561")
		xdhycd_isbn.save()
		
		xdhycd.isbn = xdhycd_isbn


class get(Fixture):
	def runTest(self):
		redstar = Book(title="Red Star over China")
		redstar.save()
		
		star_isbn = ISBN(code="1234567890123")
		star_isbn.save()
		
		redstar.isbn = star_isbn
		
		xdhycd = Book(title=u"现代汉语词典")
		xdhycd.save()
		
		xdhycd_isbn = ISBN(code="4564564564561")
		xdhycd_isbn.save()
		
		xdhycd.isbn = xdhycd_isbn

		# db setup complete
		
		self.assert_(redstar.isbn is star_isbn)
		self.assert_(star_isbn.book is redstar)
		self.assert_(redstar.isbn.book is redstar)
		self.assert_(star_isbn.book.isbn is star_isbn)
		self.assert_(xdhycd.isbn.book.isbn.book is xdhycd)
		self.assert_(xdhycd.isbn.book.isbn is xdhycd.isbn is xdhycd_isbn)


class set(Fixture):
	def runTest(self):
		redstar = Book(title="Red Star over China")
		redstar.save()
		
		star_isbn = ISBN(code="1234567890123")
		star_isbn.save()
		
		redstar.isbn = star_isbn
		
		self.assert_(redstar.isbn is star_isbn)
		
		xdhycd = Book(title=u"现代汉语词典")
		xdhycd.save()
		
		xdhycd_isbn = ISBN(code="4564564564561")
		xdhycd_isbn.save()
		
		xdhycd.isbn = xdhycd_isbn
		self.assert_(xdhycd.isbn is xdhycd_isbn)

		# db setup complete

		# on setting an isbn that has already been related to another book,
		# the relation to the other book has to be deleted.
		redstar.isbn = xdhycd_isbn

		self.assert_(redstar.isbn is xdhycd_isbn)
		self.assert_(star_isbn.book is None)
		self.assert_(xdhycd.isbn is None)


class add(Fixture):
	"""
	This method is not available on OneToOneManagers.
	"""

	def runTest(self):
		pass


class delete(Fixture):
	"""Delete the relation unconditionally."""
	
	def runTest(self):
		redstar = Book(title="Red Star over China")
		redstar.save()
		
		star_isbn = ISBN(code="1234567890123")
		star_isbn.save()
		
		redstar.isbn = star_isbn
		
		xdhycd = Book(title=u"现代汉语词典")
		xdhycd.save()
		
		xdhycd_isbn = ISBN(code="4564564564561")
		xdhycd_isbn.save()
		
		xdhycd.isbn = xdhycd_isbn

		# db setup complete
		
		# delete
		del redstar.isbn
		
		self.assert_(redstar.isbn is None)
		self.assert_(star_isbn.book is None)
		
		# Re-set to test another way to delete
		star_isbn.book = redstar
		
		self.assert_(redstar.isbn is star_isbn)
		self.assert_(star_isbn.book is redstar)
		
		redstar.isbn = None
		
		# delete another way
		self.assert_(redstar.isbn is None)
		self.assert_(star_isbn.book is None)
		


class remove(Fixture):
	"""
	This method is not available on OneToOneManagers.
	"""

	def runTest(self):
		pass
		


if __name__ == "__main__":
	alltests = (
		populate,
		get,
		set,
		# add,			This method is not available on OneToOneManagers.
		delete,
		# remove,		This method is not available on OneToOneManagers.
	)

	runtests(tests=alltests, verbosity=3)
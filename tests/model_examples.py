# -*- coding: utf-8 -*-

import os

from heinzel.core import models
from heinzel.core import signals

NEUTRAL, MALE, FEMALE = range(3)


class Picture(models.Model):
	path = models.TextField(max_length=4096, null=False, unique=True)
	name = models.TextField(max_length=100)

	tags = models.ManyToManyField("Tag", related_name="pictures")

	def __unicode__(self):
		return u"<Picture '%s'>" % self.get_name()

	def __repr__(self):
		return self.__unicode__()

	def get_name(self):
		if self.name is None:
			self.name = self.path
		return self.name


class Tag(models.Model):
	name = models.TextField(max_length=50, null=False, unique=True)

	def __unicode__(self):
		return u"<Tag '%s'>" % self.name


class Character(models.Model):
	firstname = models.TextField(max_length=100)
	lastname = models.TextField(max_length=100)
	sex = models.IntegerField()	
	age = models.IntegerField()
	height = models.IntegerField()
	weight = models.IntegerField()
	hitpoints = models.IntegerField()
	
	titles = models.ManyToManyField("Title")
	traits = models.OneToOneField("TraitSheet")
	home_address = models.ForeignKeyField("Address")
	current_location = models.ForeignKeyField("Location")
	member_of = models.ManyToManyField("Party")

	
	def __unicode__(self):
		return u"<Character '%s'>" % self.get_name()

	def get_name(self):
		return u"%s %s" %(self.firstname, self.lastname)

	def get_respectful_name(self):
		name = [u"%s %s" %(self.firstname, self.lastname)]
		if self.title:
			name.append(self.titles[-1])
		return ", ".join(name)

	def get_nationality(self):
		return self.home_address.country.get_adjective(self.traits.sex)

	def get_hitpoints(self):
		if self.hitpoints is None:
			self.hitpoints = self.trait.max_hitpoints
		return self.hitpoints

	def get_location(self):
		if self.location is None:
			self.location = self.home_address.location
		return self.location

	def is_alive(self):
		return self.get_hitpoints() > 0

	# signals
	def model_post_init(self):
		#self.hitpoints = self.traits.max_hitpoints
		print "%s post init" %self


class Title(models.Model):
	name = models.TextField(max_length=200)
	
	def __unicode__(self):
		return u"<Title '%s'>" % self.name


class TraitSheet(models.Model):
	max_hitpoints = models.IntegerField()
	experience = models.IntegerField()
	level = models.IntegerField()
	agility = models.IntegerField()
	strength = models.IntegerField()
	intelligence = models.IntegerField()


class Address(models.Model):
	street = models.TextField(max_length=255)
	housenr = models.IntegerField()
	city = models.TextField(max_length=255)

	country = models.ForeignKeyField("Country")
	location = models.ForeignKeyField("Location")
	
	def __unicode__(self):
		return (u"<Address '%s %s, %s, %s'>" 
			%(self.street, self.housenr, self.city,
				self.country.official_name))


class Country(models.Model):
	official_name = models.TextField(max_length=500)
	abbreviated_name = models.TextField(max_length=100)
	colloquial_name = models.TextField(max_length=100)
	
	adjective_neutral = models.TextField(max_length=100)
	adjective_male = models.TextField(max_length=100)
	adjective_female = models.TextField(max_length=100)

	def __unicode__(self):
		return u"<Country %s>" %self.official_name

	def get_adjective(self, sex=NEUTRAL):
		if sex == NEUTRAL:
			return self.adjective_neutral
		if sex == MALE:
			return self.adjective_male
		if sex == FEMALE:
			return self.adjective_female


class Location(models.Model):
	x = models.IntegerField()
	y = models.IntegerField()
	
	def __unicode__(self):
		return u"<Location (x=%i, y=%i)>" %(self.x, self.y)


class Party(models.Model):
	name = models.TextField(max_length=300)
	
	def __unicode__(self):
		return u"<Party %s>" % self.name



class Item(models.Model):
	name = models.TextField(max_length=100, null=False, unique=True)
	price = models.FloatField()
	stock = models.IntegerField()
	
	def __unicode__(self):
		return "<Item '%s'>" % self.name


class Actor(models.Model):
	name = models.TextField(max_length=50)
	acted_in = models.ManyToManyField("Movie")
	
	def __unicode__(self):
		return u"<Actor '%s'>" %self.name


class Movie(models.Model):
	title =  models.TextField(max_length=50)
	
	def __unicode__(self):
		return u"<Movie '%s'>" %self.title

class UniqueTitleMovie(models.Model):
	title = models.TextField(max_length=50, unique=True)
		

class Brand(models.Model):
	
	name = models.TextField(max_length=50, unique=True)
	manufacturer = models.ForeignKeyField("Manufacturer")
	
	def __unicode__(self):
		return "<" + self.__class__.__name__ + " '" + unicode(self.name) + "'>"


class Manufacturer(models.Model):
	
	name = models.TextField(max_length=50, unique=True)

	def __unicode__(self):
		return u"<" + self.__class__.__name__ + " '" + unicode(self.name) + "'>"


class Car(models.Model):
	
	name = models.TextField(max_length=50, unique=True)
	brand = models.ForeignKeyField('Brand')
	
	def __unicode__(self):
		return "<" + self.__class__.__name__ + " '" + unicode(self.name) + "'>"


class Driver(models.Model):
	
	first_name = models.TextField(max_length=50)
	last_name = models.TextField(max_length=100)
	
	cars = models.ManyToManyField(Car)

	def __unicode__(self):
		return u"<" + self.__class__.__name__ + " '" + self.get_name() + "'>"

	def full_name(self):
		return u" ".join((str(self.first_name or ""), str(self.last_name or "")))


class Key(models.Model):
	
	serial = models.IntegerField(unique=True)
	owner = models.OneToOneField(Driver)

	def __unicode__(self):
		return u"<" + self.__class__.__name__ + " '" + unicode(self.serial) + "'>"


class Page(models.Model):
	content = models.TextField(max_length=4000)
	
	# prev = models.OneToOneField("self")
	# next = models.OneToOneField("self")


class ISBN(models.Model):
	code = models.TextField(max_length=13)
	
	book = models.OneToOneField("Book", related_name="isbn")

	def __unicode__(self):
		return u"<ISBN '%s'>" % self.code


class Book(models.Model):
	title = models.TextField(max_length=300)
	
	def __unicode__(self):
		return u"<Book '%s'>" % self.title

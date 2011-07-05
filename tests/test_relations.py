# -*- coding: utf-8 -*-

"""
The methods below test the getting, setting, deleting, adding and removing of 
one or more instances from a relation between models. These are the possible 
relations and their RelationManagers:

	Type of relation:				RelationManager class:
1)	Many-to-many					ManyToManyManager
2) 	One-to-one						OneToOneManager
3)	One-to-many						ForeignKeyManager and
4)	Many-to-one						ReverseForeignKeyManager

Accessing the above mentioned methods is done implicitly for RelationManagers 
representing the one-side of a relation (Nr. 2, 3) and explicitly for the 
many-side of a relation (Nr. 1, 4). Following is a map of overridden python 
access methods ("descriptors") to the implicitly called methods of the 
one-side RelationManager methods:

	Access method:					RelationManager method:
1)	__get__							get
2)	__set__							set
3)	__delete__						delete

Unused methods on the one-side managers are: add, remove. These are not 
necessary on one-side managers, because they add/remove one instance to/from
a set that can be more than one and one-side managers only ever hold a single 
instance, not many.

By default the relation can be accessed through the attribute name of the 
RelationField (one of heinzel.fields.ForeignKeyField, ManyToManyField,
OneToOneField) on the model where it was defined and through the 
‘related_name‘ attribute on the RelationField on the related model. By 
default the following related_names are used: 

	Type of RelationField:			related_name:
1)	ForeignKeyField					%s_set % fieldname
2)	ManyToManyField					settings.RELATED_NAME_PREFIX +
										model.__name__.lower() +
										settings.RELATED_NAME_POSTFIX
3)	OneToOneField					model.__name__.lower()

where ‘fieldname‘ is the attribute name of the RelationField and ‘model‘ is 
the primary model where it is defined.

"""

import unittest, os

from heinzel.core import models
from heinzel.core import exceptions
from utils import Fixture, runtests

# Import the models.
from model_examples import (Character, Party, Address, Location, Country,
	TraitSheet, Title, MALE, FEMALE, NEUTRAL)

# Register models, so their relations can be set up and syncdb can do its job.
models.register([Character, Party, Address, Location, Country, TraitSheet, Title])



class GrandUnifiedRelationsTest(Fixture):
	"""Test some rather complex models."""

	def runTest(self):
		# Imagine some kind of role playing game
		
		# Player Herrmann
		herman = Character(
			firstname="Herrmann",
			lastname="von Fintel",
			age=18,
			sex=MALE,
			height=185,
			weight=85,
		).save()[0]
		
		hermanstraits = TraitSheet(
			max_hitpoints=16,
			experience=5,
			level=0,
			agility=10,
			strength=12,
			intelligence=105,
		).save()[0]

		herman.traits = hermanstraits
		
		hermanstitle = Title(name="The Weasel").save()[0]
		herman.titles = [hermanstitle]
		
		hermanshome = Address(
			street="Main Street",
			housenr=2,
			city="Fintel"
		).save()[0]

		hermanslocation = Location(x=100, y=23).save()[0]
		
		
		
		herman.current_location = hermanslocation
		hermanshome.location = hermanslocation

		finisterre = Country(
			official_name="Duchy of Finisterre",
			abbreviated_name="Finisterre",
			colloquial_name="Fini",
			adjective_neutral="finisterrian",
			adjective_male="finisterrian",
			adjective_female="finisterrian",
		).save()[0]
		
		hermanshome.country = finisterre
		
		herman.home_address = hermanshome
		
		# Player Meister, mentor of Player Herrmann
		meister = Character(
			firstname="Kuhnibert",
			lastname="Morgenstern",
			age=42,
			sex=MALE,
			height=174,
			weight=88,
		).save()[0]
		
		meisterstraits = TraitSheet(
			max_hitpoints=25,
			experience=24,
			level=8,
			agility=13,
			strength=18,
			intelligence=116,
		).save()[0]

		meister.traits = meisterstraits
		
		meisterstitle = Title(name="Master").save()[0]
		meister.titles = [meisterstitle]
		
		meistershome = Address(
			street="Meister's Rock",
			housenr=3,
			city="Fintel"
		).save()[0]

		meisterslocation = Location(x=101, y=25).save()[0]
		
		meister.current_location = meisterslocation
		meistershome.location = meisterslocation
		
		meistershome.country = finisterre
		
		meister.home_address = meistershome

		# Shady villain
		villain = Character(
			firstname="Dante",
			lastname="de Krouffe",
			age=38,
			sex=MALE,
			height=188,
			weight=80,
		).save()[0]
	
		villainstraits = TraitSheet(
			max_hitpoints=25,
			experience=34,
			level=11,
			agility=19,
			strength=23,
			intelligence=110
		).save()[0]

		villain.traits = villainstraits
		
		villainstitle = Title(name="The Crow").save()[0]
		villainstitle2 = Title(name="Ambassador of the Duke").save()[0]
		villain.titles = [villainstitle, villainstitle2]
		
		villainshome = Address(
			street="Decay Road",
			housenr=666,
			city="Badsville"
		).save()[0]

		villainslocation = Location(x=92, y=21).save()[0]
		
		villain.current_location = villainslocation
		villainshome.location = Location(x=203, y=45).save()[0]

		villainshome.country = finisterre
		
		villain.home_address = villainshome
		
		
		party = Party(name="The visitor's to the Duke").save()[0]
		party.character_set = [villain, meister, herman]
		
		###
		###
		
		self.assert_(party in meister.member_of)
		self.assert_(party in herman.member_of)
		self.assert_(party in villain.member_of)
		

		
		
		
		

		



if __name__ == "__main__":
	alltests = (
		GrandUnifiedRelationsTest,
	)

	runtests(tests=alltests, verbosity=3)
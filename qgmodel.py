from peewee import *

db = SqliteDatabase('data/qg.db')

class Questions(Model):
    question = CharField(null=True)
    answer = CharField(null=True)
    choice1 = CharField(null=True)
    choice2 = CharField(null=True)
    choice3 = CharField(null=True)
    choice4 = CharField(null=True)
    class Meta:
        database = db
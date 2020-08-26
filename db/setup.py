#  TODO: startup script to initialize DB
from mongoengine import connect
connect(db="tempdb")

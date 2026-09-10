import sqlite3
from pathlib import Path
def req(c,m):
 if not c:raise AssertionError(m)
def db(r:Path,version=1):
 p=r/'profiles.db';con=sqlite3.connect(p);con.execute('CREATE TABLE schema_meta(version INTEGER NOT NULL)');con.execute('INSERT INTO schema_meta VALUES(?)',(version,));con.execute('CREATE TABLE profiles(id INTEGER PRIMARY KEY,name TEXT NOT NULL)');con.executemany('INSERT INTO profiles(id,name) VALUES(?,?)',[(1,'Ada Lovelace'),(2,'Grace Hopper')]);con.commit();con.close();return p

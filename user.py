import hashlib
import hmac
import random
from string import letters

from google.appengine.ext import db

#create salt for hash password
def make_salt(length = 5):
  return ''.join(random.choice(letters) for x in xrange(length))

#create hash password
def make_pw_hash(name, pw, salt = None):
    if not salt:
      salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (salt, h)

#check password
def check_pw(name, pw, pw_hash):
  salt = pw_hash.split(',')[0]
  return pw_hash == make_pw_hash(name, pw, salt)

#create a hash of the username
def make_un_hash(secret, username):
  return '%s' % hmac.new(secret, username).hexdigest()

#User object
class User(db.Model):
  """
  Creates a User object with variables name, pw_hash (a hashed
  password and email)
  """
  name = db.StringProperty(required = True)
  pw_hash = db.StringProperty(required = True)
  email = db.StringProperty()
  liked_posts = db.StringListProperty()
  unliked_posts = db.StringListProperty()

  @classmethod
  def by_name(cls, name):
    #Get a User by name
    u = User.all().filter('name =', name).get()
    return u

  @classmethod
  def register(cls, name, password, email, secret):
    #Hash the entered password and username and then create User object
    hash_password = make_pw_hash(name, password)
    hash_username = make_un_hash(secret, name)
    u = User(name = hash_username, pw_hash = hash_password, email = email, liked_posts = [], unliked_posts = [])
    u.put()

  @classmethod
  def login(cls, name, password, secret):
    #see if username exisits
    hash_username = make_un_hash(secret, name)
    u = cls.by_name(hash_username)
    if u and check_pw(name, password, u.pw_hash):
      return u
from google.appengine.ext import db

#Post object
class Post(db.Model):
  title = db.StringProperty(required = True)
  post = db.TextProperty(required = True)
  created = db.DateTimeProperty(auto_now_add = True)
  created_by = db.StringProperty(required = True)
  likes = db.IntegerProperty()

class Comment(db.Model):
  post = db.ReferenceProperty(Post, collection_name = "blog_comments")
  comment = db.TextProperty(required = True)
  created = db.DateTimeProperty(auto_now_add = True)
  created_by = db.StringProperty(required = True)
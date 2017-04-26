from google.appengine.ext import db

#Post object
class Post(db.Model):
  """
  Creates a Blog Post object with variables title, post,
  created (a date), created_by and likes
  """
  title = db.StringProperty(required = True)
  post = db.TextProperty(required = True)
  created = db.DateTimeProperty(auto_now_add = True)
  created_by = db.StringProperty(required = True)
  likes = db.IntegerProperty()


#Comment Object
class Comment(db.Model):
  """
  Creates a comment object with variables post,
  comment, created (a date) and created_by
  """
  post = db.ReferenceProperty(Post, collection_name = 'blog_comments')
  comment = db.TextProperty(required = True)
  created = db.DateTimeProperty(auto_now_add = True)
  created_by = db.StringProperty(required = True)
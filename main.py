# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import jinja2
import webapp2
import re
import hashlib
import hmac
import time
import operator

from google.appengine.ext import db

import user
import blogPost

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
  autoescape = True)

SECRET = 'tGhlsdmn92jbe'


def make_secure_hash(var):
  return '%s|%s' % (var, hmac.new(SECRET, var).hexdigest())


#Handler class to make rendering pages easier and contain helper methods
class Handler(webapp2.RequestHandler):
  def write(self, *a, **kw):
    self.response.out.write(*a, **kw)

  def render_str(self, template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

  def render(self, template, **kw):
    self.write(self.render_str(template, **kw))

  def create_cookie(self, username):
    user_hash = str(make_secure_hash(username))
    self.response.headers.add_header('Set-Cookie', 'user_id='+user_hash)

  def check_user(self, what_object):
    if hmac.new(SECRET, self.request.cookies.get('user_id') \
      .split('|')[0]).hexdigest() == \
      self.request.cookies.get('user_id').split('|')[1] and \
      self.request.cookies.get('user_id').split('|')[1] == \
      what_object.created_by.name:
      return True

  def wait_for_eventual_consistancy(self):
    time.sleep(.1)


#Create an account
class Signup(Handler):
  def get(self):
    self.render('signin.html')

  def post(self):
    if self.request.get('login'):
      self.redirect('/login')
    else:
      self.username = self.request.get('username')
      self.password = self.request.get('password')
      self.verify = self.request.get('verify')
      self.email = self.request.get('email')
      errorFound = False

      params = dict(username = self.username)

      #Check to ensure valid details entered
      if not self.valid_username(self.username):
        params['error_username'] = "That's not a valid username."
        errorFound = True
      if not self.unique_username(self.username):
        params['error_username'] = 'That username already exists'
        errorFound = True
      if not self.valid_password(self.password):
        params['error_password'] = "That's not a valid password."
        errorFound = True
      if not self.password_match(self.password, self.verify):
        params['error_verify'] = "Your passwords didn't match."
        errorFound = True
      if not self.valid_email(self.email):
        params['error_email'] = "That's not a valid email."
        errorFound = True

      if not errorFound:
        self.done()
      else:
        self.render('signin.html', **params)

  def done():
    raise NotImplementedError

  def valid_username(self, username):
    USER_RE = re.compile(r'^[a-zA-Z0-9_-]{3,20}$')
    return USER_RE.match(username)

  def valid_password(self, password):
    PW_RE = re.compile(r'^.{3,20}$')
    return PW_RE.match(password)

  def valid_email(self, email):
    EMAIL_RE = re.compile(r'^[\S]+@[\S]+.[\S]+$')
    if not email:
      return True
    else:
      return EMAIL_RE.match(email)

  def password_match(self, first, second):
    if first == second:
      return True

  def hash_str(self, s):
    return hashlib.sha256(s).hexdigest()

  def unique_username(self, username):
    username_unique = user.User.by_name(username)
    if not username_unique:
      return True


#Register a new user
class Register(Signup):
  def done(self):
    u = user.User.by_name(self.username)
    if u:
      self.render('signin.html', error_username = 'That user already exists')
    else:
      u = user.User.register(self.username, self.password, self.email, SECRET)
      self.create_cookie(self.username)
      self.redirect('/')


#Login to blog
class Login(Handler):
  def get(self):
    #If a cookie exists go straight to homepage, otherwise render login page
    h = self.request.cookies.get('user_id')
    if h:
      self.redirect('/')
    else:
      self.render('login.html')

  def post(self):
    if self.request.get('signup'):
      self.redirect('/signup')
    else:
      #Check valid username and password entered
      username = self.request.get('username')
      password = self.request.get('password')
      u = user.User.login(username, password, SECRET)
      if u:
        self.create_cookie(username)
        self.redirect('/')
      else:
        self.render('login.html', error = 'Invalid login')


#Home page displaying last 10 blog posts
class Home(Handler):
  def get(self):
    #Only render homepage if a user is logged in
    logged_in_user = self.request.cookies.get('user_id')
    if logged_in_user:
      posts = db.GqlQuery('SELECT * FROM Post ORDER BY created DESC LIMIT 10')
      self.render('home.html', posts = posts)
    else:
      self.redirect('/login')


#Like a post - post author cannot like own post and user can only like once
class LikePost(Handler):
  def post(self):
    #from pdb import set_trace
    #set_trace()
    post = blogPost.Post.get_by_id(int(self.request.get('post_id')))
    posts = db.GqlQuery('SELECT * FROM Post ORDER BY created DESC LIMIT 10')
    if post is not None:
      current_user = user.User.by_name(self.request.cookies.get('user_id').
        split('|')[1])
      if current_user is not None:
        if self.check_user(post):
          self.render('home.html', posts = posts,
            like_error = 'You can not like your own post',
            error_id = int(self.request.get('post_id')))
        else:
          if self.request.get('post_id') in current_user.liked_posts:
            self.render('home.html', posts = posts,
              like_error = 'You have already liked this post',
              error_id = int(self.request.get('post_id')))
          else:
            updated_likes = post.likes + 1
            post.likes = updated_likes
            current_user.liked_posts.append(self.request.get('post_id'))
            current_user.put()
            post.put()
            self.wait_for_eventual_consistancy()
            self.render('home.html', posts = posts)


#Unlike a post - post author cannot unlike own post and
#user can only unlike once
class UnlikePost(Handler):
  def post(self):
    post = blogPost.Post.get_by_id(int(self.request.get('post_id')))
    posts = db.GqlQuery('SELECT * FROM Post ORDER BY created DESC LIMIT 10')
    if post is not None:
      current_user = user.User.by_name(self.request.cookies.get('user_id')
        .split('|')[1])
      if current_user is not None:
        if self.check_user(post):
          self.render('home.html', posts = posts,
            like_error = 'You can not unlike your own post',
            error_id = int(self.request.get('post_id')))
        else:
          if self.request.get('post_id') in current_user.unliked_posts:
            self.render('home.html', posts = posts,
              like_error = 'You have already unliked this post',
              error_id = int(self.request.get('post_id')))
          else:
            updated_likes = post.likes - 1
            post.likes = updated_likes
            current_user.liked_posts.append(self.request.get('post_id'))
            current_user.put()
            post.put()
            self.wait_for_eventual_consistancy()
            self.render('home.html', posts = posts)


#Create a new blog post
class NewPost(Handler):
  def get(self):
    self.render('new_entry.html')

  def post(self):
    title = self.request.get('subject')
    post = self.request.get('content')
    created_by = user.User.by_name(self.request.cookies.get('user_id')
      .split('|')[1])
    #Only create a new Post if a title and content have been
    #added and a user is logged in
    if title and post and self.request.cookies.get('user_id'):
      p = blogPost.Post(title = title, post = post,
        created_by = created_by, likes = 0)
      p.put()
      key = str(p.key().id())
      self.redirect('/' + key, p.key().id())
    else:
      self.render("new_entry.html", error = 'Enter a title and a post')


#Indivdual blog post page, this is where you can edit or delete
#a blog post and add comments
class PostPage(Handler):
  def get(self, post_id):
    post = blogPost.Post.get_by_id(int(post_id))
    sorted_comments = post.blog_comments.order('-created')
    self.render("post_page.html", title = post.title, content = post.post,
      post_id = post_id, comments = sorted_comments)


#Edit a blog post
class EditPost(Handler):
  def get(self):
    post_id = self.request.get('post')
    post = blogPost.Post.get_by_id(int(post_id))
    if post is not None:
      if not self.check_user(post):
        self.render('post_page.html', title = post.title,
          content = post.post, post_id = post.key().id(),
          comments = post.blog_comments,
          error='You can not edit this post')
      else:
        self.render('edit_post.html', title = post.title,
          content = post.post,
          post_id = post_id)

  def post(self):
    post_id = self.request.get('post')
    if self.request.get('cancel'):
      self.redirect('/' + str(post_id), post_id)
    else:
      post = blogPost.Post.get_by_id(int(post_id))
      updated_title = self.request.get('title')
      updated_content = self.request.get('content')
      post.title = updated_title
      post.post = updated_content
      post.put()
      self.wait_for_eventual_consistancy()
      self.redirect('/' + str(post_id), post_id)


#Delete a post - only post author can delete post
class DeletePost(Handler):
  def get(self):
    self.redirect('/')

  def post(self):
    post_id = self.request.get('post')
    post = blogPost.Post.get_by_id(int(post_id))
    if post is not None:
      if not self.check_user(post):
        self.render('post_page.html', title = post.title,
          content = post.post, post_id = post_id,
          comments = post.blog_comments,
          error='Only post author can delete this post')
      else:
        post.delete()
        self.wait_for_eventual_consistancy()
        self.redirect('/')


#Comment on a blog post - anyone can comment
class Comment(Handler):
  def get(self):
    self.render('comment.html')

  def post(self):
    post_id = self.request.get('post')
    if self.request.get('cancel'):
      self.redirect('/' + str(post_id))
    else:
      comment = self.request.get('comment')
      created_by = user.User.by_name(self.request.cookies.get('user_id')
        .split('|')[1])
      post = blogPost.Post.get_by_id(int(post_id))
      c = blogPost.Comment(post = post, comment = comment,
        created_by = created_by)
      c.put()
      self.wait_for_eventual_consistancy()
      self.redirect('/' + str(post_id))


#Edit a comment - only comment author can edit
class EditComment(Handler):
  def get(self):
    comment = blogPost.Comment.get_by_id(int(self.request.get('comment')))
    post = blogPost.Post.get_by_id(int(self.request.get('post')))
    if comment is not None:
      if not self.check_user(comment):
        self.render('post_page.html', title = post.title,
          content = post.post, post_id = post.key().id(),
          comments = post.blog_comments,
          comment_error='You can not edit or delete this comment',
          error_id = comment.key().id())
      else:
        self.render('edit_comment.html', comment = comment.comment,
          comment_id = self.request.get('comment'))

  def post(self):
    c = blogPost.Comment.get_by_id(int(self.request.get('comment')))
    if self.request.get('cancel'):
      self.redirect('/' + str(c.post.key().id()))
    else:
      new_comment = self.request.get('content')
      c.comment = new_comment
      c.put()
      self.wait_for_eventual_consistancy()
      self.redirect('/' + str(c.post.key().id()))


#Delete a commment - only comment author can delete
class DeleteComment(Handler):
  def get(self):
    self.redirect('/')

  def post(self):
    comment = blogPost.Comment.get_by_id(int(self.request.get('comment')))
    post = blogPost.Post.get_by_id(int(self.request.get('post')))
    if comment is not None:
      if not self.check_user(comment):
        self.render('post_page.html', title = post.title,
          content = post.post, post_id = post.key().id(),
          comments = post.blog_comments,
          comment_error='You can not edit or delete this comment',
          error_id = comment.key().id())
      else:
        comment.delete()
        self.wait_for_eventual_consistancy()
        self.render('post_page.html', title = post.title,
          content = post.post, post_id = post.key().id(),
          comments = post.blog_comments)


#Logout of blog
class Logout(Handler):
  def get(self):
    self.response.headers.add_header('Set-Cookie', 'user_id=;Path="/"')
    self.redirect('/signup')

app = webapp2.WSGIApplication([
    ('/', Home),
    ('/newpost', NewPost),
    ('/([0-9]+)', PostPage),
    ('/signup', Register),
    ('/login', Login),
    ('/logout', Logout),
    ('/edit_post', EditPost),
    ('/delete_post', DeletePost),
    ('/comment', Comment),
    ('/edit_comment', EditComment),
    ('/delete_comment', DeleteComment),
    ('/like_post', LikePost),
    ('/unlike_post', UnlikePost)
], debug=True)
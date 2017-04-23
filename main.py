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

import user
import blogPost

from google.appengine.ext import db

def someFunction():
  print "Click"

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)
jinja_env.globals['someFunction'] = someFunction
USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
PW_RE = re.compile(r"^.{3,20}$")
EMAIL_RE = re.compile(r"^[\S]+@[\S]+.[\S]+$")
SECRET = "tGhlsdmn92jbe"

def make_secure_hash(var):
  return '%s|%s' % (var, hmac.new(SECRET, var).hexdigest())

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

class MainPage(Handler):
  def get(self):
    logged_in_user = self.request.cookies.get('user_id')
    if logged_in_user:
      posts = db.GqlQuery("SELECT * FROM Post ORDER BY created DESC LIMIT 10")
      self.render("home.html", posts = posts)
    else:
      self.redirect("/login")

  def post(self):
    print "click"
    post_id = self.request.get('post_id')
    key = str(post_id)
    self.redirect('/'+key, post_id)

class NewPost(Handler):
  def get(self):
    self.render("new_entry.html")

  def post(self):
    title = self.request.get('subject')
    post = self.request.get('content')
    created_by = self.request.cookies.get('user_id').split('|')[0]
    if title and post:
      p = blogPost.Post(title = title, post = post, created_by = created_by)
      p.put()
      key = str(p.key().id())
      self.redirect('/'+key, p.key().id())
    else:
      self.render("new_entry.html", error="Enter a title and a post")

class PostPage(Handler):
  def get(self, post_id):
    post = blogPost.Post.get_by_id(int(post_id))
    self.render("post_page.html", title = post.title, content = post.post)

class SignUp(Handler):
  def get(self):
    self.render("signin.html")

  def post(self):
    self.username = self.request.get('username')
    self.password = self.request.get('password')
    self.verify = self.request.get('verify')
    self.email = self.request.get('email')
    errorFound = False

    params = dict(username = self.username)

    if not self.valid_username(self.username):
      params['error_username'] = "That's not a valid username."
      errorFound = True;
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
      self.render("signin.html", **params)

  def done():
    raise NotImplementedError

  def valid_username(self, username):
    return USER_RE.match(username)

  def valid_password(self, password):
    return PW_RE.match(password)

  def valid_email(self, email):
    if not email:
      return True
    else:
      return EMAIL_RE.match(email)

  def password_match(self, first, second):
    if first == second:
      return True

  def hash_str(self, s):
    return hashlib.sha256(s).hexdigest()

class Register(SignUp):
  def done(self):
    print "Done was called"
    u = user.User.by_name(self.username)
    if u:
      print 'U exists'
      self.render("signin.html", error_username = "That user already exists")
    else:
      u = user.User.register(self.username, self.password, self.email)
      self.create_cookie(self.username)
      self.redirect('/welcome')

class Welcome(Handler):
  def get(self):
    username = self.request.cookies.get('user_id').split('|')[0]
    self.render("welcome.html", username = username)

class Login(Handler):
  def get(self):
    h = self.request.cookies.get('user_id')
    if h:
      #print h .split('|')[0]
      self.redirect('/welcome')
    else:
      self.render("login.html")

  def post(self):
    username = self.request.get('username')
    password = self.request.get('password')
    u = user.User.login(username, password)
    if u:
      self.create_cookie(username)
      self.redirect('/welcome')
    else:
      self.render("login.html", error = "Invalid login")

class Logout(Handler):
  def get(self):
    self.response.headers.add_header('Set-Cookie', 'user_id=;Path="/"')
    self.redirect('/signup')

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/newpost', NewPost),
    ('/([0-9]+)', PostPage),
    ('/signup', Register),
    ('/welcome', Welcome),
    ('/login', Login),
    ('/logout', Logout)
], debug=True)

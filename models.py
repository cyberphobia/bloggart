import aetycoon
import datetime
import hashlib
import re

from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext import deferred

import config
import generators
import markup
import static
import utils


if config.default_markup in markup.MARKUP_MAP:
  DEFAULT_MARKUP = config.default_markup
else:
  DEFAULT_MARKUP = 'html'


class BlogDate(db.Model):
  """Contains a list of year-months for published blog posts."""

  @classmethod
  def get_key_name(cls, post):
    return '%d/%02d' % (post.published.year, post.published.month)

  @classmethod
  def create_for_post(cls, post):
    inst = BlogDate(key_name=BlogDate.get_key_name(post))
    inst.put()
    return inst

  @classmethod
  def datetime_from_key_name(cls, key_name):
    year, month = key_name.split("/")
    return datetime.datetime(int(year), int(month), 1, tzinfo=utils.tzinfo())

  @property
  def date(self):
    return BlogDate.datetime_from_key_name(self.key().name()).date()


class BlogPost(db.Model):
  # Name of the handler that serves this Model
  HANDLER = 'PostHandler'

  # The URL path to the blog post. Posts have a path iff they are published.
  path = db.StringProperty()
  title = db.StringProperty(required=True, indexed=False)
  body_markup = db.StringProperty(choices=set(markup.MARKUP_MAP),
                                  default=DEFAULT_MARKUP)
  body = db.TextProperty(required=True)
  tags = aetycoon.SetProperty(basestring, indexed=False)
  published = db.DateTimeProperty()
  created = db.DateTimeProperty(auto_now_add=True)
  updated = db.DateTimeProperty(auto_now=True)
  deps = aetycoon.PickleProperty()
  draft = db.TextProperty()
  is_deleted = db.BooleanProperty(default=False)

  @aetycoon.TransformProperty(tags)
  def normalized_tags(tags):
    return list(set(utils.slugify(x.lower()) for x in tags))

  @property
  def tag_pairs(self):
    return [(x, utils.slugify(x.lower())) for x in self.tags]

  @property
  def rendered(self):
    """Returns the rendered body."""
    return markup.render_body(self)

  @property
  def summary(self):
    """Returns a summary of the blog post."""
    return markup.render_summary(self)

  @property
  def hash(self):
    val = (self.title, self.body, self.published)
    return hashlib.sha1(str(val)).hexdigest()

  @property
  def summary_hash(self):
    val = (self.title, self.summary, self.tags, self.published)
    return hashlib.sha1(str(val)).hexdigest()

  def set_key_name(self, key_name):
    post_properties = BlogPost.properties()
    del post_properties['normalized_tags']
    new_post = BlogPost(
        key_name=key_name,
        **dict([(prop, getattr(self, prop)) for prop in post_properties]))
    return new_post

  def update(self, body, is_draft=False):
    if is_draft:
      self.draft = body
    else:
      memcache.flush_all()
      self.draft = None
      self.body = body

    if not self.path and not is_draft:
      # Post is being published for the first time
      self.published = datetime.datetime.now()
      same_path = True
      count = 0
      while same_path:
        path = utils.format_post_path(self, count)
        same_path = models.BlogPost.get_by_key_name(path)
        count += 1

      self.path = path
      if self.is_saved():
        new_post = self.set_key_name(path)
        new_post.put()
        self.delete()
        BlogDate.create_for_post(new_post)
        return new_post

    if not self.is_saved():
      new_post = self.set_key_name('/draft:' + utils.slugify(self.title))
      new_post.put()
      return new_post

    self.put()
    return self

  def remove(self):
    if not self.is_saved():
      return

    # TODO: Delete BlogDate if this is the only entry for the date.
    self.delete()
    memcache.flush_all()

  @classmethod
  def get_prev_next(cls, post):
    """Retrieves the chronologically previous and next post for this post"""
    q = cls.all().order('-published')
    q.filter('is_draft =', False)
    q.filter('is_deleted =', False)
    q.filter('published <', post.published)
    prev = q.get()

    q = cls.all().order('published')
    q.filter('is_draft =', False)
    q.filter('is_deleted =', False)
    q.filter('published >', post.published)
    next = q.get()

    return prev,next


class Page(db.Model):
  # The URL path to the page.
  path = db.StringProperty(required=True)
  title = db.TextProperty(required=True)
  template = db.StringProperty(required=True)
  body = db.TextProperty(required=True)
  created = db.DateTimeProperty(required=True, auto_now_add=True)
  updated = db.DateTimeProperty()

  @property
  def rendered(self):
    # Returns the rendered body.
    return markup.render_body(self)

  @property
  def hash(self):
    val = (self.path, self.body, self.published)
    return hashlib.sha1(str(val)).hexdigest()

  def publish(self):
    self._key_name = self.path
    self.put()
    generators.PageContentGenerator.generate_resource(self, self.path);

  def remove(self):
    if not self.is_saved():   
      return
    self.delete()
    generators.PageContentGenerator.generate_resource(self, self.path, action='delete')

class VersionInfo(db.Model):
  bloggart_major = db.IntegerProperty(required=True)
  bloggart_minor = db.IntegerProperty(required=True)
  bloggart_rev = db.IntegerProperty(required=True)

  @property
  def bloggart_version(self):
    return (self.bloggart_major, self.bloggart_minor, self.bloggart_rev)

class CsrfSecret(db.Model):
  secret = db.StringProperty(required=True)

  @staticmethod
  def get():
    secret = memcache.get('csrf_secret')
    if not secret:
      csrf_secret = CsrfSecret.all().get()
      if csrf_secret:
        memcache.set('csrf_secret', csrf_secret.secret)
      else:
        # hmm, nothing found? We need to generate a secret for csrf protection.
        import os, binascii
        secret = binascii.b2a_hex(os.urandom(16))
        csrf_secret = CsrfSecret(secret=secret)
        csrf_secret.put()

      secret = csrf_secret.secret
      memcache.set('csrf_secret', secret)

    return secret


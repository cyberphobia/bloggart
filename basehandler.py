import os

from google.appengine.api import memcache
from google.appengine.api import users

import jinja2
import webapp2

import config
import models
import xsrfutil


def csrf_protect(func):
  """Decorator to protect get and post functions from CSRF."""
  def decorate(self, *args, **kwargs):
    path = os.environ.get('PATH_INFO', '/')
    token = self.request.get('csrf', None)
    if not token:
      self.error(403)
      return

    if not xsrfutil.validate_token(models.CsrfSecret.get(), token,
        users.get_current_user().user_id(), path):
      self.error(403)
      return

    return func(self, *args, **kwargs)

  return decorate


def cached(content_type='text/html; charset=utf-8'):
  """Decorator for caching the output in memcache.

  Note that the decorator requires that the page is identified by a key passed
  as first argument to get/post functions bearing this decorator. This
  decorator should only be used if the output is always the same for the same
  key.
  """
  def wrapper(func):
    def decorate(self, key):
      handler_name = self.__class__.__name__
      memcache_key = 'cache:%s:%s' % (handler_name, key)
      cached_output = memcache.get(memcache_key)
      if not cached_output:
        cached_output = func(self, key)
        memcache.set(memcache_key, cached_output)

      self.response.headers['Content-Type'] = content_type
      self.response.out.write(cached_output)

    return decorate
  return wrapper


class BaseHandler(webapp2.RequestHandler):
  def _csrf_token(self, path=None):
    """Generates a CSRF token for the given path."""
    if not path:
      path = os.environ.get('PATH_INFO')
    user_id = 'anonymous'
    if self.user:
      user_id = self.user.user_id()
    return xsrfutil.generate_token(models.CsrfSecret.get(), user_id, path)

  def __init__(self, request=None, response=None):
    super(BaseHandler, self).__init__(request, response)

    base_templ_dir = os.path.join(os.path.dirname(__file__), 'themes')
    template_dirs = [os.path.abspath(os.path.join(base_templ_dir, 'default'))]
    if config.theme and config.theme != 'default':
      template_dirs.insert(0, os.path.abspath(os.path.join(base_templ_dir, config.theme)))

    self.jinja = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dirs),
        extensions=['jinja2.ext.autoescape'],
        autoescape=True)
    self.jinja.globals['csrf_token'] = self._csrf_token

    self.user = users.get_current_user()

    # Default template variables
    self.templ = {}
    self.templ['config'] = config
    self.templ['devel'] = os.environ['SERVER_SOFTWARE'].startswith('Devel')
    self.templ['path'] = os.environ.get('PATH_INFO')
    self.templ['handler_class'] = self.__class__.__name__
    self.templ['is_admin'] = False
    if self.user:
      self.templ['is_admin'] = users.is_current_user_admin()

  def render_to_response(self, template_name, template_vals=None, theme=None,
                         content_type='text/html; charset=utf-8'):
    self.response.headers['Content-Type'] = content_type
    self.response.out.write(self.render(template_name, template_vals, theme))

  def render(self, template_name, template_vals=None, theme=None):
    if not template_vals:
      template_vals = self.templ
    import pprint
    pprint.pprint(self.templ)
    template = self.jinja.get_template(template_name)
    return template.render(template_vals)

  def fail(self, error=404, template='404.html'):
    self.error(error)
    self.render_to_response(template)

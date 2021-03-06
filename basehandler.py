import os

from google.appengine.api import memcache
from google.appengine.api import users

import jinja2
import webapp2

import config
import models
import xsrfutil


def cached(content_type='text/html; charset=utf-8'):
  """Decorator for caching the output in memcache.

  Note that the decorator requires that the page is identified by a key passed
  as first argument to get/post functions bearing this decorator. This
  decorator should only be used if the output is always the same for the same
  key.
  """
  def wrapper(func):
    def decorate(self, *args, **kwargs):
      # Use the "key" argument, or the first non-kw argument, or the first kwarg.
      key = kwargs.get('key', None)
      if not key and len(args) > 0:
        key = args[0]

      handler_name = self.__class__.__name__
      memcache_key = 'cache:%s:%s' % (handler_name, key)
      cached_output = memcache.get(memcache_key)
      if not cached_output or users.is_current_user_admin():
        cached_output = func(self, *args, **kwargs)
        if not users.is_current_user_admin():
          memcache.set(memcache_key, cached_output)

      self.response.headers['Content-Type'] = content_type
      self.response.out.write(cached_output)

    return decorate
  return wrapper


class BaseHandler(webapp2.RequestHandler):

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
    self.jinja.globals['csrf_token'] = xsrfutil.xsrf_token

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
    template = self.jinja.get_template(template_name)
    return template.render(template_vals)

  def fail(self, error=404, template='404.html'):
    self.error(error)
    return self.render(template)

  def fail_to_response(self, error=404, template='404.html'):
    self.response.out.write(self.fail(error, template))

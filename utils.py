import os
import re
import unicodedata

from google.appengine.api import users
import jinja2
import webapp2

import config
import generators
import models


def slugify(s):
  s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore')
  return re.sub('[^a-zA-Z0-9-]+', '-', s).strip('-')


def format_post_path(post, num):
  slug = slugify(post.title)
  if num > 0:
    slug += "-" + str(num)
  date = post.published
  return config.post_path_format % {
      'slug': slug,
      'year': date.year,
      'month': date.month,
      'day': date.day,
  }


def _get_all_paths():
  import static
  keys = []
  q = static.StaticContent.all(keys_only=True).filter('indexed', True)
  cur = q.fetch(1000)
  while len(cur) == 1000:
    keys.extend(cur)
    q = static.StaticContent.all(keys_only=True)
    q.filter('indexed', True)
    q.filter('__key__ >', cur[-1])
    cur = q.fetch(1000)
  keys.extend(cur)
  return [x.name() for x in keys]


def _regenerate_sitemap():
  import static
  import gzip
  from StringIO import StringIO
  paths = _get_all_paths()
  rendered = generators.ContentGenerator.render('sitemap.xml', {'paths': paths})
  static.set('/sitemap.xml', rendered, 'application/xml', False)
  s = StringIO()
  gzip.GzipFile(fileobj=s,mode='wb').write(rendered)
  s.seek(0)
  renderedgz = s.read()
  static.set('/sitemap.xml.gz',renderedgz, 'application/x-gzip', False)
  if config.google_sitemap_ping:
      ping_googlesitemap()

def ping_googlesitemap():
  # Don't ping Google webmaster tools for development instance
  if os.environ['SERVER_SOFTWARE'].startswith('Devel'):
    return

  import urllib
  from google.appengine.api import urlfetch
  google_url = 'http://www.google.com/webmasters/tools/ping?sitemap=http://' + config.host + '/sitemap.xml.gz'
  response = urlfetch.fetch(google_url, '', urlfetch.GET)
  if response.status_code / 100 != 2:
    raise Warning("Google Sitemap ping failed", response.status_code, response.content)

import datetime
import itertools
import os

import webapp2

from google.appengine.api import memcache
from google.appengine.ext import db

import basehandler
import config
import models


class BlogPostHandler(basehandler.BaseHandler):
  @basehandler.cached()
  def get(self, post_key):
    post = models.BlogPost.get_by_key_name(post_key)
    if not post or post.is_deleted:
      return self.fail(error=404, template='404.html')

    prev, next = models.BlogPost.get_prev_next(post)
    self.templ['post'] = post
    self.templ['prev'] = prev
    self.templ['next'] = next

    return self.render('post.html')


class PostListingHandler(basehandler.BaseHandler):
  @basehandler.cached()
  def get(self, page_nr=1):
    page = int(page_nr) or 1

    # We're limiting ourselves to 1000 blog posts here, but protecting
    # us against a DoS, where someone enters large numbers and causes
    # all entities to be retrieved over and over again.
    if page < 1 or page > 100:
      return self.fail(404)

    q = models.BlogPost.all().order('-published')
    q.filter('published !=', None)
    q.filter('is_deleted =', False)

    # This is not super-efficient, as if we're on, say, page 10, the first 90
    # blog posts are retrieved and discarded. Since we're not going to have
    # hundreds of pages though, probably not worth to over-optimize.
    self.templ['posts'] = q.run(offset=(page-1)*10, limit=10)
    self.templ['page'] = page
    self.templ['page_path'] = '/page'

    return self.render('listing.html')


class ArchiveHandler(basehandler.BaseHandler):
  @basehandler.cached()
  def get(self, date):
    (year, month) = map(int, date.split('/'))
    start = datetime.datetime(year, month, 1)
    if start < datetime.datetime(2013, 07, 01) or start > datetime.datetime.now():
      return self.fail(404)
    end = start + datetime.timedelta(days=32)
    end = end.replace(day=1) - datetime.timedelta(milliseconds=1)

    q = models.BlogPost.all().order('-published')
    q.filter('published >', start)
    q.filter('published <', end)
    q.filter('is_deleted =', False)

    self.templ['posts'] = q.run()

    return self.render('listing.html')


class ArchiveIndexHandler(basehandler.BaseHandler):
  @basehandler.cached()
  def get(self):
    q = models.BlogDate.all().order('-__key__')
    dates = [entry.date for entry in q]
    date_struct = {}
    for date in dates:
      date_struct.setdefault(date.year, []).append(date)

    self.templ['years'] = reversed(sorted(date_struct.keys()))
    self.templ['date_struct'] = date_struct

    return self.render('archive.html')


class TagsHandler(basehandler.BaseHandler):
  @basehandler.cached()
  def get(self, tag):
    page = 1
    if '/' in tag:
      (tag, page) = tag.split('/')

    page = int(page) or 1
    if page < 1 or page > 10:
      return self.fail(404)

    q = models.BlogPost.all().order('-published')
    q.filter('normalized_tags =', tag)
    q.filter('is_deleted =', False)

    self.templ['posts'] = q.run(offset=(page-1)*10, limit=10)
    self.templ['page'] = page
    self.templ['page_path'] = '/tag/' + tag

    return self.render('listing.html')


class AtomHandler(basehandler.BaseHandler):
  @basehandler.cached('application/atom+xml; charset=utf-8')
  def get(self):
    q = models.BlogPost.all().order('-updated')
    q.filter('is_deleted =', False)
    self.templ['posts'] = list(itertools.islice((x for x in q if x.published), 10))
    self.templ['updated'] = datetime.datetime.now().replace(second=0, microsecond=0)

    if not self.templ['devel'] and config.hubbub_hub_url:
      self.send_hubbub_ping(config.hubbub_hub_url)

    return self.render('atom.xml')

  def send_hubbub_ping(self, hub_url):
    data = urllib.urlencode({
        'hub.url': 'http://%s/feeds/atom.xml' % (config.host,),
        'hub.mode': 'publish',
    })
    response = urlfetch.fetch(hub_url, data, urlfetch.POST)


class PageContentHandler(basehandler.BaseHandler):
  @basehandler.cached()
  def get(self, page):
    page = models.Page.get_by_key_name(page)
    if not page:
      return self.fail(404)

    self.templ['page'] = page
    return self.render(os.path.join('pages', page.template))


app = webapp2.WSGIApplication([
    ('/', PostListingHandler),
    ('/feeds/atom.xml', AtomHandler),
    ('/page/(\d+)', PostListingHandler),
    ('/archive/', ArchiveIndexHandler),
    ('/archive/(\d+/\d+)/', ArchiveHandler),
    ('/tag/(\w+/?\d*)', TagsHandler),
    ('(/\d+/\d+/.*)', BlogPostHandler),
    ('(/.*)', PageContentHandler)
])

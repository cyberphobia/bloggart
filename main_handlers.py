import datetime

import webapp2

import basehandler
import config
import static


HTTP_DATE_FMT = "%a, %d %b %Y %H:%M:%S GMT"

if config.google_site_verification is not None:
  ROOT_ONLY_FILES = ['/robots.txt','/' + config.google_site_verification]
else:
  ROOT_ONLY_FILES = ['/robots.txt']


class StaticContentHandler(basehandler.BaseHandler):
  def output_content(self, content, serve=True):
    if content.content_type:
      self.response.headers['Content-Type'] = str(content.content_type)
    last_modified = content.last_modified.strftime(HTTP_DATE_FMT)
    self.response.headers['Last-Modified'] = last_modified
    self.response.headers['ETag'] = '"%s"' % (content.etag,)
    for header in content.headers:
      key, value = header.split(':', 1)
      self.response.headers[key] = value.strip()
    if serve:
      self.response.set_status(content.status)
      self.response.out.write(content.body)
    else:
      self.response.set_status(304)

  def get(self, path):
    if not path.startswith(config.url_prefix):
      if path not in ROOT_ONLY_FILES:
        self.error(404)
        self.render_to_response('404.html')
        return
    else:
      if config.url_prefix != '':
        path = path[len(config.url_prefix):]  # Strip off prefix
        if path in ROOT_ONLY_FILES:  # This lives at root
          self.error(404)
          self.render_to_response('404.html')
          return
    content = static.get(path)
    if not content:
      self.error(404)
      self.render_to_response('404.html')
      return

    serve = True
    if 'If-Modified-Since' in self.request.headers:
      try:
        last_seen = datetime.datetime.strptime(
            self.request.headers['If-Modified-Since'].split(';')[0],
            HTTP_DATE_FMT)
        if last_seen >= content.last_modified.replace(microsecond=0):
          serve = False
      except ValueError, e:
        import logging
        logging.error('StaticContentHandler in static.py, ValueError: %s',
                      self.request.headers['If-Modified-Since'])
    if 'If-None-Match' in self.request.headers:
      etags = [x.strip('" ')
               for x in self.request.headers['If-None-Match'].split(',')]
      if content.etag in etags:
        serve = False
    self.output_content(content, serve)


app = webapp2.WSGIApplication([
    ('(/.*)', StaticContentHandler)
])

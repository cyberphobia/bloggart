import datetime
import logging
import os

from django import forms
from google.appengine.api import users
from google.appengine.ext import deferred
from google.appengine.ext.db import djangoforms

import webapp2
import xsrfutil

import basehandler
import config
import markup
import models
import utils


def with_post(fun):
  def decorate(self, post_key=None):
    post = None
    if post_key:
      post = models.BlogPost.get_by_key_name(post_key)
      if not post:
        self.fail(404)
        return
    fun(self, post)
  return decorate


def with_page(fun):
  def decorate(self, page_key=None):
    page = None
    if page_key:
      page = models.Page.get_by_key_name(page_key)
      if not page:
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('404 :(\n' + page_key)
        #self.error(404)
        return
    fun(self, page)
  return decorate


class AdminHandler(basehandler.BaseHandler):
  def get(self):
    offset = int(self.request.get('start', 0))
    count = int(self.request.get('count', 20))
    posts = models.BlogPost.all().order('-published').fetch(count, offset)
    self.templ.update({
        'offset': offset,
        'count': count,
        'last_post': offset + len(posts) - 1,
        'prev_offset': max(0, offset - count),
        'next_offset': offset + count,
        'posts': posts,
    })
    self.render_to_response('admin/index.html')


class PostForm(djangoforms.ModelForm):
  title = forms.CharField(widget=forms.TextInput(attrs={'id':'name'}))
  body = forms.CharField(widget=forms.Textarea(attrs={
      'id': 'message',
      'rows': 10,
      'cols': 20}))
  body_markup = forms.ChoiceField(
    choices=[(k, v[0]) for k, v in markup.MARKUP_MAP.iteritems()])
  tags = forms.CharField(widget=forms.Textarea(attrs={'rows': 5, 'cols': 20}))
  is_draft = forms.BooleanField(required=False)

  class Meta:
    model = models.BlogPost
    fields = [ 'title', 'tags' ]


class PostHandler(basehandler.BaseHandler):
  @with_post
  def get(self, post):
    self.templ['form'] = PostForm(
        instance=post,
        initial={
          'body_markup': post and post.body_markup or config.default_markup,
          'body' : post and (post.draft or post.body)
        })
    self.render_to_response('admin/edit.html')

  @basehandler.csrf_protect
  @with_post
  def post(self, post):
    form = PostForm(data=self.request.POST, instance=post)
    if form.is_valid():
      post = form.save(commit=False)
      post = post.update(form.cleaned_data['body'], is_draft=form.cleaned_data['is_draft'])

      self.templ['draft'] = form.cleaned_data['is_draft']
      self.templ['post'] = post
      self.render_to_response('admin/published.html')
    else:
      self.templ['form'] = form
      self.render_to_response('admin/edit.html')


class DeleteHandler(basehandler.BaseHandler):
  @basehandler.csrf_protect
  @with_post
  def post(self, post):
    post.remove()
    self.render_to_response('admin/deleted.html')


class PreviewHandler(basehandler.BaseHandler):
  @with_post
  def get(self, post):
    # Temporary set a published date
    if not post.published:
      post.published = datetime.datetime.now()
    self.templ['post'] = post
    self.render_to_response('post.html')


class PageForm(djangoforms.ModelForm):
  path = forms.RegexField(
    widget=forms.TextInput(attrs={'id':'path'}),
    regex='(/[a-zA-Z0-9/]+)')
  title = forms.CharField(widget=forms.TextInput(attrs={'id':'title'}))
  template = forms.ChoiceField(choices=config.page_templates.items())
  body = forms.CharField(widget=forms.Textarea(attrs={
      'id':'body',
      'rows': 10,
      'cols': 20}))

  class Meta:
    model = models.Page
    fields = [ 'path', 'title', 'template', 'body' ]

  def clean_path(self):
    data = self._cleaned_data()['path']
    existing_page = models.Page.get_by_key_name(data)
    if not data and existing_page:
      raise forms.ValidationError("The given path already exists.")
    return data


class PageAdminHandler(basehandler.BaseHandler):
  def get(self):
    offset = int(self.request.get('start', 0))
    count = int(self.request.get('count', 20))
    pages = models.Page.all().order('-updated').fetch(count, offset)
    self.templ.update({
        'offset': offset,
        'count': count,
        'prev_offset': max(0, offset - count),
        'next_offset': offset + count,
        'last_page': offset + len(pages) - 1,
        'pages': pages,
    })
    self.render_to_response('admin/indexpage.html')


class PageHandler(basehandler.BaseHandler):

  @with_page
  def get(self, page):
    self.templ['form'] = PageForm(
        instance=page,
        initial={
          'path': page and page.path or '/',
        })
    self.render_to_response('admin/editpage.html')

  @basehandler.csrf_protect
  @with_page
  def post(self, page):
    form = None
    # if the path has been changed, create a new page
    if page and page.path != self.request.POST['path']:
      form = PageForm(data=self.request.POST, instance=None, initial={})
    else:
      form = PageForm(data=self.request.POST, instance=page, initial={})
    if form.is_valid():
      oldpath = form._cleaned_data()['path']
      if page:
        oldpath = page.path
      page = form.save(commit=False)
      page.updated = datetime.datetime.now()
      page.publish()
      # path edited, remove old stuff
      if page.path != oldpath:
        oldpage = models.Page.get_by_key_name(oldpath)
        oldpage.remove()
      self.templ['page'] = page
      self.render_to_response('admin/publishedpage.html')
    else:
      self.templ['form'] = form
      self.render_to_response('admin/editpage.html')


class PageDeleteHandler(basehandler.BaseHandler):
  @basehandler.csrf_protect
  @with_page
  def post(self, page):
    page.remove()
    self.render_to_response('admin/deletedpage.html')


class RegenerateHandler(basehandler.BaseHandler):
  @basehandler.csrf_protect
  def post(self):
    memcache.flush_all()
    self.render_to_response('admin/regenerating.html')


app = webapp2.WSGIApplication([
  ('/admin/', AdminHandler),
  ('/admin/posts', AdminHandler),
  ('/admin/pages', PageAdminHandler),
  ('/admin/newpost', PostHandler),
  ('/admin/regenerate', RegenerateHandler),
  ('/admin/post/delete(/.*)', DeleteHandler),
  ('/admin/post/preview(/.*)', PreviewHandler),
  ('/admin/post(/.*)', PostHandler),
  ('/admin/newpage', PageHandler),
  ('/admin/page/delete/(/.*)', PageDeleteHandler),
  ('/admin/page/(/.*)', PageHandler),
])

# Name of the blog
blog_name = 'Cyberphobia'

# Your name (used for copyright info)
author_name = 'Daniel F'

# (Optional) slogan
slogan = 'Your Random Security Blog.'

# The hostname this site will primarially serve off (used for Atom feeds)
host = 'blog.websec.at'

# Selects the theme to use. Theme names correspond to directories under
# the 'themes' directory, containing templates and static content.
theme = 'default'

# List of page templates
page_templates = {
  'Theme.html': 'Theme',
  'Simple.html': 'Simple',
}

# Defines the URL organization to use for blog postings. Valid substitutions:
#   slug - the identifier for the post, derived from the title
#   year - the year the post was published in
#   month - the month the post was published in
#   day - the day the post was published in
post_path_format = '/%(year)d/%(month)02d/%(slug)s'

# A nested list of sidebar menus, for convenience. If this isn't versatile
# enough, you can edit themes/default/base.html instead.
sidebars = [
  ('Blogroll', [
    '<a href="http://lcamtuf.blogspot.com/">lcamtuf</a>',
    '<a href="http://blog.cmpxchg8b.com/">Tavis Ormandy</a>',
    '<a href="http://www.schneier.com/blog/">Schneier on Security</a>',
    '<a href="http://blog.notdot.net/">Nick Johnson</a>',
    '<a href="http://www.thedailywtf.com/">The Daily WTF</a>',
    '<a href="http://xkcd.com/">XKCD</a>',
  ]),
]

# Number of entries per page in indexes.
posts_per_page = 10

# The mime type to serve HTML files as.
html_mime_type = "text/html; charset=utf-8"

# To use disqus for comments, set this to the 'short name' of the disqus forum
# created for the purpose.
disqus_forum = None

# Length (in words) of summaries, by default
summary_length = 200

# If you want to use Google Analytics, enter your 'web property id' here
analytics_id = None

# If you want to use PubSubHubbub, supply the hub URL to use here.
hubbub_hub_url = 'http://pubsubhubbub.appspot.com/'

# Default markup language for entry bodies (defaults to html).
default_markup = 'html'

# Syntax highlighting style for RestructuredText and Markdown,
# one of 'manni', 'perldoc', 'borland', 'colorful', 'default', 'murphy',
# 'vs', 'trac', 'tango', 'fruity', 'autumn', 'bw', 'emacs', 'pastie',
# 'friendly', 'native'.
highlighting_style = 'friendly'

# Defines where the user is defined in the rel="me" of your pages.
# This allows you to expand on your social graph.
rel_me = None

# For use a feed proxy like feedburne.google.com
feed_proxy = None

# To format the date of your post.
# http://docs.djangoproject.com/en/1.1/ref/templates/builtins/#now
date_format = "%d %B, %Y"

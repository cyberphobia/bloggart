import re
import unicodedata

import config


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

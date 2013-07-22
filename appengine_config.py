import os
import sys

from google.appengine.api import memcache

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

# Check if the version is updated, and if yes, flush memcache.
# Note: If memcache is flushed outside of this function, this causes it to be
# flushed again the next time a page is visited. That's not a big deal though.
if memcache.get("static-version") == os.environ["CURRENT_VERSION_ID"]:
  pass
else:
  memcache.flush_all()
  memcache.set(key="static-version", value=os.environ["CURRENT_VERSION_ID"])

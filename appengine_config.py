import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

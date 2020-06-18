#!/usr/bin/env python
#import gmusicapi
from gmusicapi.clients import Mobileclient
from config import *

import logging
from logging import debug, info, warning, error

logging.basicConfig(level=logging.DEBUG)

api = Mobileclient()
if not api.oauth_login(gmusic_client_id):
    print(f"oauth: {api.perform_oauth()}")
else:
    print(f"already logged in (you may remove ~.local/share/gmusicapi/mobileclient.cred to relogin, or modify this script to handle logoffs more correctly)")


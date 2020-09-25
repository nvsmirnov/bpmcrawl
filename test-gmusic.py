# this file contains experiments

# {'album': 'Tuesday Night Music Club (Deluxe Edition)',
#  'albumArtRef': [{'aspectRatio': '1',
#                   'autogen': False,
#                   'kind': 'sj#imageRef',
#                   'url': 'http://lh3.googleusercontent.com/D9SpAUs2jv5kMsmywhfcHmbKd9OkUZYK-aSAW2-nqjBLekFlrl3PcYoZ63oMFamxaGV2lZBM'}],
#  'albumArtist': 'Sheryl Crow',
#  'albumAvailableForPurchase': False,
#  'albumId': 'Bak44famcemjjulytsnmvswt4vu',
#  'artist': 'Sheryl Crow',
#  'artistId': ['Adkql6r7fypssykmftatdab542a'],
#  'composer': '',
#  'discNumber': 1,
#  'durationMillis': '190000',
#  'estimatedSize': '7601669',
#  'explicitType': '2',
#  'genre': 'Country',
#  'kind': 'sj#track',
#  'nid': 'Tc6giaoficqwnkxt3vr5bmpmndy',
#  'storeId': 'Tc6giaoficqwnkxt3vr5bmpmndy',
#  'title': 'Strong Enough',
#  'trackAvailableForPurchase': True,
#  'trackAvailableForSubscription': True,
#  'trackNumber': 3,
#  'trackType': '7',
#  'year': 1993}



# Station API Sample:
# {'byline': 'By Google Play Music',
#  'clientId': 'e77f862d-80b8-476e-b8d9-ef878b72b8d1',
#  'compositeArtRefs': [{'aspectRatio': '1',
#                        'kind': 'sj#imageRef',
#                        'url': 'http://lh3.googleusercontent.com/TQnYELBaKhzAy7-Vojd-EjPMBGWUt_oME-iE-gK23n3WEr0rMddnJpp-SA'},
#                       {'aspectRatio': '2',
#                        'kind': 'sj#imageRef',
#                        'url': 'http://lh3.googleusercontent.com/Eel3EqYIwV0N637WugtEGj9YUxaWxHKcgl4BhLVWeJwDYBs_TNNIpbSRsw'}],
#  'deleted': False,
#  'id': '9e33f458-9337-31bf-beef-cf7d6304681e',
#  'imageUrls': [{'aspectRatio': '1',
#                 'autogen': False,
#                 'kind': 'sj#imageRef',
#                 'url': 'http://lh3.googleusercontent.com/AMpadY2-zl_gxew7rGHfeEBlHq9RV-P5S9Ih_yKwIZgVhwahXRjVntZeFiRHcHA_YI8jOCfH'},
#                {'aspectRatio': '1',
#                 'autogen': False,
#                 'kind': 'sj#imageRef',
#                 'url': 'http://lh3.googleusercontent.com/tu-1HjrRaptf1kP51HGzac3eH1Yzi5vpycpaoHmrj_WxXrvfw43PFgKbpBFMtftNzaEpSsbk'}],
#  'inLibrary': False,
#  'kind': 'sj#radioStation',
#  'lastModifiedTimestamp': '1592421058708000',
#  'name': 'Путь Рок-н-Ролла',
#  'recentTimestamp': '1592421058381000',
#  'seed': {'curatedStationId': 'Lfx5b7jpzzbc2jyv76h45j7jqo4',
#           'kind': 'sj#radioSeed',
#           'seedType': '9'},
#  'skipEventHistory': []}

import logging
from logging import debug, info, warning, error

from calc_bpm import *

logging.basicConfig(level=logging.DEBUG)

h = calc_bpm_histogram("sample.mp3")
#h = {'bpm': 89.91, 'histogram': {86: 15.31, 89: 52.48, 91: 33.01}}
info(f"{h['bpm']}, histogram: {[(x,h['histogram'][x]) for x in sorted(h['histogram'],key=lambda bpm: h['histogram'][bpm], reverse=True)]}")

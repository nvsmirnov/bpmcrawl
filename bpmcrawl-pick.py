#!/usr/bin/env python

# TODO: добавлять найденное в какой-то playlist (и создавать его если его ещё нет)

import sys
import os
import urllib.parse
import tempfile
import requests

from gmusicapi.clients import Mobileclient

from sqlitedict import SqliteDict

import logging
from logging import debug, info, warning, error

from exceptions import *
from whoami import *
from config import *
from calc_bpm import *

api = None

def get_scaled_good_bpm(bpm, good_bpm):
    """
    Вернёт значение bpm, приведённое с учётом множителя, если bpm попадает в good_bpm (формат см. в get_good_bpms)
    None если не попало
    """
    for mult in good_bpm["mult"]:
        if bpm >= mult*good_bpm["min"] and bpm <= mult*good_bpm["max"]:
            return bpm/mult
    return None

def get_avg_bpm(histogram: dict):
    """Вернёт средний bpm из histogram с учётом доли каждого значения
    histogram должен содержать приведённые значения (т.е. должен быть результатом выполнения get_good_bpms)"""
    sum = 0
    sum_shares = 0
    for bpm in histogram:
        sum += bpm * histogram[bpm]
        sum_shares += histogram[bpm]
    return sum/sum_shares


def get_good_bpms(histogram: dict, good_bpm, min_share=0.9):
    """
    Если доля "хороших" bpm >= min_share, то вернёт dict:
        {bpm1: share1, bpm2: share2}
        Результат будет состоять только из "хороших" bpm, он будет отсортирован по убыванию share
        bpm будут приведены с учётом мультипликатора из good_bpm
        Вернёт None, если гистограмма не даёт уверенного результата или доля "хороших" bpm < min_share
    "хороший" bpm - такой, который попадает в интервал good_bpm
    Параметры:
        histogram: {bpm1: share1, bpm2: share2, ...}
        good_bpm: {"min": bpm_min, "max": bpm_max, "mult": [multiplier1, m2, ...]}, напр., для 180+-4 (90+-2) это {176,184, [1, 0.5]}
        min_share: минимальная суммарная доля всех подходящих bpm
    """
    sum_good_share = 0
    good_bpms = {}
    # you may not need to do this, it's only for clear debug printing
    histogram = OrderedDict(sorted(histogram.items(), key=lambda k: k[1], reverse=True))
    for bpm in histogram:
        bpm_scaled = get_scaled_good_bpm(bpm,good_bpm)
        if bpm_scaled:
            sum_good_share += histogram[bpm]
            if bpm_scaled not in good_bpms:
                good_bpms[bpm_scaled] = 0
            good_bpms[bpm_scaled] += histogram[bpm]

    good_bpms = OrderedDict(sorted(good_bpms.items(), key=lambda k: k[1], reverse=True))
    #debug(f"{whoami()}: orig={histogram}")
    #debug(f"{whoami()}: good={good_bpms}")
    if sum_good_share < min_share:
        debug(f"{whoami()}: returning None")
        return None

    debug(f"{whoami()}: returning {good_bpms}")
    return good_bpms


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    logging.getLogger("sqlitedict").setLevel(logging.ERROR)

    oldloglevel = logging.getLogger().level
    logging.getLogger().setLevel(logging.ERROR)
    api = Mobileclient(debug_logging=False)
    logging.getLogger("gmusicapi.Mobileclient1").setLevel(logging.WARNING)
    if not api.oauth_login(gmusic_client_id):
        print(f"Please login to Google Music first (run gmusic-login.py)")
        sys.exit(1)
    logging.getLogger().setLevel(oldloglevel)
    debug("logged in")


    logging.getLogger().setLevel(logging.INFO)
    with SqliteDict(tracks_histogram_db, autocommit=True) as cache:
        for track_id in cache:
            good_bpms = get_good_bpms(cache[track_id], {"min": 176, "max": 184, "mult": [1, 0.5]})
            if good_bpms:
                info(f"{track_id}: avg={round(get_avg_bpm(good_bpms),2)}, {good_bpms}")

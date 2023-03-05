#!/usr/bin/env python
# encoding: utf-8

from collections import OrderedDict

from essentia import log
log.infoActive = False
log.warningActive = False
from essentia.standard import *

from logging import debug, info, warning, error

from exceptions import *

def calc_file_bpm_histogram(filename):
    """Analyze filename, get average BPM and calculate DPB histogram
    :returns dict: { bpm(int): bpm_share(float) }
    :raises ExcBpmCrawlGeneric on error
    """

    bpm = None
    beats_intervals = None
    beats = None
    beats_confidence = None
    try:
        audio = MonoLoader(filename=filename)()
        rhythm_extractor = RhythmExtractor2013(method="multifeature")
        (bpm, beats, beats_confidence, _, beats_intervals) = rhythm_extractor(audio)
    except Exception as e:
        raise ExBpmCrawlGeneric(str(e))
        #if re.search('Could not find stream information', str(e)):
        #    raise ExcBpmCrawlGeneric(str(e))
        #else:
        #    print( "Failed on '%s': %s(%s)" % (filename, type(e).__name__, str(e)) )

    if bpm == None:
        raise ExcBpmCrawlGeneric(f"Failed to calculate BPM for {filename}")
    debug(f"Analyzed {filename}, got average bpm: {bpm}")

    peak1_bpm, peak1_weight, peak1_spread, peak2_bpm, peak2_weight, peak2_spread, histogram = BpmHistogramDescriptors()(beats_intervals)
    #debug(histogram)

    hist_hash = {}
    hist_bpm = 0
    while hist_bpm < len(histogram):
        hval = round(float(histogram[hist_bpm]), 2) # float is necessary, because there is non-json-serializable float32 in histogram
        if hval > 0:
            hist_hash[hist_bpm] = hval
        hist_bpm += 1
    #debug(hist_hash)
    return hist_hash


__all__ = ["calc_file_bpm_histogram"]

# from collections import OrderedDict

# NB on using essentia.standard:
#   it is ok to have unresolved names from essentia.standard because they are created runtime
#   so if you unsure (maybe something changed with a time passed),
#   you may try to import and call them in python console
import essentia
import essentia.standard

from backend.log import *
from backend.exceptions import *

essentia.log.infoActive = False
essentia.log.warningActive = False


def calc_file_bpm_histogram(filename):
    """Analyze filename, get average BPM and calculate DPB histogram
    :returns dict: { bpm(int): bpm_share(float) }
    :raises ExcBpmcrawlGeneric on error
    """

    bpm = None
    beats_intervals = None
    beats = None
    beats_confidence = None
    try:
        audio = essentia.standard
        audio = essentia.standard.MonoLoader(filename=filename)()
        rhythm_extractor = essentia.standard.RhythmExtractor2013(method="multifeature")
        (bpm, beats, beats_confidence, _, beats_intervals) = rhythm_extractor(audio)
    except Exception as e:
        raise ExBpmcrawlGeneric(str(e))
        #if re.search('Could not find stream information', str(e)):
        #    raise ExcBpmCrawlGeneric(str(e))
        #else:
        #    print( "Failed on '%s': %s(%s)" % (filename, type(e).__name__, str(e)) )

    if bpm is None:
        raise ExBpmcrawlGeneric(f"Failed to calculate BPM for {filename}")
    debug(f"Analyzed {filename}, got average bpm: {bpm}")

    (
        peak1_bpm, peak1_weight, peak1_spread, peak2_bpm, peak2_weight, peak2_spread, histogram
    ) = essentia.standard.BpmHistogramDescriptors()(beats_intervals)
    #debug(histogram)

    hist_hash = {}
    hist_bpm = 0
    while hist_bpm < len(histogram):
        hval = round(float(histogram[hist_bpm]), 2)  # float is necessary, because there is non-json-serializable float32 in histogram
        if hval > 0:
            hist_hash[hist_bpm] = hval
        hist_bpm += 1
    #debug(hist_hash)
    return hist_hash


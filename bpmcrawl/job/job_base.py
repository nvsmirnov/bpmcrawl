from bpmcrawl.utils import *
from bpmcrawl.exceptions import *

class BpmcrawlJob(object, WhoamiObject):
    kind = None
    jobdef = None

    @staticmethod
    def create(self, kind=None, json=None):
        if kind == "calc_bpm":
            return BpmcrawlJobCalcBpm(json)
        raise ExBpmcrawlGeneric(f"{self.whoami()}: unknown kind='{kind}'")

    def __init__(self, json=None):
        self.jobdef = None
        if json is not None:
            self.from_json(json)

    def to_json(self):
        return self.jobdef

    def from_json(self, json):
        try:
            self.jobdef["user"] = json["user"]
            self.jobdef["service"] = json["service"]
            self.jobdef["track_id"] = json["track_id"]
        except KeyError as e:
            raise ExBpmcrawlGeneric(f"{self.whoami()}: required value is absent in json: {e}")

    def from_json_internal(self, json):
        # it is wrapped by from_json catching KeyError
        raise ExBpmcrawlGeneric(f"{self.whoami()}: tried to use base job class")


class BpmcrawlJobCalcBpm(BpmcrawlJob):

    def from_json_internal(self, json):
        self.jobdef["user"] = json["user"]
        self.jobdef["service"] = json["service"]
        self.jobdef["track_id"] = json["track_id"]

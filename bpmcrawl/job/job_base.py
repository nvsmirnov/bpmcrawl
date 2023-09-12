__all__ = [
    'BpmcrawlJob', 'BpmcrawlJobCalcBpm',
]

from bpmcrawl.utils import *
from bpmcrawl.exceptions import *

import pymongo

import bson
import uuid


class BpmcrawlJob(WhoamiObject):
    db = None
    job = None
    worker_id = None

    @classmethod
    def create(cls, db, job):
        if db is None:
            raise ExBpmcrawlGeneric(f"{cls.whoami()}: internal error: db is mandatory")
        if job['kind'] == "calc_bpm":
            return BpmcrawlJobCalcBpm(db, job)
        raise ExBpmcrawlGeneric(f"{whoami()}: unsupported job kind='{job['kind']}'")

    def __init__(self, db, job: dict):
        self.db = db
        self.job = job
        self.worker_id = None
        self.from_json(job['def'])

        if 'job_id' not in job:
            # this is new job, generate id and save it to DB
            self.new_job()

    def __str__(self):
        if self.job is None:
            return f"{self.__class__.__name__}(empty)"
        if self.worker_id is None:
            return f"{self.__class__.__name__}(job=({self.job['job_id']}, {self.job['job_uri']}))"
        return f"{self.__class__.__name__}(worker={self.worker_id}, job=({self.job['job_id']}, {self.job['job_uri']}))"

    def new_job(self):
        # add default and mandatory fields to job and save it to db
        self.job['job_id'] = str(uuid.uuid4())
        self.job['locked'] = self.job['job_id']
        self.job['job_uri'] = self.get_job_uri()
        self.job['finished'] = 0
        self.job['time_took'] = 0
        self.job['timestamp_started'] = None

        try:
            self.db.jobs.insert_one(self.job)
        except pymongo.errors.DuplicateKeyError as e:
            try:
                details = e.details['keyValue']
            except KeyError:
                details = str(e)
            raise ExBpmcrawlJobAlreadyExist(f"Job already exists: {details}")

    def to_json(self):
        return self.job

    def from_json(self, json):
        try:
            self.from_json_internal(json)
        except KeyError as e:
            raise ExBpmcrawlGeneric(f"{self.whoami()}: required value is absent in json: {e}")

    def from_json_internal(self, json):
        # it is wrapped by from_json catching KeyError
        raise ExBpmcrawlGeneric(f"{self.whoami()}: tried to use base abstract job class's method")

    def get_job_uri(self):
        raise ExBpmcrawlGeneric(f"{self.whoami()}: tried to use base abstract job class's method")

    def pickup(self):
        if self.worker_id is None:
            self.worker_id = str(uuid.uuid4())
        result = self.db.jobs.find_one_and_update(
            {
                "job_id": self.job["job_id"],
                "worker_id": None,
            },
            {"$set": {
                "worker_id": self.worker_id,
            }},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        if result is None:
            raise ExBpmcrawlJobPickupFailed(
                f"Failed to pick up job {self.job['job_id']}({self.job['job_uri']}): either it was deleted, or picked up by other worker")
        if not result['worker_id']:
            raise ExBpmcrawlJobPickupFailed(
                f"Internal error: Failed to pick up job {self.job['job_id']}({self.job['job_uri']}): expected to get worker_id but got nothing")
        if result['worker_id'] != self.worker_id:
            raise ExBpmcrawlJobPickupFailed(
                f"Failed to pick up job {self.job['job_id']}({self.job['job_uri']}): job was picked up by other worker ({result['worker_id']})")

    def finish(self):
        raise ExBpmcrawlGeneric(f"{self.whoami()}: internal error: this method is not implemented yet")

    def run(self):
        raise ExBpmcrawlGeneric(f"{self.whoami()}: tried to use base abstract job class's method")


class BpmcrawlJobCalcBpm(BpmcrawlJob):

    def from_json_internal(self, job_def):
        # just check that all fields are in place
        _ = job_def["user"]
        _ = job_def["service"]
        _ = job_def["track_id"]

    def get_job_uri(self):
        return \
                f"{self.job['kind']}/{self.job['def']['user']}" \
                + f"/{self.job['def']['service']}/{self.job['def']['track_id']}"
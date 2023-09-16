__all__ = [
    'BpmcrawlJob', 'BpmcrawlJobCalcBpm',
]

from backend.whoami import *
from backend.exceptions import *

import pymongo

import uuid


class BpmcrawlJob(WhoamiObject):
    """
    Base class for a job.
    Job objects may be in two states: job (description) and worker (job which has picked up task for working on it).
    Job becomes worker upon calling of pickup()
    In this base abstract BpmcrawlJob class you should use only create() method,
    which will return object of appropriate real job class.
    """
    db = None
    job = None
    worker_id = None

    @classmethod
    def create(cls, db, job):
        """Creates and returns object of appropriate class based on a 'job' paramter."""
        if db is None:
            raise ExBpmcrawlGeneric(f"{cls.whoami()}: internal error: db is mandatory")
        if job['kind'] == "calc_bpm":
            return BpmcrawlJobCalcBpm(db, job)
        raise ExBpmcrawlGeneric(f"{whoami()}: unsupported job kind='{job['kind']}'")

    def __init__(self, db, job: dict):
        self.db = db
        self.job = job
        self.worker_id = None
        self.from_json_internal(job['def'])

        if 'job_id' not in job:
            # this is new job, generate id and save it to DB
            self.new_job()

    def __str__(self):
        if self.job is None:
            return f"job(kind={self.job['kind']}, empty)"
        if self.worker_id is None:
            return f"job(kind={self.job['kind']}, {self.job['job_uri']})"
        return f"worker(kind={self.job['kind']}, {self.job['job_uri']})"

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

    def from_json_internal(self, json):
        """
        Internal method to wrap actual child's class from_json() with catching KeyErrors
        :param json: see from_json
        :return: nothing
        """
        try:
            self.from_json(json)
        except KeyError as e:
            raise ExBpmcrawlGeneric(f"{self.whoami()}: required value is absent in json: {e}")

    def from_json(self, json):
        """
        Redefine this method to initialize job from it's json
        This method is wrapped by from_json_internal catching KeyError exceptions.
        So in child's class from_json_internal you may just use some like this:
            _ = json['field']
        And it will check if this field is in place.
        :param json: job description (how it is found in db.jobs object's 'def' field.
        :return: nothing
        """
        # it is wrapped by from_json catching KeyError
        raise ExBpmcrawlGeneric(f"{self.whoami()}: tried to use base abstract job class's method")

    def get_job_uri(self):
        """
        Generates job uri appropriate for saving it to db.
        Job uri must be unique among all jobs, but should be equal for equal jobs.
        It is used also to prevent equal jobs from creating, i.e. these jobs should have same uris:
            - calculate bpm for the same track of same music service
            - crawl on user's playlist named X
        :return: job_uri string
        """
        raise ExBpmcrawlGeneric(f"{self.whoami()}: tried to use base abstract job class's method")

    def pickup(self):
        """
        Pick up job (become a worker) and lock the job in the db for this worker.
        :return: Nothing
        """
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
        """
        Internal method. Called when job finished.
        Marks it as finished in the db and save job's statistics to db.
        """
        raise ExBpmcrawlGeneric(f"{self.whoami()}: internal error: this method is not implemented yet")

    def run(self):
        """
        Call to run a worker process for this job.
        The worker must be created first with call of pickup().
        Then, it calls run_internal(), which must be defined in child class.
        After irun_internal() finishes, this method calls finish()
        """
        self.run_internal()
        self.finish()

    def heartbeat(self):
        """
        Update job's object in db - set last activity time.
        It needed to determine that the job becomes stale.
        You must call it from run_internal() frequent enough to be sure that scheduler will not decide the job is stale.
        :return:
        """
        raise ExBpmcrawlGeneric(f"{self.whoami()}: internal error: this method is not implemented yet")

    def run_internal(self):
        """
        The worker's real task is performed by this method.
        This method must be redefined in child class.
        If job may run for a long time, it must sometimes call heartbeat(), ensuring to call it more frequently
        than scheduler may decide that job is stale.
        :return: Nothing
        """
        raise ExBpmcrawlGeneric(f"{self.whoami()}: tried to use base abstract job class's method")


class BpmcrawlJobCalcBpm(BpmcrawlJob):

    def from_json(self, job_def):
        # just check that all fields are in place
        _ = job_def["user"]
        _ = job_def["service"]
        _ = job_def["track_id"]

    def get_job_uri(self):
        return \
                f"{self.job['kind']}/{self.job['def']['user']}" \
                + f"/{self.job['def']['service']}/{self.job['def']['track_id']}"
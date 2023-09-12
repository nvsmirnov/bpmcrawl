from bpmcrawl.exceptions import *
from bpmcrawl.job import *
import bpmcrawl.db
import logging

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.ERROR)

    db = bpmcrawl.db.connect()
    try:
        job_obj = BpmcrawlJob.create(db, {
            "kind": "calc_bpm",
            "def": {
                "user": "nsmirnov@gmail.com",
                "service": "yandexmusic",
                "track_id": "46650050",
            }
        })
        print(f"created job {job_obj}")
    except ExBpmcrawlGeneric as e:
        print(f"Didn't create new job: {e}")
    job = db.jobs.find_one(filter={'worker_id': None, 'def.service': 'yandexmusic'}, projection={'_id': False})
    if job is not None:
        worker = BpmcrawlJob.create(db, job)
        print(f"found job: {worker}")
        worker.pickup()
        print(f"picked up job {worker}")
    else:
        print(f"Didn't find any job to pick up")

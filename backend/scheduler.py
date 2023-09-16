from backend.log import *
from backend.exceptions import *
from backend.job import *
import backend.db

if __name__ == '__main__':
    # logger.setLevel(DEBUGALL)

    db = backend.db.connect()
    try:
        job_obj = BpmcrawlJob.create(db, {
            "kind": "calc_bpm",
            "def": {
                "user": "nsmirnov@gmail.com",
                "service": "yandexmusic",
                "track_id": "46650050",
            }
        })
        info(f"created job {job_obj}")
    except ExBpmcrawlGeneric as e:
        info(f"Didn't create new job: {e}")
    job = db.jobs.find_one(filter={'worker_id': None, 'def.service': 'yandexmusic'}, projection={'_id': False})
    if job is not None:
        worker = BpmcrawlJob.create(db, job)
        info(f"found job: {worker}")
        worker.pickup()
        info(f"picked up job {worker}")
    else:
        info(f"Didn't find any job to pick up")

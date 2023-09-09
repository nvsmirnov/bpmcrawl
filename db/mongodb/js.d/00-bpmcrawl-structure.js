//use bpmcrawl;

db.services.createIndexes([{"name":1}],{unique:true});
db.services.insertMany([
    { "name": "sampleservice",  "enabled": false, },
    { "name": "gmusic",         "enabled": false, },
    { "name": "spotify",        "enabled": false, },
    { "name": "yandexmusic",    "enabled": true,  },
]);

db.users.createIndexes([{"email":1, "user":1}], {"unique":true});
db.users.insertMany([
    {
        "user":  "sample@sample.nonexistent",
        "email": "sample@sample.nonexistent",
        "displayName": "Sample User",
        "enabled": false,
        "services": {
            "yandexmusic": {
                "token": "x",
            },
        },
    },
]);

db.playlists.createIndexes([{"playlist_uri":1}], {"unique":true});
db.playlists.createIndexes([{"service":1}, {"service_playlist_id":1}], {"unique":false});
db.playlists.insertMany([
// there may be some special per-service playlist ids, like these:
//   PLOD (play list of the day)
//   LIKED (liked tracks)
//   and others, depending on music service
    {
        "name": "Sample Playlist",
        "user": "sample@sample.nonexistent",
        "service": "sampleservice",
        "service_playlist_id": "sample_playlist_id", // id in the service
        "playlist_uri": "sampleservice/sample@sample.nonexistent/sample_playlist_id",
    },
]);

db.histograms.createIndexes([{"track_uri":1}], {"unique":true});
db.histograms.createIndexes([{"service":1}, {"service_track_id":1}], {"unique":false});
db.histograms.insertMany([
    {
        // it is ok to have sample track record in real database
        "track_uri": "sampleservice/sample_track_id", // track_uri is "our" unique track id consisting of service name and service's track id
        "service": "sampleservice",
        "service_track_id": "sample_track_id", // track id in the service
        "histogram": { 90: 0.9, 181: 0.1, },
        "from_playlists": {
            "sampleservice/sample@sample.nonexistent/sample_playlist_id": 1, // playlist ids are service-specific - service_playlist_id
        },
        "timestamp_last_job_scheduled": 0, // when last update job was scheduled
        "timestamp_last_job_finished": 0, // when last update job finished
    },
]);

db.targets.createIndexes([{"target_uri":1}], {"unique": true});
db.targets.insertMany([
    {
        "user": "sample@sample.nonexistent",
        "service": "sampleservice",
        "target": "bpmcrawl.180",
        "target_uri": "sample@sample.nonexistent/sampleservice/ym.bpmcrawl.180.ng", // just for uniqueness
        "bpms": { "min": 176, "max": 182 },
        "sources": {
            "playlists": {
                "PLOD": 1,
                "LIKED": 1,
                "sample_playlist": 1,
            },
            "artists": {
            },
            "albums": {
            },
            "tracks": {
            },
        },
        "timestamp_last_job_scheduled": 0, // when last update job was scheduled
        "timestamp_last_job_finished": 0, // when last update job finished
    },
]);

db.jobs.createIndexes([{"job_id":1, "locked":1}], {"unique": true});
// the logic of job pick-up:
// the process who wants to puck up job to work on it, must first update job's document
// and set "locked" field to value of "job_id" field.
// there is unique constraint on "locked" field, so only first attempt will be successful
// who updated field successfully, may and must proceed to work on job
// who got exception on unique constraint - should go for another job
db.jobs.insertMany([
    {
        "job_id": "sample_job_1", // better when name will be made of all job's parameters combined, it will prevent same job creation
        "locked": "",
        "finished": false,
        "time_took": 0, // seconds - set after job finish
        "timestamp_updated": "", // для длительных заданий периодически ставить timestamp, UTC unixtime
        "user":  "sample@sample.nonexistent",
        "service": "sampleservice",
        // job_kind:
        //   scan_playlist:
        //     scan playlist, find tracks without calculated histograms,
        //     and create other jobs of calc_bpm kind
        //   calc_bpm:
        //     calculate bpm for specified track, and save histogram to database
        //   pick_tracks:
        //     per-user, per-target job: pick jobs from histograms db that are still not in target
        //     and put them to target playlist
        "job_kind": "",
    },
]);

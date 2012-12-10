"""
The AVScheduler has two primary functions.

1. It is the job producer.

2. It makes sure processes are running to consume the job queue.

CONSUMERS:
 - TVDB Search and Update
 - NZB Search
 - NZB Fetch
 - NZB Stitch
 - Repair & Extract

JOB_TYPES:
 - Update TVDB Info
 - State Transition
 - NZB Search
 - Download (has sub jobs)
 - Stitch (has sub jobs)
 - Repair
 - Extract

"""
#import logging
import time, beanstalkc
from core.storage import get_session, Episode, ESTATE_SEARCHING

__author__ = 'trey'

JOB_UPDATE_DB = 'update_tvdb'


class NNTPConnectionPool(object):
    def __init__(self, max_connections=10, idle=30):
        pass


class AVJobBase(object):
    def __init__(self):
        self.retries = 0


class AVJobPool(object):
    pass


class AVScheduler(object):
    def __init__(self, sleep_time=60):
        self.active = True
        self.sleep_time = sleep_time
        self.run()

    def run(self):
        session = get_session()
        beanstalk = beanstalkc.Connection(host='localhost', port=11300)

        while self.active:
            # Look for episodes that we want, that should be or become available shortly and set to searching.
            waiting_episodes = Episode.get_waiting(session)
            for ep in waiting_episodes:
                print 'Set to {} :: {}'.format(ESTATE_SEARCHING, unicode(ep))
                ep.state = ESTATE_SEARCHING
            session.commit()

            print beanstalk.peek_ready()

            # The basic way this works is that we will peek at various job queues and make sure
            # spawn subprocesses to manage those queues.

            # Any episodes that require searching, spawn a process to search NZB repository.
            # SPAWN SEARCH PROCESS

            # Any episode that has a candidate NZB, spawn a download process.
            # SPAWN DOWNLOAD PROCESS

            # Any episode that has completed download, begin stitching of file.
            # SPAWN FILE STITCHER/REPAIR/UNCOMPRESS

            # Any episode that is complete but for post processing...
            # SPAWN post processor.

            time.sleep(self.sleep_time)
        beanstalk.close()














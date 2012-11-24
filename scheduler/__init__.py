"""
The scheduler will look for shows to queue for the downloader.

STATES:
Wanted: Show is desired, but awaiting air date.
Searching: Show has aired, searching for NZB.
Fetching: NZB has been found, waiting on downloader to complete.
Processing: Show is being processed (stitched, named, copied).
Skipped:
Ignored:
Exception: One of the steps failed without a recovery option.

0. Update TVDB show information.
1. Look for episodes on our want list that have aired and switch to searching.
2. Search wanted episodes that should be available and filter by preferences and weights.
3. If any shows match add them to the queue.
"""
import logging

__author__ = 'trey'

ESTATE_WANTED = 'wanted'
ESTATE_SEARCHING = 'searching'
ESTATE_FETCHING = 'fetching'
ESTATE_PROCESSING = 'processing'
ESTATE_SKIPPED = 'skipped'
ESTATE_IGNORED = 'ignored'
ESTATE_EXCEPTION = 'exception'

EPISODE_STATES = (ESTATE_WANTED, ESTATE_SEARCHING, ESTATE_FETCHING, ESTATE_PROCESSING,
                  ESTATE_SKIPPED, ESTATE_IGNORED, ESTATE_EXCEPTION)
DEFAULT_STATE = ESTATE_IGNORED

class AVScheduler(object):
    def __init__(self):
        self.log = logging.getLogger()
        self.run()

    def run(self):
        self.log.info('Scheduler Starting')


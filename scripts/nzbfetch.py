#!/usr/bin/python
import socket
import os, logging
from functools import partial
from math import ceil
from StringIO import StringIO
from Queue import Empty, Queue
from threading import Thread, current_thread, Event
from blessings import Terminal
import time
from lib.nzb import read_segment, check_crc, InvalidSegmentException
from lib.pynzb import nzb_parser
from lib.utils import bytes2human
from lib.asyncnntp import NNTP
from scripts import BaseScript


class RetryJobException(Exception):
    pass


class TooManyRetriesException(Exception):
    pass


class Segment(object):
    id = None
    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id.__eq__(other.id)

    def __cmp__(self, other):
        return self.id.__cmp__(other.id)

    def __repr__(self):
        return self.id


class NZBSegment(Segment):
    def __init__(self, segment=None):
        self.id = segment.message_id
        self.segment = segment

    def __getattr__(self, item):
        return getattr(self.segment, item)


class FileSegment(Segment):
    def __init__(self, message_id=None):
        self.id = message_id


class TaskMaster(object):
    def __init__(self, job_queue, worker, max_threads=1, status=None, *a, **kw):
        self.job_queue = job_queue
        self.worker = worker
        self.max_threads = max_threads
        self.threads = {}
        self.status = status
        self.working = True
        self.args = a
        self.kwargs = kw

    def __call__(self):
        empty_count = 0
        max_empty_count = 5
        # We are either working or we have threads to manage.
        while self.working or len(self.threads) > 0:
            # Spawn threads!
            if self.working is True:
                while len(self.threads) < self.max_threads and not self.job_queue.empty():
                    target = self.worker(self.job_queue, self.status, *self.args, **self.kwargs)
                    thread = Thread(target=target)
                    self.threads[thread] = target
                    thread.start()

            # Manage existing threads
            for thread, worker in self.threads.items():
                if self.working is False:
                    # We are trying to destroy the threads.
                    worker.stop()
                if not thread.is_alive():
                    self.threads.pop(thread)
                    self.status.set()

            # Check if the queue is empty a few times, give it a chance to fill.
            if self.job_queue.empty():
                if empty_count >= max_empty_count:
                    self.working = False
                empty_count += 1

            time.sleep(0.1)
        print 'Master Exit'

    def stop(self):
        self.working = False


class PoolWorker(object):
    STATE_SKIP = 'SKIP'
    STATE_RETRY = 'RETRY'
    STATE_IDLE = 'IDLE'
    STATE_EXIT = 'EXIT'

    def __init__(self, job_queue, status_event=None, *a, **kw):
        self.status = status_event
        self.status_update(state=FetchWorker.STATE_IDLE)
        self.jobs = job_queue
        self.args = a
        self.kwargs = kw
        self.running = True

    def __call__(self):
        self.worker_startup()
        while self.running:
            try:
                job = self.jobs.get(timeout=1)
            except Empty:
                continue
            try:
                job.attempt()
                self.execute(job)  # Do work here.
            except RetryJobException:
                self.status_update(state=PoolWorker.STATE_RETRY)
                self.jobs.put(job)
            except TooManyRetriesException:
                self.status_update(state=PoolWorker.STATE_SKIP)
                continue
        self.worker_shutdown()
        self.status_update(state=PoolWorker.STATE_EXIT)

    def stop(self):
        self.running = False

    def status_update(self, **kw):
        self.status_data = kw
        self.status.set()

    def worker_startup(self):
        raise NotImplementedError()

    def worker_shutdown(self):
        raise NotImplementedError()

    def execute(self, job):
        raise NotImplementedError()


class FetchWorker(PoolWorker):
    STATE_DOWN = 'DOWNLOADING'
    STATE_CONN = 'CONNECTING'
    STATE_CLOSE = 'CLOSING'

    def worker_startup(self):
        self.status_update(state=self.STATE_CONN)
        self.conn = NNTP2(**self.kwargs.get('config'))

    def worker_shutdown(self):
        self.status_update(state=self.STATE_CLOSE)
        self.conn.quit()

#    def stop(self):
#        super(FetchWorker, self).stop()
#        self.conn.sock.close()

    def execute(self, job):
        update = partial(
            self.status_update,
            state=FetchWorker.STATE_DOWN,
            msg='Downloading',
            name=job.segment.id,
            sequence=job.segment.number,
            bytes_total=job.segment.bytes
        )

        def _status(bytes):
            update(bytes_received=bytes)

        _status(1)

        buffer = ProgressStringIO()
        buffer.progress(_status)

        #:TODO: Implement retry on failed socket operation.
        try:
            self.conn.group(job.segment.groups[0])
            self.conn.body('<{}>'.format(job.segment.id), buffer)
        except socket.error:
            raise RetryJobException(job)

        with open(os.path.join(job.destination, job.segment.id), 'wb') as fp:
            buffer.seek(0)
            fp.write(buffer.read())


class Job(object):
    def __init__(self, attempts=0, max_attempts=3):
        self.attempts = attempts
        self.max_attempts = max_attempts

    def attempt(self):
        if self.attempts == self.max_attempts:
            raise ValueError('Job cannot be tried again')
        self.attempts += 1


class FetchJob(Job):
    def __init__(self, segment, destination):
        super(FetchJob, self).__init__()
        self.segment = segment
        self.destination = destination


class NNTP2(NNTP):
    pass
    #TODO: Implement speed limits on socket.
    #TODO: Implement reset on segments that take too long to retrieve.


class ProgressStringIO(StringIO):
    def progress(self, fn):
        self.progress_fn = fn

    def write(self, s):
        StringIO.write(self, s)
        if hasattr(self, 'progress_fn'):
            self.progress_fn(self.len)


class NZBFetch(BaseScript):
    def configure_args(self, parser):
        super(NZBFetch, self).configure_args(parser)
        parser.add_argument('-n', '--connections', dest='connections', action='store', type=int, default=20)
        parser.add_argument('-s', '--skip-verify', dest='verify', action='store_false', default=True)
        parser.add_argument('-o', '--output', dest='dest', action='store', help="Specify a download location")
        parser.add_argument('nzb', action='store', help="Specify a NZB file")

    def start(self, args, config):
        """
        1. Verify any files that exist in the destination that are sourced in the NZB.
        2. Queue segments for files that are remaining.
        3. Spin up download threads and allow them to empty the job queue.
        """
        # Init thread safe structures
        stat = Event()
        jobs = Queue()

        # For fancy printing.
        term = Terminal()

        # Parse specified segments out of NZB file.
        needed = set()
        with open(args.nzb) as fp:
            parsed = nzb_parser.parse(fp.read())
            subject = parsed.subject or args.nzb
        for file in parsed.files:
            for segment in file.segments:
                needed.add(NZBSegment(segment))

        # Check to see if destination exists, if not create.
        destination = args.dest
        if not destination:
            destination = os.path.join(os.path.dirname(os.path.realpath(args.nzb)), subject)
        if not os.path.isdir(destination):
            os.makedirs(destination)

        print 'Files will be downloaded to "{}"'.format(destination)

        print 'There are {} parts required for "{}"'.format(len(needed), args.nzb)

        # Scan destination directory for files we are looking for from the NZB.
        existing = set([FileSegment(f) for f in os.listdir(destination)]) & needed  # Adding the union of needed filters to just what we want.
        existing_count = len(existing)

        print '{} of these parts exist in the destination.'.format(existing_count)

        if args.verify:
            failed = set()
            loop_count = 1
            for segment in existing:
                with term.location():
                    print 'Checking {:<50} [{:05d}/{:05d}]{}'.format(segment.id, loop_count, existing_count, term.clear_eol)
                try:
                    header, part, body, trail = read_segment(os.path.join(destination, segment.id))
                except InvalidSegmentException:
                    failed.add(segment)
                    #print segment.id
                    #raise
                if not check_crc(trail, body):
                    print 'failed'
                    failed.add(segment)
                loop_count += 1
            print '{} of the existing parts are invalid and will be retried'.format(len(failed))
            existing -= failed

        segments_to_fetch = needed - existing

        # Add files to fetch into the queue.
        #jobs.put(FetchJob(segments_to_fetch.pop(), destination))
        for segment in segments_to_fetch:
            jobs.put(FetchJob(segment, destination))

        master = TaskMaster(jobs, FetchWorker, max_threads=args.connections, status=stat, config=config['USENET'])

        thread = Thread(name='Task Master', target=master)
        thread.start()

        def status_output_control():
            # It's nice to have the total bytes.
            total_bytes = sum([s.bytes for s in segments_to_fetch])
            total_jobs = jobs.qsize()
            while thread.is_alive():
                stat.wait(timeout=1)
                self.print_status(master.threads, total_jobs, jobs.qsize(), total_bytes)
                stat.clear()
            print 'Stat Exit'

        status = Thread(name='Status Printer', target=status_output_control)
        status.start()

        while jobs.qsize() > 0:
            try:
                thread.join(0.1)
            except KeyboardInterrupt:
                print 'Waiting on Threads to Exit'
                master.stop()
                thread.join()
                break
        print 'All Exiting'

    def print_status(self, workers, total_jobs, jobs_left, total_bytes):
        term = Terminal()
        with term.location(), term.hidden_cursor():
            for thread, worker in workers.items():
                self.print_worker(worker, term)

            # Print overall status
            jobs_consumed = abs(jobs_left - total_jobs)
            percent_complete = ceil((float(jobs_consumed) / float(total_jobs)) * 100)

            prefix = '{: 5d}/{: 5d}'.format(jobs_consumed, total_jobs)
            #{:>4}/{:>4}
            suffix = '({: 3d}%)'.format(
                int(percent_complete)
            )

            bar_len = term.width - len(prefix) - len(suffix) - 2  # 2 for []
            bar_count = int(bar_len * (percent_complete / 100))
            bars = ('[{0:<'+str(bar_len)+'}]').format('=' * (bar_count-1) + '>')
            print prefix + bars + suffix
            print '{}'.format(term.clear_eos)

    def print_worker(self, worker, term):
        # <state> - file: [====>] 001/100 (xxx%)
        status = worker.status_data
        state = status['state']

        if state == FetchWorker.STATE_DOWN:
            percent_complete = ceil((float(status['bytes_received']) / float(status['bytes_total'])) * 100)
            prefix = '<{state:^11s}> - {file:^20}: '.format(
                state=status['state'],
                file=status['name'][:20],
                seq=status['sequence']
            )

            suffix = ' {:>4}/{:>4} ({:>3}%)'.format(
                bytes2human(status['bytes_received']),
                bytes2human(status['bytes_total']),
                int(percent_complete)
            )

            bar_len = term.width - len(prefix) - len(suffix) - 2  # 2 for []

            bar_count = int(bar_len * (percent_complete / 100))
            bars = ('[{0:<'+str(bar_len)+'}]').format('=' * (bar_count-1) + '>')
            print prefix + bars + suffix

        else:
            print '<{state:^11s}> - Job Startup'.format(
                state=status['state'],
            )
        return


if '__main__' == __name__:
    NZBFetch()

#!/usr/bin/python

####
# Must ../../par2/par2 r dexter.s07e06.720p.hdtv.x264-immerse.par2
# on par files after stitching.
####

import os, logging, sys, mmap, contextlib, string
from Queue import Empty, Queue
from threading import Thread, current_thread, Event, RLock, Lock
from blessings import Terminal
from scripts import BaseScript
from lib.utils import bytes2human, parse_yenc_header

yenc42 = string.join(map(lambda x: chr((x-42) & 255), range(256)), "")
yenc64 = string.join(map(lambda x: chr((x-64) & 255), range(256)), "")

# Decode a YENC-encoded message into a list of string fragments.
def yenc_decode(lines):
    buffer = []
    for line in lines:
        # Trim mandatory returns from lines.
        if line[-2:] == "\r\n":
            line = line[:-2]
        elif line[-1:] in "\r\n":
            line = line[:-1]

        # Not even sure: http://effbot.org/zone/yenc-decoder.htm
        data = string.split(line, "=")
        buffer.append(string.translate(data[0], yenc42))
        for data in data[1:]:
            data = string.translate(data, yenc42)
            buffer.append(string.translate(data[0], yenc64))
            buffer.append(data[1:])
    return ''.join(buffer)

def read_segment(filename):
    header = part = body = trail = None

    with open(filename, 'rb') as fp:
        with contextlib.closing(mmap.mmap(fp.fileno(), 0, access=mmap.ACCESS_READ)) as m:
            # Check to make sure header is present
            line = m.readline()
            if not line.startswith('=ybegin'):
                raise InvalidSegmentException('Not a Segment')
            header = parse_yenc_header(line)

            # For us, we depend on the part header also.
            line = m.readline()
            if not line.startswith('=ypart'):
                raise InvalidSegmentException('Segment has no Part')
            part = parse_yenc_header(line)

            # Read rest of file.
            buffer = []
            while True:
                line = m.readline()
                if not line:
                    break
                if line.startswith('=yend'):
                    trail = parse_yenc_header(line)
                    break
                buffer.append(line)
            body = yenc_decode(buffer)
    return header, part, body, trail


class InvalidSegmentException(Exception): pass


class ThreadSafeFile(object):
  def __init__(self, f):
    self.f = f
    self.lock = RLock()
    self.nesting = 0

  def _getlock(self):
    self.lock.acquire()
    self.nesting += 1

  def _droplock(self):
    nesting = self.nesting
    self.nesting = 0
    for i in range(nesting):
      self.lock.release()

  def write(self, data):
    self._getlock()
    self.f.write(data)
    if data == '\n':
      self._droplock()
sys.stdout = ThreadSafeFile(sys.stdout)


class Job(object):
    def __init__(self, retries=0, **kw):
        self.__dict__.update(kw)
        self.retries = retries


class TaskMaster(object):
    def __init__(self, job_queue, worker, max_threads=1, status=None):
        self.job_queue = job_queue
        self.worker = worker
        self.max_threads = max_threads
        self.threads = {}
        self.status = status

    def __call__(self):
        still_working = True

        while still_working:
            still_working = False

            while len(self.threads) < self.max_threads:
                if self.job_queue.empty():
                    break
                # We still have tasks, start a new Thread
                target = self.worker(self.job_queue, self.status)
                thread = Thread(target=target)
                self.threads[thread] = target
                thread.start()

            for thread in self.threads.keys():
                if thread.is_alive():
                    still_working = True
                else:
                    # Remove Dead Threads.
                    self.threads.pop(thread)
        print 'Master Exit'


class FileWorker(object):
    STATE_EXIT = 'EXIT'
    STATE_IDLE = 'IDLE'
    STATE_PROC = 'PROCESSING'
    STATE_LOAD = 'LOADING'

    def __init__(self, jobs, status_event=None):
        self.jobs = jobs
        self.lock = Lock()

        # Managing Status Updates
        self.status = status_event

        # Set Initial Status
        self.status_update(state=FileWorker.STATE_IDLE)

    def __call__(self):
        while True:
            try:
                job = self.jobs.get(timeout=1)
            except Empty:
                break
            self.execute(job)  # Do work here.
        self.status_update(state=FileWorker.STATE_EXIT)

    def status_update(self, **kw):
        self.status_data = kw
        self.status.set()

    def execute(self, job):
        filename = job.path
        self.status_update(state=FileWorker.STATE_LOAD, msg='Reading File', file=filename)

        try:
            header, part, body, trail = read_segment(filename)
        except InvalidSegmentException:
            return  # Skip File

        # The header tells us the target file and size. Let's setup the destination file if we need to.
        destination = os.path.join(job.dest, header['name'])
        with self.lock:
            if not os.path.isfile(destination):
                with open(destination, 'ab') as fp:
                    fp.truncate(int(header['size']))

        # The part tells us what block this is we are reading, let's put the block in the right place.
        self.status_update(state=FileWorker.STATE_PROC, msg='Reading File',
            file=filename, sbyte=part['begin'], ebyte=part['end'], dest=destination)

        with open(destination, 'r+b') as fp:
            fp.seek(int(part['begin'])-1)  # HOHOHO, yeah, -1...
            fp.write(body)
            fp.flush()



class NZBFetch(BaseScript):
    """
    This is the console interface to the file stitcher.
    """
    def configure_args(self, parser):
        super(NZBFetch, self).configure_args(parser)
        parser.add_argument('source', action='store', help="Directory to Scan for Segments")
        parser.add_argument('dest', action='store', help="Directory to place assembled pieces")
        parser.add_argument('-w', '--workers', dest='workers', action='store', help="How many IO threads to use", default=1)

    def start(self, args, config):
        jobs = Queue()
        stat = Event()

        # Scan directory for file list, create jobs.
        for filename in os.listdir(args.source):
            path = os.path.join(args.source, filename)
            if os.path.isfile(path):
                jobs.put(Job(path=path, dest=args.dest))

        master = TaskMaster(jobs, FileWorker, max_threads=10, status=stat)

        thread = Thread(name='Task Master', target=master)
        thread.start()

        def status_output_control():
            while thread.is_alive():
                stat.wait(timeout=1)
                self.print_status(master.threads)
                stat.clear()
            print 'Stat Exit'

        status = Thread(name='Status Printer', target=status_output_control)
        status.start()

        thread.join()
        print 'All Exiting'

    def print_status(self, workers):
        term = Terminal()
        with term.location():
            for thread, worker in workers.items():
                self.print_worker(worker)
            print '{}'.format(term.clear_eos)

    def print_worker(self, worker):
        # IDLE/EXIT #STATE Waiting on Job: MSG
        # LOAD      #STATE CURRENT_FILE  : MSG
        # PROC      #STATE CURRENT_FILE  :[START_BYTE:END_BYTE] -> DEST
        term = Terminal()
        status = worker.status_data
        state = status['state']

        if state in (FileWorker.STATE_IDLE, FileWorker.STATE_EXIT):
            output = '{:^11s} {:<25s} : {:<50}{}'.format(
                status['state'], 'Waiting on Job', status.get('msg', '')[-50:], term.clear_eol
            )
        elif state == FileWorker.STATE_LOAD:
            output = '{:^11s} {:<25s} : {:<50}{}'.format(
                status['state'], status['file'][-25:], status.get('msg', '')[-50:], term.clear_eol
            )
        else:
            output = '{:^11s} {:<25s} : [{:>8s}:{:>8s}] -> {:<50}{}'.format(
                status['state'], status['file'][-25:], status['sbyte'], status['ebyte'], status['dest'][-50:], term.clear_eol
            )

        print output


if '__main__' == __name__:
    NZBFetch()

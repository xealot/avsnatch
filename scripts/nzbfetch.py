#!/usr/bin/python
from functools import partial
from math import ceil
import os, logging
from nntplib import NNTP
from StringIO import StringIO
from Queue import Empty, Queue
from threading import Thread, current_thread, Event
from blinker import Signal
from blessings import Terminal
from scripts import BaseScript
from scripts.nzbparse import parse_nzb
from lib.utils import bytes2human, parse_yenc_header


class ProgressStringIO(StringIO):
    def progress(self, fn):
        self.progress_fn = fn

    def write(self, s):
        StringIO.write(self, s)
        if hasattr(self, 'progress_fn'):
            self.progress_fn(self.len)


class NNTPProcessor(object):
    STATE_IDLE = 'IDLE'
    STATE_PROC = 'PROCESSING'
    STATE_DOWN = 'DOWNLOADING'

    def __init__(self, config, queue, status_event):
        self.config = config
        self.q = queue

        # Managing Status Updates
        self.status = Signal()
        self.status_data = None
        self.status_event = status_event
        self.status.connect(self.status_update)

        # Set Initial Status
        self.status.send(state=NNTPProcessor.STATE_IDLE, msg='Idle', name='--', sequence=0)

    def status_update(self, sender, **kw):
        self.status_data = kw
        self.status_event.set()

    def __call__(self):
        thread = current_thread()
        log = logging.getLogger(thread.name)
        conn = NNTP(**self.config)
        while True:
            try:
                segment = self.q.get(timeout=1)
#                log.debug('Download segment: {}/{}'.format(segment.file.subject, segment.number))
                download_segment(conn, segment, self.status, '_work')
                self.status.send(state=NNTPProcessor.STATE_IDLE, msg='Idle', name='--', sequence=0)
            except Empty:
#                log.debug('worker done, exiting')
                break

        self.status.send(state=NNTPProcessor.STATE_PROC, msg='Disconnecting...', name='--', sequence=0)
        conn.quit()


def download_segment(connection, segment, signal=None, destination=None):
    if destination is not None and not os.path.exists(destination):
        print 'DESTINATION "{}" NOT FOUND'.format(destination)
        return

    # Status Types are Processing and Downloading.
    def _processing(state, msg, bytes=None):
        if signal is not None:
            signal_data = dict(
                state=state,
                msg=msg,
                name=segment.message_id,
                sequence=segment.number
            )
            if bytes is not None:
                signal_data.update(data=dict(
                    bytes_received=bytes,
                    bytes_total=segment.bytes,
                ))
            signal.send(**signal_data)


    buffer = ProgressStringIO()
    _processing(NNTPProcessor.STATE_DOWN, 'Starting Download', bytes=1)  # Init things.
    buffer.progress(partial(_processing, NNTPProcessor.STATE_DOWN, 'Downloading'))

    connection.group(segment.groups[1])
    connection.body('<{}>'.format(segment.message_id), buffer)

    if destination is None:
        return (
            segment, buffer
        )

    _processing(NNTPProcessor.STATE_PROC, 'Writing File', bytes=segment.bytes)
    with open(os.path.join(destination, segment.message_id), 'wb') as fp:
        buffer.seek(0)
        fp.write(buffer.read())


class NZBFetch(BaseScript):
    def configure_args(self, parser):
        super(NZBFetch, self).configure_args(parser)
        parser.add_argument('-n', '--connections', dest='connections', action='store', type=int, default=20)
        parser.add_argument('nzb', action='store', help="Specify a NZB file")
        parser.add_argument('dest', action='store', help="Specify a download location")

    def start(self, args, config):
        task_queue = Queue()
        status_event = Event()

        target_bytes = 0
        with open(args.nzb) as fp:
            parsed = parse_nzb(fp.read())
        for file in parsed:
            for segment in file.segments:
                target_bytes += segment.bytes
                task_queue.put(segment)
#                break
#            break

#        self.log.debug('Opening {} NNTP Processors'.format(args.connections))

        threads = {}
        for i in range(args.connections):
            target = NNTPProcessor(config['USENET'], queue=task_queue, status_event=status_event)
            thread = Thread(
                name='Worker {0:03d}'.format(i),
                target=target
            )
            thread.start()
            threads[thread] = target


        term = Terminal()
        start_size = task_queue.qsize()

        # Status Thread
        def poll_status_continuously():
            still_working = True
            while still_working:
                status_event.wait(timeout=2)
                # Poll Status of Threads
                still_working = False
                with term.location():
                    for thread, processor in threads.items():
                        if thread.is_alive():
                            if still_working is False:
                                still_working = True

                        status = processor.status_data
                        intro = '<{state:^11s}> - {seq:>03d} / {file:^20}:'.format(
                            state=status['state'],
                            file=status['name'][:20],
                            seq=status['sequence']
                        )

                        if status['state'] == NNTPProcessor.STATE_DOWN:
                            # Progress Bar
                            percent_complete = ceil((float(status['data']['bytes_received']) / float(status['data']['bytes_total'])) * 100)
                            follow = ' {:>4}/{:>4} ({:>3}%)'.format(
                                bytes2human(status['data']['bytes_received']),
                                bytes2human(status['data']['bytes_total']),
                                int(percent_complete)
                            )
                            bar_len = term.width - len(intro) - len(follow) - 2  # 2 for []
                            bars = int(bar_len * (percent_complete / 100))
                            outro = ('[{0:<'+str(bar_len)+'}]').format('=' * (bars-1) + '>')
                            print intro + outro + follow
                        else:
                            outro = ' {}{}'.format(status['msg'], term.clear_eol)
                            print intro + outro

                    # Print overall status
                    percent_complete = int(ceil(float(abs(task_queue.qsize() - start_size)) / float(start_size) * 100))
                    intro = '{: 5d}/{: 5d}'.format(abs(task_queue.qsize() - start_size), start_size)
                    follow = ' ({: 3d}%)'.format(percent_complete)

                    bar_len = term.width - len(intro) - len(follow) - 2  # 2 for []
                    bars = int(bar_len * (percent_complete / 100))
                    outro = ('[{0:<'+str(bar_len)+'}]').format('=' * (bars-1) + '>')

                    print intro + outro + follow

                    status_event.clear()

        thread = Thread(name='NNTP Status Poller', target=poll_status_continuously)
        thread.start()


#        still_working = True
#        while still_working:
#            Poll Status of Threads
#            still_working = False
#            for thread, processor in threads.items():
#                if thread.is_alive():
#                    if still_working is False:
#                        still_working = True
#
#                    print processor.progress()


if '__main__' == __name__:
    NZBFetch()

#!/usr/bin/python
import daemon
from core.scheduler import AVScheduler
from core.storage import get_session, Series
from scripts import BaseScript


class SchedulerConsole(BaseScript):
    """
    This is the console interface to start the scheduler daemon.
    """
    def configure_args(self, parser):
        super(SchedulerConsole, self).configure_args(parser)
        parser.add_argument('-d', '--daemonize', dest='daemonize', action='store_true', help="Daemonize Scheduler")
        parser.add_argument('-l', '--logfile', dest='logfile', default='scheduler.log')

    def start(self, args, config):
        conf = config['scheduler']
        if args.daemonize or conf['daemonize']:
            with daemon.DaemonContext():
                print 'WITH DAEMON'
                AVScheduler(sleep_time=conf['rest_duration'])
        else:
            AVScheduler(sleep_time=conf['rest_duration'])


if '__main__' == __name__:
    SchedulerConsole()

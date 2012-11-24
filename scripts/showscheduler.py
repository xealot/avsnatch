#!/usr/bin/python
import daemon
from scheduler.storage import get_session, Series, Episode
from scheduler import AVScheduler
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
        session = get_session()
        shows = session.query(Series).all()
        print 'here'
        print shows

        return

        if args.daemonize:
            with daemon.DaemonContext():
                AVScheduler()
        else:
            AVScheduler()


if '__main__' == __name__:
    SchedulerConsole()

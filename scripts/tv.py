#!/usr/bin/python
import argparse
import daemon
from scheduler import AVScheduler, storage
from scripts import BaseScript
from scripts.showscheduler import SchedulerConsole
from scripts.showsearch import ShowSearch

SUB_COMMANDS = {
    'schedule': SchedulerConsole,
    'search': ShowSearch
}


class TVConsole(BaseScript):
    """
    This is the console interface to start the scheduler daemon.
    """
    def configure_args(self, parser):
        super(TVConsole, self).configure_args(parser)
        parser.add_argument('command')
        parser.add_argument('arguments', nargs=argparse.REMAINDER)

    def start(self, args, config):
        if args.command in SUB_COMMANDS:
            SUB_COMMANDS[args.command](args.arguments)


if '__main__' == __name__:
    TVConsole()

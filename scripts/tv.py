#!/usr/bin/python
import argparse
from scheduler.storage import open_engine, initialize_db
from scripts import BaseScript
from scripts.show import SeriesCommand
from scripts.showscheduler import SchedulerConsole
from scripts.showsearch import ShowSearch

SUB_COMMANDS = {
    'schedule': SchedulerConsole,
    'search': ShowSearch,
    'show': SeriesCommand
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
        # Initialize Storage Layer.
        open_engine(config['datastore']['connect_string'])
        initialize_db() #NFC how to test if this should be done yet. Like a sync.

        if args.command in SUB_COMMANDS:
            SUB_COMMANDS[args.command](args.arguments, config)


if '__main__' == __name__:
    TVConsole()

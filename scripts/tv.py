#!/usr/bin/python
import argparse
from core.storage import open_engine, initialize_db
from scripts import SubCommand
from scripts.show import SeriesCommand
from scripts.showscheduler import SchedulerConsole
from scripts.showsearch import ShowSearch

class TVConsole(SubCommand):
    """
    This is the console interface to start the scheduler daemon.
    """
    def sub_commands(self):
        return {
            'schedule': SchedulerConsole,
            'search': ShowSearch,
            'show': SeriesCommand
        }

    def start(self, args, config):
        # Initialize Storage Layer.
        open_engine(config['datastore']['connect_string'])
        initialize_db() #NFC how to test if this should be done yet. Like a sync.
        super(TVConsole, self).start(args, config)


if '__main__' == __name__:
    TVConsole()

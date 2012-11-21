#!/usr/bin/python
import logging
import inspect
from configobj import ConfigObj
from validate import Validator
from blessings import Terminal
from sourcedb import load_info_source


class Input(object):
    prompt = '?> '
    def __init__(self, config):
        self.config = config
        self.term = Terminal()
        self.commands = {}
        for name, member in inspect.getmembers(self):
            if inspect.ismethod(member) and name.startswith('do_'):
                self.commands[name[3:]] = member.__doc__ # A Command
        self.say_hello()
        self.say_prompt()

    def _validate(self, cmd):
        if cmd in self.commands:
            getattr(self, 'do_{}'.format(cmd))()
        else:
            print 'ERROR'

    def say_hello(self):
        if self.intro:
            print self.term.bold(self.intro)
            print '-'*len(self.intro)
        if self.commands:
            for name, help in self.commands.items():
                print self.term.bold(name), ' ', help

    def say_prompt(self):
        input = raw_input(self.prompt)
        self._validate(input)


class Main(Input):
    intro = 'Welcome to AVSnatch.'

    def do_add(self):
        """Search for and add a new show to the tracker"""
        tv = load_info_source('tv', self.config)
        search = raw_input('Enter Show Title: ')
        tv.find_show(search)
        print search



log = logging.getLogger('AVSnatch')

def load_config(config_file):
    configspec = ConfigObj('default.ini', interpolation=False, list_values=False, _inspec=True)
    config = ConfigObj(infile=config_file, configspec=configspec)
    config.validate(Validator())
    log.debug('Loaded CONFIG {}'.format(config))
    return config

if '__main__' == __name__:
    # Late import, in case this project becomes a library, never to be run as main again.
    import argparse

    # Populate our options, -h/--help is already there for you.
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', dest='verbose', action='count', default=0,
                    help="Increase verbosity (specify multiple times for more)")
    parser.add_argument('-c', '--config', dest='config', action='store', default='config.ini',
                    help="Specify a config file")
    # Parse the arguments (defaults to parsing sys.argv).
    args = parser.parse_args()

    # Here would be a good place to check what came in on the command line and
    # call optp.error("Useful message") to exit if all it not well.

    log_level = logging.WARNING # default
    if args.verbose == 1:
        log_level = logging.INFO
    elif args.verbose >= 2:
        log_level = logging.DEBUG

    # Set up basic configuration, out to stderr with a reasonable default format.
    logging.basicConfig(level=log_level)

    config = load_config(args.config)
    cmd = Main(config)


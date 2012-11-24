import argparse
import logging
from config import load_config

__author__ = 'trey'

class BaseScript(object):
    def __init__(self, args=None, config=None):
        import argparse
        self.log = logging.getLogger()

        self.parser = parser = argparse.ArgumentParser()
        self.configure_args(self.parser)
        self.args = args = parser.parse_args(args=args)

        log_level = logging.WARNING # default
        if args.verbose == 1:
            log_level = logging.INFO
        elif args.verbose >= 2:
            log_level = logging.DEBUG

        logging.basicConfig(level=log_level)

        if config is None:
            self.config = config = load_config(self.args.config)
        self.start(args, config)

    def configure_args(self, parser):
        parser.add_argument('-c', '--config', dest='config', action='store', default='config.ini',
                    help="Specify a config file")
        parser.add_argument('-v', '--verbose', dest='verbose', action='count', default=0,
                        help="Increase verbosity (specify multiple times for more)")

    def start(self, args, config):
        raise NotImplementedError()


class SubCommand(BaseScript):
    def sub_commands(self):
        return {}

    def configure_args(self, parser):
        super(SubCommand, self).configure_args(parser)
        parser.add_argument('command')
        parser.add_argument('arguments', nargs=argparse.REMAINDER)

    def start(self, args, config):
        commands = self.sub_commands()
        if args.command in commands:
            commands[args.command](args.arguments, config)
        else:
            print 'UNKNOWN COMMAND'

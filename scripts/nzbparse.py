#!/usr/bin/python
from scripts import BaseScript
from lib.pynzb import nzb_parser
from lib.utils import bytes2human

def parse_nzb(contents):
    return nzb_parser.parse(contents)

class NZBParse(BaseScript):
    def configure_args(self, parser):
        super(NZBParse, self).configure_args(parser)
        parser.add_argument('-z', '--nzb', dest='nzbfile', action='store', help="Specify a NZB file")

    def start(self, args, config):
        # If there is no nzbfile, check stdin.
        with open(args.nzbfile) as fp:
            parsed = parse_nzb(fp.read())
        for file in parsed:
            print file.subject
            print file.groups
            print bytes2human(file.bytes)
            for segment in file.segments:
                print '  ', bytes2human(segment.bytes), segment.message_id

if '__main__' == __name__:
    NZBParse()

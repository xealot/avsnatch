#!/usr/bin/python
"""
Search NZB Provider for keywords provided.
"""

####
# Must ../../par2/par2 r dexter.s07e06.720p.hdtv.x264-immerse.par2
# on par files after stitching.
####
import os
import sys
from lib.utils import bytes2human, sizeof_fmt

from scripts import BaseScript
from sourcenzb.newznab import NewzNab


class NZBSearch(BaseScript):
    """
    This is the console interface to the NZB search tools.
    """
    def configure_args(self, parser):
        super(NZBSearch, self).configure_args(parser)
        group = parser.add_mutually_exclusive_group(required=False)
        group.add_argument('-g', '--category', dest='category', action='store', type=int, help="Search Category")
        group.add_argument('--movies', dest='category', action='store_const', const=2000, help="Search Movies: HD (x264)")
        group.add_argument('--tv', dest='category', action='store_const', const=5040, help="Search TV: HD (x264)")
        group.add_argument('-z', '--nzbid', dest='nzb', action='store', help="Download the NZB resource specified")
        parser.add_argument('resource', action='store', help="If searching, a search string. If specifying an NZB, a destination.")
        parser.set_defaults(category=0, nzb=False)

    def start(self, args, config):
        backend = NewzNab(config['NEWZNAB_API_KEY'])
        if args.nzb:
            if sys.stdout.isatty():
                with open(os.path.join(args.resource, '{}.nzb'.format(args.nzb)), 'wb') as fp:
                    fp.write(backend.fetch(args.nzb))
            else:
                sys.stdout.write(backend.fetch(args.resource))
        else:
            self.print_search_results(backend.search(args.resource, args.category))

    def print_search_results(self, results):
        for result in results:
            if 'error' in result:
                print 'ERROR {}'.format(result['error'])
            else:
                print '{:35s}: ({:5s}) {:15s} - {:50s}'.format(
                    result['nzbid'], sizeof_fmt(float(result['size'])), result['category'], result['name']
                )

if '__main__' == __name__:
    NZBSearch()

#!/usr/bin/python
"""
Search NZB Provider for keywords provided.
"""

####
# Must ../../par2/par2 r dexter.s07e06.720p.hdtv.x264-immerse.par2
# on par files after stitching.
####
import sys
from lib.utils import bytes2human, sizeof_fmt

from scripts import BaseScript
from sourcenzb.nzbmatrix import NZBMatrix


class NZBSearch(BaseScript):
    """
    This is the console interface to the NZB search tools.
    """
    def configure_args(self, parser):
        super(NZBSearch, self).configure_args(parser)
        group = parser.add_mutually_exclusive_group(required=False)
        group.add_argument('-g', '--category', dest='category', action='store', type=int, help="Search Category")
        group.add_argument('--movies', dest='category', action='store_const', const=42, help="Search Movies: HD (x264)")
        group.add_argument('--tv', dest='category', action='store_const', const=41, help="Search TV: HD (x264)")
        group.add_argument('-z', '--nzbid', dest='nzb', action='store_true', help="Download the NZB resource specified")
        parser.add_argument('resource', action='store', help="The search string or id you are looking for. Use QUOTES to specify a string with spaces.")
        parser.set_defaults(category=0, nzb=False)

    def start(self, args, config):
        backend = NZBMatrix(config['NZB_MATRIX_USER'], config['NZB_MATRIX_API_KEY'])
        if args.nzb is True:
            sys.stdout.write(backend.fetch(args.resource))
        else:
            self.print_search_results(backend.search(args.resource, args.category))

    def print_search_results(self, results):
        for result in results:
            if 'error' in result:
                print 'ERROR {}'.format(result['error'])
            else:
                print '{:7d}: ({:5s}) {:15s} - {:50s}'.format(
                    int(result['nzbid']), sizeof_fmt(float(result['size'])), result['category'], result['nzbname']
                )

if '__main__' == __name__:
    NZBSearch()

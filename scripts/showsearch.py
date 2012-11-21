#!/usr/bin/python
import logging
from config import load_config
from sourcedb import load_info_source

log = logging.getLogger()

def search(backend, search_str, config):
    """Search for and add a new show to the tracker"""
    tv = load_info_source(backend, config)
    results = tv.find_show(search_str)
    return results

if '__main__' == __name__:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('search', metavar='SHOW', type=str, nargs='+',
                   help='The name of a show you are searching for')
    parser.add_argument('-v', '--verbose', dest='verbose', action='count', default=0,
                    help="Increase verbosity (specify multiple times for more)")
    args = parser.parse_args()

    log_level = logging.WARNING # default
    if args.verbose == 1:
        log_level = logging.INFO
    elif args.verbose >= 2:
        log_level = logging.DEBUG

    logging.basicConfig(level=log_level)

    config = load_config()

    results = search('tv', args.search, config)
    print results


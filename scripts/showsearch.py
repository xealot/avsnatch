#!/usr/bin/python
from sourcedb import load_info_source
from scripts import BaseScript


class ShowSearch(BaseScript):
    """
    This is the console interface to the TVDB Search.
    """
    def configure_args(self, parser):
        super(ShowSearch, self).configure_args(parser)
        parser.add_argument('-i', '--id', action='store_true', help="Specify an ID to retrieve complete show data.")
        parser.add_argument('search', action='store', help="The search string or id you are looking for. Use QUOTES to specify a string with spaces.")

    def start(self, args, config):
        tv = load_info_source('tv', config['TVDB_API_KEY'])
        if not args.id:
            self.print_search_results(tv.find_series(args.search))
        else:
            self.print_series(tv.get_series(args.search))

    def print_series(self, series):
        for i in ['tvdb_id', 'network', 'status', 'airtime', 'airday', 'name']:
            print '{:15s}: {}'.format(i, series[i])
        for episode in series['episodes']:
            print ' - S{:02d}E{:02d} ({}) > {}'.format(
                int(episode['season']), int(episode['episode']), episode['air_date'], episode['name']
            )

    def print_search_results(self, results):
        for result in results:
            if 'error' in result:
                print 'ERROR {}'.format(result['error'])
            else:
                print '{:7d} - {:100s}'.format(
                    int(result['tvdb_id']), result['name'][-100:]
                )

if '__main__' == __name__:
    ShowSearch()

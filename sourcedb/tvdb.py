import logging
import requests
import xml.etree.ElementTree as ET
from . import BaseSource

__author__ = 'trey'

log = logging.getLogger()

class TheTVDB(BaseSource):
    def __init__(self, config):
        self.api_key = config['TVDB_API_KEY']

    def find_show(self, search_string):
        results = []
        response = requests.get('http://thetvdb.com/api/GetSeries.php', params=dict(seriesname=search_string))

        root = ET.fromstring(response.text)
        series = root.findall('Series')
#        import pdb; pdb.set_trace()
        for show in series:
            show_dict = {}
            for el in show.iter():
                show_dict[el.tag] = el.text
            results.append(show_dict)
        return results

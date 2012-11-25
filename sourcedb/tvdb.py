import logging
import requests
import xml.etree.ElementTree as ET
from . import BaseSource

__author__ = 'trey'

log = logging.getLogger()

series_col_map = {
    'id': 'tvdb_id',
    'IMDB_ID': 'imdb_id',
    'zap2it_id': 'zap2it_id',
    'FirstAired': 'first_aired',
    'Airs_Time': 'airtime',
    'Airs_DayOfWeek': 'airday',
    'Network': 'network',
    'banner': 'banner',
    'Language': 'language',
    'SeriesName': 'name',
    'Status': 'status',
    'Overview': 'overview',
}

episode_col_map = {
    'id': 'id',
    'seriesid': 'series_id',
    'SeasonNumber': 'season',
    'EpisodeNumber': 'episode',
    'FirstAired': 'air_date',
    'EpisodeName': 'name',
}


class TheTVDB(BaseSource):
    BASE_URL = 'http://thetvdb.com/api'

    def __init__(self, api_key):
        self.api_key = api_key

    def _default_params(self, **kw):
        return dict(
            apikey=self.api_key,
            **kw
        )

    def _get(self, path, params, with_key=True):
        url = self.BASE_URL
        if with_key is True:
            url += '/{}'.format(self.api_key)
        url += path
        return requests.get(url, params=params)

    def _nodes_to_dict(self, nodes):
        results = []
        for node in nodes:
            results.append(self._node_to_dict(node))
        return results

    def _node_to_dict(self, node):
        node_dict = {}
        for el in node.iter():
            node_dict[el.tag] = el.text
        return node_dict

    def _convert(self, data, map, skip_missing=False):
        converted = {}
        for s, d in map.items():
            try:
                converted[d] = data[s]
            except KeyError:
                if skip_missing is False:
                    raise
        return converted

    def find_series(self, search_string):
        response = self._get('/GetSeries.php', params=self._default_params(seriesname=search_string), with_key=False)

        root = ET.fromstring(response.text.encode('utf8'))
        results = []
        for result in self._nodes_to_dict(root.findall('Series')):
            results.append(self._convert(result, series_col_map, skip_missing=True))
        return results

    def get_series(self, show_id):
        response = self._get('/series/{}/all/'.format(show_id), params=self._default_params())

        root = ET.fromstring(response.text.encode('utf8'))
        series = self._convert(self._node_to_dict(root.find('Series')), series_col_map)
        series['episodes'] = []
        for ep in self._nodes_to_dict(root.findall('Episode')):
            series['episodes'].append(self._convert(ep, episode_col_map))
        return series




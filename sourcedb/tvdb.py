import logging
import requests
import xml.etree.ElementTree as ET
from . import BaseSource

__author__ = 'trey'

log = logging.getLogger()

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

    def find_series(self, search_string):
        response = self._get('/GetSeries.php', params=self._default_params(seriesname=search_string), with_key=False)

        root = ET.fromstring(response.text.encode('utf8'))
        return self._nodes_to_dict(root.findall('Series'))

    def get_series(self, show_id):
        response = self._get('/series/{}/all/'.format(show_id), params=self._default_params())

        root = ET.fromstring(response.text.encode('utf8'))
        series = self._node_to_dict(root.find('Series'))
        series['episodes'] = self._nodes_to_dict(root.findall('Episode'))
        return series




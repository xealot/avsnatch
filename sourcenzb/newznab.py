import json

__author__ = 'trey'
# http://newz.keagaming.com/
# http://nzbtv.net/
# category list queries from capabilities call http://newz.keagaming.com/api?t=caps&o=json
# list(chain(*[[c['@attributes']]+[i['@attributes'] for i in c['subcat']] for c in data['categories']['category']]))
# dict([(c['id'], c['name']) for c in cats])

from . import BaseNZBSource
import requests

API_CATEGORIES = {
    '1000': 'Console',
    '1010': 'NDS',
    '1020': 'PSP',
    '1030': 'Wii',
    '1040': 'Xbox',
    '1050': 'Xbox 360',
    '1060': 'WiiWare/VC',
    '1070': 'XBOX 360 DLC',
    '1080': 'PS3',
    '2000': 'Movies',
    '2010': 'Foreign',
    '2020': 'Other',
    '2030': 'SD',
    '2040': 'HD',
    '2050': 'BluRay',
    '2060': '3D',
    '3000': 'Audio',
    '3010': 'MP3',
    '3020': 'Video',
    '3030': 'Audiobook',
    '3040': 'Lossless',
    '4000': 'PC',
    '4020': 'ISO',
    '4030': 'Mac',
    '4040': 'Mobile-Other',
    '4050': 'Games',
    '4060': 'Mobile-iOS',
    '4070': 'Mobile-Android',
    '5000': 'TV',
    '5020': 'Foreign',
    '5030': 'SD',
    '5040': 'HD',
    '5050': 'Other',
    '5060': 'Sport',
    '5070': 'Anime',
    '5080': 'Documentary',
    '7000': 'Other',
    '7010': 'Misc',
    '7020': 'Ebook',
    '7030': 'Comics'
}


class NewzNab(BaseNZBSource):
    BASE_URL = "http://nzbtv.net/api"

    def __init__(self, api_key):
        self.api_key = api_key

    def _default_params(self, **kw):
        return dict(
            o='json',
            apikey=self.api_key,
            **kw
        )

    def _get(self, path='', **kw):
        return requests.get('{}{}'.format(self.BASE_URL, path), params=self._default_params(**kw))

    def _parse_result(self, text):
        """
        Ugly XML based on ATOM. The JSON is even uglier.
        """
        #print text
        raw_results = json.loads(text)['channel']['item']
        results = []
        for raw_result in raw_results:
            result = {
                'name': raw_result['title'],
                'category': raw_result['category'],
                'size': [i['@attributes']['value'] for i in raw_result['attr'] if i['@attributes']['name'] == 'size'][0],
                'nzbid': [i['@attributes']['value'] for i in raw_result['attr'] if i['@attributes']['name'] == 'guid'][0]
            }
            results.append(result)
        return results

    def search(self, id, category=0):
        response = self._get(t='search', q=id, cat=category)
        return self._parse_result(response.text)

    def fetch(self, id):
        return self._get(t='get', id=id).text

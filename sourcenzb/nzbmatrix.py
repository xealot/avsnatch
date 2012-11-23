"""
Holy no error handlig batman!
"""
from . import BaseNZBSource
import requests

API_CATEGORIES = {
    0: "Everything",
    1: "Movies: SD (Image)",
    2: "Movies: SD",
    54: "Movies: HD (Remux)",
    42: "Movies: HD (x264)",
    50: "Movies: HD (Image)",
    4: "Movies: Other",
    5: "TV: SD (Image)",
    6: "TV: SD",
    41: "TV: HD (x264)",
    57: "TV: HD (Image)",
    7: "TV: Sport/Ent",
    8: "TV: Other",
    9: "Documentaries: SD",
    53: "Documentaries: HD",
    10: "Games: PC",
    11: "Games: PS2",
    43: "Games: PS3",
    12: "Games: PSP",
    13: "Games: Xbox",
    14: "Games: Xbox360",
    56: "Games: Xbox360 (Other)",
    44: "Games: Wii",
    51: "Games: Wii VC",
    45: "Games: DS",
    17: "Games: Other",
    18: "Apps: PC",
    19: "Apps: Mac",
    52: "Apps: Portable",
    20: "Apps: Linux",
    21: "Apps: Other",
    22: "Music: MP3 Albums",
    47: "Music: MP3 Singles",
    23: "Music: Lossless",
    24: "Music: DVD",
    25: "Music: Video",
    27: "Music: Other",
    28: "Anime: ALL",
    49: "Other: Audio Books",
    26: "Other: Radio",
    36: "Other: E-Books",
    37: "Other: Images",
    55: "Other: Android",
    38: "Other: iOS/iPhone",
    39: "Other: Extra Pars/Fills",
    40: "Other: Other",
}


class NZBMatrix(BaseNZBSource):
    BASE_URL = "http://api.nzbmatrix.com/v1.1"

    def __init__(self, user, api_key):
        self.user = user
        self.api_key = api_key

    def _default_params(self, **kw):
        return dict(
            username=self.user,
            apikey=self.api_key,
            **kw
        )

    def _get(self, path, params):
        return requests.get('{}{}'.format(self.BASE_URL, path), params=params)

    def _parse_result(self, text):
        """
        NZBID:444027; = NZB ID On Site
        NZBNAME:mandriva linux 2009; = NZB Name On Site
        LINK:nzbmatrix.com/nzb-details.php?id=444027&hit=1; = Link To NZB Details PAge
        SIZE:1469988208.64; = Size in bytes
        INDEX_DATE:2009-02-14 09:08:55; = Indexed By Site (Date/Time GMT)
        USENET_DATE:2009-02-12 2:48:47; = Posted To Usenet (Date/Time GMT)
        CATEGORY:TV > Divx/Xvid; = NZB Post Category
        GROUP:alt.binaries.linux; = Usenet Newsgroup
        COMMENTS:0; = Number Of Comments Posted
        HITS:174; = Number Of Hits (Views)
        NFO:yes; = NFO Present
        WEBLINK:http://linux.org; = HTTP Link To Attached Website
        LANGUAGE:English; = Language Attached From Our Index
        IMAGE:http://linux.org/logo.gif; = HTTP Link To Attached Image
        REGION:0; = Region Coding (See notes)
        """
        raw_results = text.split('|')
        results = []
        for raw_result in raw_results:
            result = {}
            lines = raw_result.splitlines()
            for line in lines:
                if line:
                    key, _, value = line.partition(':')
                    result[key.lower()] = value[:-1]
            if result:
                results.append(result)
        return results

    def search(self, id, category=0, limit=10):
        response = self._get('/search.php', self._default_params(
            catid=category,
            num=limit,
            search=id
        ))
        return self._parse_result(response.text)

    def fetch(self, id):
        return self._get('/download.php', self._default_params(id=id)).text

from .utils import load_class

__author__ = 'trey'

INFO_SOURCES = {
    'tv': 'sourcedb.tvdb.TheTVDB'
}

class BaseSource(object):
    def find_show(self, search_string):
        raise NotImplementedError()

def load_info_source(name_or_path, config):
    if name_or_path in INFO_SOURCES:
        return load_class(INFO_SOURCES[name_or_path])(config)
    else:
        return load_class(name_or_path)(config)

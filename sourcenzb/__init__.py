__author__ = 'trey'

class BaseNZBSource(object):
    def __init__(self, config):
        self.config = config

    def fetch(self, id):
        raise NotImplementedError()

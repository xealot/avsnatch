__author__ = 'trey'

class BaseNZBSource(object):
    def search(self, id):
        raise NotImplementedError()

    def fetch(self, id):
        raise NotImplementedError()

from . import BaseNZBSource

class NZBMatrix(BaseNZBSource):
    def fetch(self, id):
        print 'config', self.config['NZB_MATRIX_USER']

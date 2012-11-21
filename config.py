#!/usr/bin/python
import logging
from configobj import ConfigObj
from validate import Validator

log = logging.getLogger()

def load_config(config_file='config.ini'):
    configspec = ConfigObj('default.ini', interpolation=False, list_values=False, _inspec=True)
    config = ConfigObj(infile=config_file, configspec=configspec)
    config.validate(Validator())
    log.debug('Loaded CONFIG')
    return config

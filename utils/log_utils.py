#!/usr/bin/env python

import sys
import logging


class Wyndhamlog(object):
    def __init__(self,which):
        self.which = which
        logger = logging.getLogger(which)
        logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        self.logger = logger

#!/usr/bin/env python

''' In place of the yucky bash to do this '''

import os

try:
    os.symlink('.', 'Wyndham')
except OSError:
    pass

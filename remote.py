#!/usr/bin/env python
# LeCrunch2 
# Copyright (C) 2014 Benjamin Land
#
# based on
#
# LeCrunch
# Copyright (C) 2010 Anthony LaTorre 
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import time
import socket
import config
from lecroy import LeCroyScope

if __name__ == '__main__':
    scope = LeCroyScope(config.ip, timeout=config.timeout)
    scope.clear()
    settings = scope.get_settings()
    print settings
    while True:
        cmd = raw_input("> ")
        if len(cmd) <= 0:
            break
        scope.send(cmd);
        print scope.recv(),

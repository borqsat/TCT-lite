#!/usr/bin/python
#
# Copyright (C) 2013 Intel Corporation
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# Authors:
#              Liu,chengtao <liux.chengtao@intel.com>

import os
import re
import sys
import threading
import time
import json
from impl import tizenMobile

class Connector:
    '''Communication module for automatic test'''

    def __init__(self,config):
        if "tizenMobile" in config:
            self.impl = tizenMobile()
        else
            self.impl = None

    def get_device_ids(self):
        """list the ids of device available"""
        if not self.impl is None:
            return self.impl.get_device_ids()
        else
            return None

    def get_device_info(self, deviceid):
        """get device information by device id"""
        if not self.impl is None:
            return self.impl.get_device_info(deviceid)
        else
            return None

    def install_package(self, deviceid, pkgpath=None):
        """install a package to remote test terminal"""
        if not self.impl is None:
            return self.impl.install_package()
        else
            return None

    def remove_package(self, deviceid, pkgname):
        """remove a package from remote test terminal"""
        if not self.impl is None:
            return self.impl.get_device_ids()
        else
            return None

    def init_test(self, deviceid, params):
        """Init the test environment"""
        if not self.impl is None:
            return self.impl.get_device_ids()
        else
            return None

    def run_test(self, sessionid, test_set=None):
        """send the test set data to remote test stub/container"""
        if not self.impl is None:
            return self.impl.send_test_data()
        else
            return None

    def get_test_status(self, sessionid):
        """get test status from remote test terminal"""
        if not self.impl is None:
            return self.impl.get_test_status()
        else
            return None

    def get_test_result(self, sessionid):
        """get test result from remote test terminal"""
        if not self.impl is None:
            return self.impl.get_test_status()
        else
            return None

    def finalize_test(self, sessionid):
        """send the test set data to remote test stub"""
        if not self.impl is None:
            return self.impl.finalize_test()
        else
            return None

def main(argvs):
    pass

if (__name__ == '__main__'):
    main(sys.argv)
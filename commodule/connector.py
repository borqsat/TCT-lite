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
# Foundation, Inc., 51 Franklin Street, Fifth Floor,Boston, MA 02110-1301,USA.
#
# Authors:
#              Liu,chengtao <liux.chengtao@intel.com>

import sys

class Connector:
    """Communication module for automatic test"""
    def __init__(self, config):
        self.__impl = None
        if 'tizenMobile' in config:
            try:
                from impl.tizenMobile import tizenMobile
                self.__impl = tizenMobile()
            except Exception, e:
                print e

    def get_device_ids(self):
        """list the ids of device available"""
        if not self.__impl is None:
            return self.__impl.get_device_ids()
        else:
            return None

    def get_device_info(self, deviceid):
        """get device information by device id"""
        if not self.__impl is None:
            return self.__impl.get_device_info(deviceid)
        else:
            return None

    def install_package(self, deviceid, pkgpath=None):
        """install a package to remote test terminal"""
        if not self.__impl is None:
            return self.__impl.install_package(deviceid, pkgpath)
        else:
            return None

    def remove_package(self, deviceid, pkgname):
        """remove a package from remote test terminal"""
        if not self.__impl is None:
            return self.__impl.get_device_ids(deviceid, pkgname)
        else:
            return None

    def init_test(self, deviceid, params):
        """Init the test environment"""
        if not self.__impl is None:
            return self.__impl.get_device_ids(deviceid, params)
        else:
            return None

    def run_test(self, sessionid, test_set=None):
        """send the test set data to remote test stub/container"""
        if not self.__impl is None:
            return self.__impl.send_test_data(sessionid, test_set)
        else:
            return None

    def get_test_status(self, sessionid):
        """get test status from remote test terminal"""
        if not self.__impl is None:
            return self.__impl.get_test_status(sessionid)
        else:
            return None

    def get_test_result(self, sessionid):
        """get test result from remote test terminal"""
        if not self.__impl is None:
            return self.__impl.get_test_status(sessionid)
        else:
            return None

    def finalize_test(self, sessionid):
        """send the test set data to remote test stub"""
        if not self.__impl is None:
            return self.__impl.finalize_test(sessionid)
        else:
            return None

def main(argvs):
    """commanline entry for invoke Connector apis"""
    if len(argvs) < 2:
        print "No parameter provided."
    conn = Connector({'tizenMobile':'yes'})
    ret = conn.get_device_ids()
    for l in ret:
        print 'id = %s' % l

if __name__ == '__main__':
    main(sys.argv)
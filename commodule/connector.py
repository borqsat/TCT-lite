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
import time

class Connector:
    """Communication module for automatic test"""
    def __init__(self, config):
        self.__handler = None
        if "testremote" in config:
            try:
                exec "from impl.%s import testremote" % config["testremote"]
                self.__handler = testremote
            except Exception, e:
                print e

    def get_connector(self):
        """list the handler instance"""
        return self.__handler

def main(argvs):
    """commanline entry"""
    pass

if __name__ == '__main__':
    main(sys.argv)
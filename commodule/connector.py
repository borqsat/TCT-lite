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
    """commanline entry for invoke Connector apis"""
    if len(argvs) < 2:
        print "No command-line parameters provided."
        return

    ret = None
    subcmd = argvs[1]
    conn = Connector({"testremote":"tizenMobile"}).get_connector()
    if conn is None:
        print "Testremote instance is not initialized successfully!"        
        return
    if subcmd == "get_device_ids":
        ret = conn.get_device_ids()
    elif subcmd == "get_device_info":
        ret = conn.get_device_info("emulator-26100") 
    elif subcmd == "install_package":
        ret = conn.install_package("emulator-26100", \
                                   "/home/test_packages/test.rpm")
    elif subcmd == "get_installed_package":
        ret = conn.get_installed_package("emulator-26100")
    elif subcmd == "remove_package":
        ret = conn.remove_package("emulator-26100", \
                                  "cts-webapi-tizen-contact-tests-1.1.9-7.1.i586")
    elif subcmd == "init_test":
        ret = conn.init_test("emulator-26100", \
                             {"stub_entry":"/tmp/httpserver"})
        while True:
            ret = conn.get_test_status("0011223344556677")
            if ret == {}:
                break
            print "get status:", ret
            time.sleep(0.6)

    elif subcmd == "run_test":
        ret = conn.run_test("0011223344556677")
    elif subcmd == "get_test_status":
        ret = conn.get_test_status("0011223344556677")
    elif subcmd == "get_test_result":
        ret = conn.get_test_result("0011223344556677")
    elif subcmd == "finalize_test":
        ret = conn.finalize_test("0011223344556677")
    else: 
        print "unknown sub command name \"%s\"" % subcmd

    #print "result:", ret

if __name__ == '__main__':
    main(sys.argv)

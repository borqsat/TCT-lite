#!/usr/bin/python
#
# Copyright (C) 2012 Intel Corporation
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
# Foundation, Inc.,
# 51 Franklin Street, 
# Fifth Floor,
# Boston, MA  02110-1301, USA.
#
# Authors:
#              Yuanyuan,Zou  <yuanyuan.zou@borqs.com>

import sys
sys.path.append("../../")
from testkitlite.engines.default.runner import *
from commodule.connector import Connector
import unittest
import json
from optparse import OptionParser
from mock import MagicMock
import traceback
#test Class 
class RunnerTestCase(unittest.TestCase):
    def setUp(self):
        self.CONNECTOR = Connector({"testremote": "tizenmobile"}).get_connector()
        self.CONNECTOR.init_test = MagicMock(return_value='123456')
        self.CONNECTOR.run_case = MagicMock(return_value=True)
        self.CONNECTOR.get_test_status = MagicMock(return_value={'finished':"1"})
        self.CONNECTOR.get_test_result = MagicMock(return_value={"cases":{}})
        self.CONNECTOR.get_device_info = MagicMock(return_value={"device_id":None,"device_model":None, "device_name":None, "build_id":None, "os_version":None, "resolution":None, "screen_size":None})
        self.runner = TRunner(self.CONNECTOR)
        self.log_dir = os.path.join(os.path.expandvars('$HOME'),"testresult")
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def tearDown(self):
        self.runner = None

    def test_set_pid_log(self):
        self.runner.set_pid_log('/home/test/autotest')
        self.assertEqual(self.runner.pid_log,'/home/test/autotest')

    def test_set_global_parameters(self):
        parser = OptionParser()
        parser.add_option("-D", "--dryrun", dest="bdryrun",
                    action="store_true",
                    help="Dry-run the selected test cases"),
        parser.add_option("-o", "--output", dest="resultfile",
                                help=""),
        parser.add_option("-e", dest="exttest", action="store",
                                help=""),
        parser.add_option("--non-active", dest="non_active", action="store_true",
                                help=""),
        parser.add_option("--deviceid",dest="device_serial", action="store",
                                help="set sdb device serial information" ),
        parser.add_option("--debug", dest="debug", action="store_true",
                    help="run in debug mode,more log information print out"),
        parser.add_option("--rerun", dest="rerun", action="store_true",
                    help="check if rerun test mode")

        args = ["--output",self.log_dir,"-e","WRTLauncher",
                "--non-active","none",
                "--deviceid","123"]
        (options, args) = parser.parse_args(args)  
        print options
        self.runner.set_global_parameters(options)

    def test_set_session_id(self):
        self.runner.set_session_id('12345')
        self.assertEqual(self.runner.session_id,'12345')

    def test_add_filter_rules(self):
        wfilters = {}
        wfilters['execution_type'] = ["manual"]
        self.runner.add_filter_rules(**wfilters)  
          
    def test_prepare_run(self):
        wfilters = {}
        wfilters['execution_type'] = ["auto"]
        self.runner.add_filter_rules(**wfilters)
        a = self.runner.prepare_run('./tct-alarm-tizen-tests/tests.xml',self.log_dir)
        self.assertEqual(a,True)

    def test_run_case(self):
        self.test_prepare_run()
        # self.runner.external_test = 'WRTLauncher'
        # self.runner.exe_sequence = ['tct-alarm-tizen-tests.auto']
        # self.runner.testsuite_dict = {'tct-alarm-tizen-tests.auto': ['/home/test/testresult/tct-time-tizen-tests.auto.suite_1_set_1.xml']}
        self.runner.run_case(self.log_dir)

    def test_merge_resultfile(self):
        #self.runner.resultfiles = set([os.path.join(self.log_dir,"tct-alarm-tizen-tests.auto.xml")])
        start_time = '2013-07-08_16_36_43'#depend you start test time
        self.runner.merge_resultfile(start_time, self.log_dir)



def suite():
    suite = unittest.TestSuite()
    suite.addTest(RunnerTestCase("test_merge_resultfile"))
    return suite

#run test
if __name__ == "__main__":
    #unittest.main(defaultTest = 'suite')
    unittest.main()



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
from testkitlite.engines.default.runner import TRunner
import unittest

#test Class 
class RunnerTestCase(unittest.TestCase):
    def setUp(self):
        self.runner = TRunner()
    def tearDown(self):
        self.runner = None
    def test_set_pid_log(self):
    	self.runner.set_pid_log('/home/test/autotest')
        self.assertEqual(self.runner.pid_log,'/home/test/autotest')
    def test_set_dryrun(self):
        self.runner.set_dryrun(True)
        self.assertEqual(self.runner.bdryrun,True)
    def test_set_non_active(self):
        self.runner.set_non_active(True)
        self.assertEqual(self.runner.non_active,True)
    def test_set_enable_memory_collection(self):
        self.runner.set_enable_memory_collection(True)
        self.assertEqual(self.runner.enable_memory_collection,True)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(RunnerTestCase("test_set_pid_log"))
    return suite

#run test
if __name__ == "__main__":
    #unittest.main(defaultTest = 'suite')
    unittest.main()



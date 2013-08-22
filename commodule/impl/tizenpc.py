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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.
#
# Authors:
#           Chengtao,Liu  <chengtaox.liu@intel.com>
""" The implementation for Tizen PC mode"""

import os
import time
import socket
import threading
import re
import uuid
import ConfigParser

from datetime import datetime
from commodule.log import LOGGER
from commodule.httprequest import get_url, http_request
from commodule.autoexec import shell_command, shell_command_ext
from commodule.killall import killall

HOST_NS = "127.0.0.1"
CNT_RETRY = 10
DATE_FORMAT_STR = "%Y-%m-%d %H:%M:%S"
APP_QUERY_STR = "ps aux | grep %s"
WRT_INSTALL_STR = "wrt-installer -i /opt/%s/%s.wgt"
WRT_QUERY_STR = "wrt-launcher -l|grep '%s'|grep -v grep" \
                "|awk '{print $2\":\"$NF}'"
WRT_START_STR = "wrt-launcher -s %s"
WRT_UNINSTL_STR = "wrt-installer -un %s"


class QUTestExecThread(threading.Thread):

    """execute Jquery Unit test suite """

    def __init__(self, deviceid="", sessionid="", test_set="", cases=None):
        super(QUTestExecThread, self).__init__()
        self.device_id = deviceid
        self.test_session = sessionid
        self.test_set = test_set
        self.test_cases = cases

    def run(self):
        """run Qunit tests"""
        global TEST_SERVER_RESULT, TEST_FLAG
        LOCK_OBJ.acquire()
        TEST_SERVER_RESULT = {"resultfile": ""}
        LOCK_OBJ.release()
        _set_finished()
        ls_cmd = "ls -l %s" % (UIFW_RESULT)
        time_stamp = ""
        prev_stamp = ""
        LOGGER.info('[webuifw] start test execution...')
        time_out = 600
        status_cnt = 0
        while time_out > 0:
            if TEST_FLAG == 1:
                break
            LOGGER.info('[webuifw] test is running')
            time.sleep(2)
            time_out -= 2
            exit_code, ret = shell_command(ls_cmd)
            time_stamp = ret[0] if len(ret) > 0 else ""
            if time_stamp == prev_stamp:
                continue
            prev_stamp = time_stamp
            status_cnt += 1

            if status_cnt == 1:
                for test_case in self.test_cases:
                    LOGGER.info("[webuifw] execute case: %s # %s"
                                % (self.test_set, test_case['case_id']))
                self.test_cases = []
            elif status_cnt >= 2:
                LOCK_OBJ.acquire()
                TEST_SERVER_RESULT = {"resultfile": UIFW_RESULT}
                LOCK_OBJ.release()
                break
        LOGGER.info('[webuifw] end test execution...')
        _set_finished(1)


class TizenPC:
    """ Implementation for transfer data
        between Host and Tizen Mobile Device
    """
    def __init__(self):
        self.__st = dict({'server_url': None,
                          'async_stub': None,
                          'async_shell': None,
                          'async_http': None,
                          'async_core': None,
                          'dlog_shell': None,
                          'block_size': 300,
                          'device_id': None,
                          'test_type': None,
                          'auto_iu': False,
                          'fuzzy_match': False,
                          'self_exec': False,
                          'self_repeat': False,
                          'debug_mode': False,
                          'test_wgt': None})

    def get_device_ids(self):
        """
            get deivce list of ids
        """
        return ['localhost']

    def get_device_info(self, deviceid=None):
        """
            get tizen deivce inforamtion
        """
        device_info = {}
        resolution_str = ""
        screen_size_str = ""
        device_model_str = ""
        device_name_str = ""
        build_id_str = ""
        os_version_str = ""

        # get resolution and screen size
        exit_code, ret = shell_command("xrandr")
        pattern = re.compile("connected (\d+)x(\d+).* (\d+mm) x (\d+mm)")
        for line in ret:
            match = pattern.search(line)
            if match:
                resolution_str = "%s x %s" % (match.group(1), match.group(2))
                screen_size_str = "%s x %s" % (match.group(3), match.group(4))

        # get architecture
        exit_code, ret = shell_command("uname -m")
        if len(ret) > 0:
            device_model_str = ret[0]

        # get hostname
        exit_code, ret = shell_command("uname -n")
        if len(ret) > 0:
            device_name_str = ret[0]

        # get os version
        exit_code, ret = shell_command(
            "cat /etc/issue")
        for line in ret:
            if len(line) > 1:
                os_version_str = "%s %s" % (os_version_str, line)

        # get build id
        exit_code, ret = shell_command(
            "cat /etc/os-release")
        for line in ret:
            if line.find("BUILD_ID=") != -1:
                build_id_str = line.split('=')[1].strip('\"\r\n')

        os_version_str = os_version_str[0:-1]
        device_info["device_id"] = deviceid
        device_info["resolution"] = resolution_str
        device_info["screen_size"] = screen_size_str
        device_info["device_model"] = device_model_str
        device_info["device_name"] = device_name_str
        device_info["os_version"] = os_version_str
        device_info["build_id"] = build_id_str
        return device_info

    def install_package(self, deviceid, pkgpath):
        """
           install a package on tizen device
        """
        cmd = "rpm -ivh %s" % pkgpath
        exit_code, ret = shell_command(cmd)
        return ret

    def get_installed_package(self, deviceid):
        """get list of installed package from device"""
        cmd = "rpm -qa | grep tct"
        exit_code, ret = shell_command(cmd)
        return ret

    def __get_test_options(self, deviceid, test_launcher, test_suite,
                           test_set):
        """get test option dict """
        test_opt = {}
        cmd = ""
        test_opt["suite_name"] = test_suite
        test_opt["launcher"] = test_launcher
        suite_id = None
        if test_launcher.find('WRTLauncher') != -1:
            test_opt["launcher"] = "wrt-launcher"
            # test suite need to be installed by commodule
            if self.__st['auto_iu']:
                test_wgt = test_set
                cmd = WRT_INSTALL_STR % (test_suite, test_wgt)
                exit_code, ret = shell_command(cmd)
                if exit_code == -1:
                    LOGGER.info("[ failed to install widget \"%s\" in target ]"
                                % test_wgt)
                    return None
            else:
                test_wgt = test_suite

            # query the whether test widget is installed ok
            cmd = WRT_QUERY_STR % test_wgt
            exit_code, ret = shell_command(cmd)
            if exit_code == -1:
                return None
            for line in ret:
                items = line.split(':')
                if len(items) < 1:
                    continue
                if (self.__st['fuzzy_match'] and
                        items[0].find(test_wgt) != -1) or items[0] == test_wgt:
                    suite_id = items[1].strip('\r\n')
                    break

            if suite_id is None:
                LOGGER.info("[ test widget \"%s\" not found in target ]"
                            % test_wgt)
                return None
            else:
                test_opt["suite_id"] = suite_id
                self.__st['test_wgt'] = suite_id

        return test_opt

    def __init_webtest_opt(self, deviceid, params):
        """init the test runtime, mainly process the star up of test stub"""
        if params is None:
            return None

        session_id = str(uuid.uuid1())
        cmdline = ""
        debug_opt = ""
        stub_app = params["stub-name"]
        stub_port = "8000"
        test_launcher = params.get('external-test', '')
        testset_name = params.get('testset-name', '')
        testsuite_name = params.get('testsuite-name', '')
        capability_opt = params.get("capability", None)
        client_cmds = params.get('client-command', '').strip().split()
        wrt_tag = client_cmds[1] if len(client_cmds) > 1 else ""
        self.__st['auto_iu'] = wrt_tag.find('iu') != -1
        self.__st['fuzzy_match'] = wrt_tag.find('z') != -1
        self.__st['self_exec'] = wrt_tag.find('a') != -1
        self.__st['self_repeat'] = wrt_tag.find('r') != -1
        self.__st['testsuite_name'] = testsuite_name
        self.__st['debug_mode'] = params.get("debug", False)

        # uifw, this suite is duplicated
        if self.__st['self_repeat']:
            self.__st['test_type'] = "jqunit"
            return session_id

        # uifw, this suite is self execution
        if self.__st['self_exec']:
            self.__st['test_type'] = "jqunit"

        test_opt = self.__get_test_options(
            deviceid, test_launcher, testsuite_name, testset_name)

        if test_opt is None:
            LOGGER.info("[ init the test options, get failed ]")
            return None

        # self executed test suite don't need stub server
        if self.__st['self_exec']:
            return session_id

        if self.__st['debug_mode']:
            debug_opt = '--debug'

        # init testkit-stub deamon process
        timecnt = 0
        blaunched = False
        while timecnt < 3:
            exit_code, ret = shell_command(
                APP_QUERY_STR % (stub_app))
            if len(ret) < 1:
                LOGGER.info("[ attempt to launch stub: %s ]" % stub_app)
                cmdline = "'%s --port:%s %s; sleep 2s' " \
                    % (stub_app, stub_port, debug_opt)
                exit_code, ret = shell_command(cmdline)
                time.sleep(2)
                timecnt += 1
            else:
                blaunched = True
                break

        if not blaunched:
            LOGGER.info("[ init test stub failed, please check target! ]")
            return None

        self.__st['server_url'] = "http://%s:%s" % (HOST_NS, stub_port)

        timecnt = 0
        blaunched = False
        while timecnt < CNT_RETRY:
            ret = http_request(get_url(
                self.__st['server_url'], "/check_server_status"), "GET", {})
            if ret is None:
                LOGGER.info("[ check server status, not ready yet! ]")
                timecnt += 1
                time.sleep(1)
                continue

            if "error_code" in ret:
                LOGGER.info("[ check server status, "
                            "get error code %d ! ]" % ret["error_code"])
                return None
            else:
                blaunched = True
                break

        if blaunched:
            ret = http_request(get_url(
                self.__st['server_url'], "/init_test"), "POST", test_opt)
            if ret is None:
                LOGGER.info("[ init test suite failed! ]")
                return None
            elif "error_code" in ret:
                LOGGER.info("[ init test suite, "
                            "get error code %d ! ]" % ret["error_code"])
                return None

            if capability_opt is not None:
                ret = http_request(get_url(self.__st['server_url'],
                                           "/set_capability"),
                                   "POST", capability_opt)
            return session_id
        else:
            LOGGER.info("[ connect to server timeout! ]")
            return None

    def init_test(self, deviceid, params):
        """init the test envrionment"""
        self.__st['device_id'] = deviceid
        self.__test_set_name = ""

        global TEST_FLAG
        LOCK_OBJ.acquire()
        TEST_FLAG = 0
        LOCK_OBJ.release()

        if "testset-name" in params:
            self.__test_set_name = params["testset-name"]
        if "client-command" in params and params['client-command'] is not None:
            self.__st['test_type'] = "webapi"
            return self.__init_webtest_opt(deviceid, params)
        else:
            self.__st['test_type'] = "coreapi"
            return str(uuid.uuid1())

    def __run_core_test(self, sessionid, test_set_name, exetype, cases):
        """
            process the execution for core api test
        """
        self.__st['async_core'] = CoreTestExecThread(
            self.__st['device_id'], test_set_name, exetype, cases)
        self.__st['async_core'].start()
        return True

    def __run_jqt_test(self, sessionid, test_set_name, exetype, cases):
        """
            process the execution for Qunit testing
        """
        global TEST_SERVER_RESULT, TEST_SERVER_STATUS
        cmdline = ""
        blauched = False
        timecnt = 0
        if self.__st['self_exec']:
            cmdline = WRT_START_STR % self.__st['test_wgt']
            while timecnt < 3:
                exit_code, ret = shell_command(cmdline)
                if len(ret) > 0 and ret[0].find('launched') != -1:
                    blauched = True
                    break
                timecnt += 1
                time.sleep(3)

            if blauched:
                self.__st['async_shell'] = QUTestExecThread(
                    deviceid=self.__st['device_id'],
                    sessionid=sessionid,
                    test_set=test_set_name,
                    cases=cases)
                self.__st['async_shell'].start()
            else:
                LOGGER.info(
                    "[ launch widget \"%s\" failed! ]" % self.__st['test_wgt'])
                TEST_SERVER_STATUS = {"finished": 1}
                TEST_SERVER_RESULT = {"resultfile": ""}
            return True

        if self.__st['self_repeat']:
            result_file = os.path.expanduser(
                "~") + os.sep + sessionid + "_uifw.xml"
            for test_case in cases:
                LOGGER.info("[uifw] execute case: %s # %s"
                            % (test_set_name, test_case['case_id']))
            TEST_SERVER_RESULT = {"resultfile": UIFW_RESULT}
            TEST_SERVER_STATUS = {"finished": 1}
            return True

    def __run_web_test(self, test_set_name, exetype, ctype, cases):
        """
            process the execution for web api test
            may be splitted to serveral blocks,
            with the unit size defined by block_size
        """
        case_count = len(cases)
        blknum = 0
        if case_count % self.__st['block_size'] == 0:
            blknum = case_count / self.__st['block_size']
        else:
            blknum = case_count / self.__st['block_size'] + 1

        idx = 1
        test_set_blocks = []
        while idx <= blknum:
            block_data = {}
            block_data["exetype"] = exetype
            block_data["type"] = ctype
            block_data["totalBlk"] = str(blknum)
            block_data["currentBlk"] = str(idx)
            block_data["casecount"] = str(case_count)
            start = (idx - 1) * self.__st['block_size']
            if idx == blknum:
                end = case_count
            else:
                end = idx * self.__st['block_size']
            block_data["cases"] = cases[start:end]
            test_set_blocks.append(block_data)
            idx += 1
        self.__st['async_http'] = WebTestExecThread(
            self.__st['server_url'], self.__st['testsuite_name'],
            test_set_blocks, exetype)
        self.__st['async_http'].start()
        return True

    def run_test(self, sessionid, test_set):
        """
            process the execution for a test set
        """
        if sessionid is None:
            return False
        if not "cases" in test_set:
            return False

        cmdline = 'dlogutil -c'
        exit_code, ret = shell_command(cmdline)
        cmdline = 'dlogutil WRT:D -v time'
        dlogfile = test_set['current_set_name'].replace('.xml', '.dlog')
        self.__st['dlog_file'] = dlogfile
        self.__st['dlog_shell'] = DlogThread(cmdline, dlogfile)
        self.__st['dlog_shell'].start()
        time.sleep(0.5)

        cases = test_set["cases"]
        exetype = test_set["exetype"]
        ctype = test_set["type"]
        if self.__st['test_type'] == "webapi":
            return self.__run_web_test(self.__test_set_name,
                                       exetype, ctype, cases)
        elif self.__st['test_type'] == "jqunit":
            return self.__run_jqt_test(sessionid, self.__test_set_name,
                                       exetype, cases)
        elif self.__st['test_type'] == "coreapi":
            return self.__run_core_test(sessionid, self.__test_set_name,
                                        exetype, cases)
        else:
            LOGGER.info("[ unsupported test type ! ]")
            return False

    def get_test_status(self, sessionid):
        """poll the test task status"""
        if sessionid is None:
            return None
        result = {}
        result["msg"] = []
        global TEST_SERVER_STATUS
        LOCK_OBJ.acquire()
        if "finished" in TEST_SERVER_STATUS:
            result["finished"] = str(TEST_SERVER_STATUS["finished"])
        else:
            result["finished"] = "0"
        TEST_SERVER_STATUS = {"finished": 0}
        LOCK_OBJ.release()

        return result

    def get_test_result(self, sessionid):
        """get the test result for a test set """
        result = {}
        if sessionid is None:
            return result
        try:
            global TEST_SERVER_RESULT
            LOCK_OBJ.acquire()
            result = TEST_SERVER_RESULT
            LOCK_OBJ.release()
        except OSError as error:
            LOGGER.error(
                "[ Error: failed to get test result, error:%s ]\n" % error)
        return result

    def finalize_test(self, sessionid):
        """clear the test stub and related resources"""
        if sessionid is None:
            return False

        global TEST_FLAG
        LOCK_OBJ.acquire()
        TEST_FLAG = 1
        LOCK_OBJ.release()

        # add dlog output for debug
        if self.__st['debug_mode']:
            _print_dlog(self.__st['dlog_file'])

        # uninstall widget
        if self.__st['test_type'] == "webapi" and self.__st['auto_iu']:
            cmd = WRT_UNINSTL_STR % self.__st['test_wgt']
            exit_code, ret = shell_command(cmd)
        return True


def get_target_conn():
    """ Get connection for Test Target"""
    return TizenPC()

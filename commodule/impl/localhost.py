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
# Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA  02110-1301, USA.
#
# Authors:
#           Liu,chengtao <chengtaox.liu@intel.com>
""" The implementation for local mode"""

import os
import time
import threading
import re
import uuid
import ConfigParser
from datetime import datetime
from commodule.log import LOGGER
from commodule.httprequest import get_url, http_request
from commodule.autoexec import shell_command, shell_command_ext


DATE_FORMAT_STR = "%Y-%m-%d %H:%M:%S"
HOST_NS = "127.0.0.1"
CNT_RETRY = 10
os.environ["no_proxy"] = HOST_NS

LOCK_OBJ = threading.Lock()
TEST_SERVER_RESULT = {}
TEST_SERVER_STATUS = {}
TEST_FLAG = 0


def _set_result(cases_list=None):
    """set cases result to the global result buffer"""
    global TEST_SERVER_RESULT
    if not cases_list is None:
        LOCK_OBJ.acquire()
        TEST_SERVER_RESULT["cases"].extend(cases_list)
        LOCK_OBJ.release()
    else:
        LOCK_OBJ.acquire()
        TEST_SERVER_RESULT = {'cases': []}
        LOCK_OBJ.release()


def _print_result(suite_name, cases_list):
    if suite_name is None:
        suite_name = ""
    for case_it in cases_list:
        LOGGER.info("execute case: %s # %s...(%s)" % (
            suite_name, case_it['case_id'], case_it['result']))
        if case_it['result'].lower() in ['fail', 'block'] and \
                'stdout' in case_it:
            LOGGER.info(case_it['stdout'])


def _set_finished(flag=0):
    global TEST_SERVER_STATUS
    LOCK_OBJ.acquire()
    TEST_SERVER_STATUS = {"finished": flag}
    LOCK_OBJ.release()


def _get_test_options(test_launcher, test_suite):
    """get test option dict """
    test_opt = {}
    suite_id = None
    if test_launcher.find('WRTLauncher') != -1:
        test_opt["launcher"] = "wrt-launcher"
        cmd = "wrt-launcher -l | grep %s | awk '{print $2\":\"$NF}'" \
            % test_suite
        exit_code, ret = shell_command(cmd)
        for line in ret:
            items = line.split(':')
            if len(items) > 1 and items[0] == test_suite:
                suite_id = items[1].strip('\r\n')
                break

        if suite_id is None:
            LOGGER.info("[ test suite \"%s\" not found in target ]"
                        % test_suite)
            return None
        else:
            test_opt["suite_id"] = suite_id

    else:
        test_opt["launcher"] = test_launcher

    test_opt["suite_name"] = test_suite
    return test_opt


class CoreTestExecThread(threading.Thread):

    """sdb communication for serve_forever app in async mode"""

    def __init__(self, device_id, test_set_name, exetype, test_cases):
        super(CoreTestExecThread, self).__init__()
        self.test_set_name = test_set_name
        self.cases_queue = test_cases
        self.device_id = device_id
        self.exetype = exetype

    def run(self):
        """run core tests"""
        if self.cases_queue is None:
            return
        total_count = len(self.cases_queue)
        current_idx = 0
        manual_skip_all = False
        result_list = []
        _set_result()
        _set_finished()
        global TEST_FLAG
        for test_case in self.cases_queue:
            if TEST_FLAG == 1:
                break
            current_idx += 1
            core_cmd = ""
            if "entry" in test_case:
                core_cmd = test_case["entry"]
            else:
                LOGGER.info(
                    "[ Warnning: test script is empty,"
                    " please check your test xml file ]")
                continue
            expected_result = test_case.get('expected_result', '0')
            time_out = int(test_case.get('timeout', '90'))
            measures = test_case.get('measures', [])
            retmeasures = []
            LOGGER.info("\n[case] execute case:\nTestCase: %s\nTestEntry: %s\n"
                        "Expected Result: %s\nTotal: %s, Current: %s" % (
                        test_case['case_id'], test_case['entry'],
                        expected_result, total_count, current_idx))
            LOGGER.info("[ execute test script,"
                        "this might take some time, please wait ]")
            strtime = datetime.now().strftime(DATE_FORMAT_STR)
            LOGGER.info("start time: %s" % strtime)
            test_case["start_at"] = strtime
            if self.exetype == 'auto':
                return_code, stdout, stderr = shell_command_ext(
                    cmd=core_cmd, timeout=time_out, boutput=False)
                if return_code is not None and return_code != "timeout":
                    test_case["result"] = "pass" if str(return_code) == expected_result else "fail"
                    test_case["stdout"] = stdout
                    test_case["stderr"] = stderr
                    for item in measures:
                        ind = item['name']
                        fname = item['file']
                        if fname and os.path.exists(fname):
                            try:
                                config = ConfigParser.ConfigParser()
                                config.read(fname)
                                item['value'] = config.get(ind, 'value')
                                retmeasures.append(item)
                            except IOError as error:
                                LOGGER.error(
                                    "[ Error: failed to parse value,"
                                    " error: %s ]\n" % error)
                    test_case["measures"] = retmeasures
                else:
                    test_case["result"] = "BLOCK"
                    test_case["stdout"] = stdout
                    test_case["stderr"] = stderr
            elif self.exetype == 'manual':
                # handle manual core cases
                try:
                    # LOGGER.infopre-condition info
                    if "pre_condition" in test_case:
                        LOGGER.info("\n****\nPre-condition: %s\n ****\n"
                                    % test_case[
                                    'pre_condition'])
                    # LOGGER.infostep info
                    if "steps" in test_case:
                        for step in test_case['steps']:
                            LOGGER.info(
                                "********************\nStep Order: %s"
                                % step['order'])
                            LOGGER.info("Step Desc: %s" % step['step_desc'])
                            LOGGER.info(
                                "Expected: %s\n********************\n"
                                % step['expected'])
                    if manual_skip_all:
                        test_case["result"] = "N/A"
                    else:
                        while True:
                            test_result = raw_input(
                                '[ please input case result ] '
                                '(p^PASS, f^FAIL, b^BLOCK, n^Next, d^Done):')
                            if test_result.lower() == 'p':
                                test_case["result"] = "PASS"
                                break
                            elif test_result.lower() == 'f':
                                test_case["result"] = "FAIL"
                                break
                            elif test_result.lower() == 'b':
                                test_case["result"] = "BLOCK"
                                break
                            elif test_result.lower() == 'n':
                                test_case["result"] = "N/A"
                                break
                            elif test_result.lower() == 'd':
                                manual_skip_all = True
                                test_case["result"] = "N/A"
                                break
                            else:
                                LOGGER.info(
                                    "[ Warning: you input: '%s' is invalid,"
                                    " please try again ]" % test_result)
                except IOError as error:
                    LOGGER.error(
                        "[ Error: fail to get core manual test step,"
                        " error: %s ]\n" % error)
            strtime = datetime.now().strftime(DATE_FORMAT_STR)
            LOGGER.info("end time: %s" % strtime)
            test_case["end_at"] = strtime
            LOGGER.info("Case Result: %s" % test_case["result"])
            result_list.append(test_case)

        _set_result(result_list)
        _set_finished(1)


class WebTestExecThread(threading.Thread):

    """execute web test in async mode"""

    def __init__(self, server_url, test_suite_name, test_data_queue):
        super(WebTestExecThread, self).__init__()
        self.server_url = server_url
        self.test_suite_name = test_suite_name
        self.data_queue = test_data_queue

    def run(self):
        """run web tests"""
        if self.data_queue is None:
            return

        test_set_finished = False
        err_cnt = 0
        _set_result()
        _set_finished()
        global TEST_FLAG
        for test_block in self.data_queue:
            ret = http_request(get_url(
                self.server_url, "/set_testcase"), "POST", test_block, 30)
            if ret is None or "error_code" in ret:
                LOGGER.error(
                    "[ set testcases time out,"
                    "please confirm target is available ]")
                LOCK_OBJ.acquire()
                TEST_SERVER_STATUS = {"finished": 1}
                LOCK_OBJ.release()
                break

            while True:
                ret = http_request(
                    get_url(self.server_url, "/check_server_status"),
                    "GET", {})

                if TEST_FLAG == 1:
                    test_set_finished = True
                    break

                if ret is None or "error_code" in ret:
                    err_cnt += 1
                    if err_cnt >= CNT_RETRY:
                        LOGGER.error(
                            "[ check status time out,"
                            "please confirm target is available ]")
                        test_set_finished = True
                        _set_finished(1)
                        break

                if "finished" in ret:
                    err_cnt = 0
                    if 'cases' in ret and ret['cases'] is not None:
                        _set_result(ret["cases"])
                        _print_result(self.test_suite_name, ret["cases"])

                    if ret["finished"] == 1:
                        test_set_finished = True
                        _set_finished(1)
                        break
                    elif ret["block_finished"] == 1:
                        break

                time.sleep(2)

            if test_set_finished:
                break


class HostCon:

    """ Implementation for transfer data to Test Target in Local Host"""

    def __init__(self):
        self.__test_set_block = 300
        self.__device_id = None
        self.__server_url = None
        self.__test_async_shell = None
        self.__test_async_http = None
        self.__test_async_core = None
        self.__test_type = None

    def get_device_ids(self):
        """get deivce list of ids"""
        return ['localhost']

    def get_device_info(self, deviceid=None):
        """get tizen deivce inforamtion"""
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
        exit_code, ret = shell_command("cat /etc/issue")
        for line in ret:
            if len(line) > 1:
                os_version_str = "%s %s" % (os_version_str, line)
        os_version_str = os_version_str[0:-1]

        # get build id
        exit_code, ret = shell_command("cat /etc/os-release")
        for line in ret:
            if line.find("BUILD_ID=") != -1:
                build_id_str = line.split('=')[1].strip('\"\r\n')

        device_info["device_id"] = 'localhost'
        device_info["resolution"] = resolution_str
        device_info["screen_size"] = screen_size_str
        device_info["device_model"] = device_model_str
        device_info["device_name"] = device_name_str
        device_info["os_version"] = os_version_str
        device_info["build_id"] = build_id_str
        return device_info

    def __init_webtest_opt(self, params):
        """init the test runtime, mainly process the star up of test stub"""
        if params is None:
            return None

        session_id = str(uuid.uuid1())
        debug_opt = ""
        test_opt = None
        capability_opt = None
        stub_app = params["stub-name"]
        stub_port = "8000"
        test_launcher = params["external-test"]
        testsuite_name = params["testsuite-name"]
        self.test_suite_name = testsuite_name

        if "debug" in params and params["debug"]:
            debug_opt = "--debug"

        if "capability" in params:
            capability_opt = params["capability"]

        test_opt = _get_test_options(test_launcher, testsuite_name)
        if test_opt is None:
            return None

        # init testkit-stub deamon process
        timecnt = 0
        blaunched = False
        while timecnt < 3:
            exit_code, ret = shell_command(
                "ps ax | grep %s | grep -v grep" % stub_app)
            if len(ret) < 1:
                LOGGER.info("[ attempt to launch stub: %s ]" % stub_app)
                cmdline = "%s --port:%s %s" % (stub_app, stub_port, debug_opt)
                exit_code, ret = shell_command(cmdline)
                timecnt += 1
                time.sleep(2)
            else:
                blaunched = True
                break

        if not blaunched:
            LOGGER.info("[ init test stub failed, please check target! ]")
            return None

        self.__server_url = "http://%s:%s" % (HOST_NS, stub_port)

        timecnt = 0
        blaunched = False
        while timecnt < CNT_RETRY:
            ret = http_request(get_url(self.__server_url,
                                       "/check_server_status"), "GET", {})
            if ret is None:
                LOGGER.info("[ check server status, not ready yet! ]")
                time.sleep(1)
                timecnt += 1
                continue

            if "error_code" in ret:
                LOGGER.info("[ check server status, "
                            "get error code %d ! ]" % ret["error_code"])
                return None
            else:
                LOGGER.info("[ check server status, get ready! ]")
                blaunched = True
            break

        if blaunched:
            ret = http_request(get_url(self.__server_url,
                                       "/init_test"),
                               "POST", test_opt)
            if "error_code" in ret:
                LOGGER.info("[ init test suite, "
                            "get error code %d ! ]" % ret["error_code"])
                return None

            if capability_opt is not None:
                ret = http_request(get_url(self.__server_url,
                                           "/set_capability"),
                                   "POST", capability_opt)
            return session_id
        else:
            LOGGER.info("[ connect to server timeout! ]")
            return None

    def init_test(self, deviceid, params):
        """init the test envrionment"""
        self.__device_id = deviceid
        self.__test_set_name = ""
        global TEST_FLAG
        LOCK_OBJ.acquire()
        TEST_FLAG = 0
        LOCK_OBJ.release()
        if "testset-name" in params:
            self.__test_set_name = params["testset-name"]
        if "client-command" in params and params['client-command'] is not None:
            self.__test_type = "webapi"
            return self.__init_webtest_opt(params)
        else:
            self.__test_type = "coreapi"
            return str(uuid.uuid1())

    def __run_core_test(self, test_set_name, exetype, cases):
        """
            process the execution for core api test
        """
        self.__test_async_core = CoreTestExecThread(
            self.__device_id, test_set_name, exetype, cases)
        self.__test_async_core.start()
        return True

    def __run_web_test(self, test_set_name, exetype, ctype, cases):
        """
            process the execution for web api test
            with the unit size defined by block_size
        """
        case_count = len(cases)
        blknum = 0
        if case_count % self.__test_set_block == 0:
            blknum = case_count / self.__test_set_block
        else:
            blknum = case_count / self.__test_set_block + 1

        idx = 1
        test_set_blocks = []
        while idx <= blknum:
            block_data = {}
            block_data["exetype"] = exetype
            block_data["type"] = ctype
            block_data["totalBlk"] = str(blknum)
            block_data["currentBlk"] = str(idx)
            block_data["casecount"] = str(case_count)
            start = (idx - 1) * self.__test_set_block
            if idx == blknum:
                end = case_count
            else:
                end = idx * self.__test_set_block
            block_data["cases"] = cases[start:end]
            test_set_blocks.append(block_data)
            idx += 1
        self.__test_async_http = WebTestExecThread(
            self.__server_url, self.test_suite_name, test_set_blocks)
        self.__test_async_http.start()
        return True

    def run_test(self, sessionid, test_set):
        """
            process the execution for a test set
        """
        if sessionid is None:
            return False
        if not "cases" in test_set:
            return False

        test_set_name = self.__test_set_name
        cases = test_set["cases"]
        exetype = test_set["exetype"]
        ctype = test_set["type"]
        if self.__test_type == "webapi":
            return self.__run_web_test(test_set_name, exetype, ctype, cases)
        else:
            return self.__run_core_test(test_set_name, exetype, cases)

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
                "[ Error: failed to get test result, error: %s ]\n" % error)

        return result

    def finalize_test(self, sessionid):
        """clear the related resources"""
        if sessionid is None:
            return False

        global TEST_FLAG
        LOCK_OBJ.acquire()
        TEST_FLAG = 1
        LOCK_OBJ.release()

        # uninstall widget
        if self.__st['test_type'] == "webapi" and self.__st['auto_iu']:
            cmd = WRT_UNINSTL_STR % (self.__st[
                                     'device_id'], self.__st['test_wgt'])
            exit_code, ret = shell_command(cmd)
        return True


def get_target_conn():
    """ Get connection for Test Target"""
    return HostCon()

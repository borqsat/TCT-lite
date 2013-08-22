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
""" The implementation test worker"""

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


CNT_RETRY = 10
LOCK_OBJ = threading.Lock()
TEST_SERVER_RESULT = {}
TEST_SERVER_STATUS = {}
TEST_FLAG = 0
DATE_FORMAT_STR = "%Y-%m-%d %H:%M:%S"


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


def _print_dlog(dlog_file):
    if not os.path.exists(dlog_file):
        return
    LOGGER.info('[ start of dlog message ]')
    rbuffile1 = file(dlog_file, "r")
    for line in rbuffile1.readlines():
        LOGGER.info(line.strip('\n'))
    LOGGER.info('[ end of dlog message ]')


def _set_finished(flag=0):
    global TEST_SERVER_STATUS
    LOCK_OBJ.acquire()
    TEST_SERVER_STATUS = {"finished": flag}
    LOCK_OBJ.release()


def _set_finished(flag=0):
    global TEST_SERVER_STATUS
    LOCK_OBJ.acquire()
    TEST_SERVER_STATUS = {"finished": flag}
    LOCK_OBJ.release()


class CoreTestWorker(threading.Thread):

    """ execute core test in async mode """

    def __init__(self, testclient, test_set_name, exetype, test_cases):
        super(CoreTestWorker, self).__init__()
        self.conn = testclient
        self.test_set_name = test_set_name
        self.cases_queue = test_cases
        self.exetype = exetype

    def run(self):
        """run core tests"""
        if self.cases_queue is None:
            return
        total_count = len(self.cases_queue)
        current_idx = 0
        manual_skip_all = False
        global TEST_FLAG
        result_list = []
        _set_result()
        _set_finished()
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
            LOGGER.info("\n[core test] execute case:\nTestCase: %s\n"
                        "TestEntry: %s\nExpected: %s\nTotal: %s, Current: %s"
                        % (test_case['case_id'], test_case['entry'],
                        expected_result, total_count, current_idx))
            LOGGER.info("[ execute core test script, please wait ! ]")
            strtime = datetime.now().strftime(DATE_FORMAT_STR)
            LOGGER.info("start time: %s" % strtime)
            test_case["start_at"] = strtime
            if self.exetype == 'auto':
                return_code, stdout, stderr = self.conn.shell_cmd_ext(core_cmd, time_out, False)
                if return_code is not None and return_code != "timeout":
                    test_case["result"] = "pass" if str(return_code) == expected_result else "fail"
                    test_case["stdout"] = stdout
                    test_case["stderr"] = stderr
                    for item in measures:
                        ind = item['name']
                        fname = item['file']
                        if fname is None:
                            continue
                        tmpname = os.path.expanduser(
                            "~") + os.sep + "measure_tmp"
                        if _download_file(self.device_id, fname, tmpname):
                            try:
                                config = ConfigParser.ConfigParser()
                                config.read(tmpname)
                                item['value'] = config.get(ind, 'value')
                                retmeasures.append(item)
                                os.remove(tmpname)
                            except IOError as error:
                                LOGGER.error(
                                    "[ Error: fail to parse value,"
                                    " error:%s ]\n" % error)
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
                                    % test_case['pre_condition'])
                    # LOGGER.infostep info
                    if "steps" in test_case:
                        for step in test_case['steps']:
                            LOGGER.info(
                                "********************\n"
                                "Step Order: %s" % step['order'])
                            LOGGER.info("Step Desc: %s" % step['step_desc'])
                            LOGGER.info(
                                "Expected: %s\n********************\n"
                                % step['expected'])
                    if manual_skip_all:
                        test_case["result"] = "N/A"
                    else:
                        while True:
                            test_result = raw_input(
                                '[ please input case result ]'
                                ' (p^PASS, f^FAIL, b^BLOCK, n^Next, d^Done):')
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
                                    "[ Warnning: you input: '%s' is invalid,"
                                    " please try again ]" % test_result)
                except IOError as error:
                    LOGGER.info(
                        "[ Error: fail to get core manual test step,"
                        " error: %s ]\n" % error)
            strtime = datetime.now().strftime(DATE_FORMAT_STR)
            LOGGER.info("end time: %s" % strtime)
            test_case["end_at"] = strtime
            LOGGER.info("Case Result: %s" % test_case["result"])
            result_list.append(test_case)

        _set_result(result_list)
        _set_finished(1)


class WebTestWorker(threading.Thread):

    """execute web test in async mode"""

    def __init__(self, server_url, test_suite_name, test_data_queue, exetype):
        super(WebTestWorker, self).__init__()
        self.server_url = server_url
        self.test_suite_name = test_suite_name
        self.data_queue = test_data_queue
        self.test_type = exetype

    def run(self):
        """run web tests"""
        if self.data_queue is None:
            return

        test_set_finished = False
        err_cnt = 0
        exetype = self.test_type.lower()
        global TEST_FLAG
        _set_result()
        _set_finished()
        for test_block in self.data_queue:
            ret = http_request(get_url(
                self.server_url, "/set_testcase"), "POST", test_block, 30)
            if ret is None or "error_code" in ret:
                LOGGER.error(
                    "[ set testcases time out,"
                    "please confirm target is available ]")
                _set_finished(1)
                break

            while True:
                if TEST_FLAG == 1:
                    test_set_finished = True
                    break

                ret = http_request(
                    get_url(self.server_url, "/check_server_status"),
                    "GET", {})

                if ret is None or "error_code" in ret:
                    err_cnt += 1
                    if err_cnt >= CNT_RETRY:
                        LOGGER.error(
                            "[ check server status time out,"
                            " please confirm device is available ]")
                        test_set_finished = True
                        _set_finished(1)
                        break

                elif "finished" in ret:
                    err_cnt = 0
                    if 'cases' in ret and ret["cases"] is not None\
                            and len(ret["cases"]):
                        _set_result(ret["cases"])
                        _print_result(self.test_suite_name, ret["cases"])
                    elif exetype == 'manual':
                        LOGGER.info(
                            "[ executing manual cases,"
                            " please take care of device ]\r\n")

                    if ret["finished"] == 1:
                        test_set_finished = True
                        _set_finished(1)
                        break
                    elif ret["block_finished"] == 1:
                        break
                time.sleep(2)

            if test_set_finished:
                break

UIFW_RESULT = "/opt/media/Documents/tcresult.xml"


class QUTestWorker(threading.Thread):
    """execute Jquery Unit test suite """

    def __init__(self, testclient, sessionid="", test_set="", cases=None):
        super(QUTestWorker, self).__init__()
        self.conn = testclient
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
        ls_cmd = "ls -l %s" % UIFW_RESULT
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
            exit_code, ret = self.conn.shell_cmd(ls_cmd)
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
                result_file = os.path.expanduser(
                    "~") + os.sep + self.test_session + "_uifw.xml"
                b_ok = self.conn.download_file(UIFW_RESULT, result_file)
                if b_ok:
                    LOCK_OBJ.acquire()
                    TEST_SERVER_RESULT = {"resultfile": result_file}
                    LOCK_OBJ.release()
                break
        LOGGER.info('[webuifw] end test execution...')
        _set_finished(1)


class TestWorker(object):
    """Test executor for testkit-lite"""

    def __init__(self, client=None):
        super(TestWorker, self).__init__()
        self.conn = client
        self.server_url = None
        self.opts = dict({'async_stub': None,
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

    def __init_test_stub(self, stub_app, stub_port, debug_opt):
        # init testkit-stub deamon process
        timecnt = 0
        blaunched = False
        while timecnt < 3:
            if not self.conn.check_process(stub_app):
                LOGGER.info("[ attempt to launch stub: %s ]" % stub_app)
                cmdline = "%s --port:%s %s" % (stub_app, stub_port, debug_opt)
                exit_code, ret = self.conn.shell_cmd(cmdline)
                time.sleep(2)
                timecnt += 1
            else:
                blaunched = True
                break

        if not blaunched:
            LOGGER.info("[ init test stub failed, please check target! ]")
            return blaunched

        if self.server_url is None:
            self.server_url = self.conn.get_server_url(stub_port)

        timecnt = 0
        while timecnt < CNT_RETRY:
            ret = http_request(get_url(
                self.server_url, "/check_server_status"), "GET", {})
            if ret is None:
                LOGGER.info("[ check server status, not ready yet! ]")
                timecnt += 1
                time.sleep(1)
                continue
            if "error_code" in ret:
                LOGGER.info("[ check server status, get error code %d ! ]" % ret["error_code"])
                return False
            else:
                blaunched = True
                break
        return blaunched

    def __init_webtest_opt(self, params):
        """init the test runtime, mainly process the star up of test stub"""
        if params is None:
            return None

        session_id = str(uuid.uuid1())
        cmdline = ""
        debug_opt = ""
        stub_app = params.get('stub-name', 'testkit-stub')
        stub_port = params.get('stub-port', '8000')
        test_launcher = params.get('external-test', '')
        testsuite_name = params.get('testsuite-name', '')
        testset_name = params.get('testset-name', '')
        capability_opt = params.get("capability", None)
        client_cmds = params.get('client-command', '').strip().split()

        wrt_tag = client_cmds[1] if len(client_cmds) > 1 else ""
        self.opts['auto_iu'] = auto_iu = wrt_tag.find('iu') != -1
        self.opts['self_exec'] = wrt_tag.find('a') != -1
        self.opts['self_repeat'] = wrt_tag.find('r') != -1
        self.opts['testsuite_name'] = testsuite_name
        self.opts['debug_mode'] = params.get("debug", False)
        fuzzy_match = wrt_tag.find('z') != -1

        # uifw, this suite is duplicated
        if self.opts['self_repeat']:
            self.opts['test_type'] = "jqunit"
            return session_id

        # uifw, this suite is self execution
        if self.opts['self_exec']:
            self.opts['test_type'] = "jqunit"

        test_opt = self.conn.get_launcher_opt(test_launcher, testsuite_name, testset_name, fuzzy_match, auto_iu)
        if test_opt is None:
            LOGGER.info("[ init the test options, get failed ]")
            return None

        self.opts['test_wgt'] = test_opt['suite_id']

        # self executed test suite don't need stub server
        if self.opts['self_exec']:
            return session_id

        # enable debug information
        if self.opts['debug_mode']:
            debug_opt = '--debug'

        if self.__init_test_stub(stub_app, stub_port, debug_opt):
            ret = http_request(get_url(
                self.server_url, "/init_test"), "POST", test_opt)
            if ret is None:
                LOGGER.info("[ init test suite failed! ]")
                return None
            elif "error_code" in ret:
                LOGGER.info("[ init test suite, "
                            "get error code %d ! ]" % ret["error_code"])
                return None

            if capability_opt is not None:
                ret = http_request(get_url(self.server_url,
                                           "/set_capability"),
                                   "POST", capability_opt)
            return session_id
        else:
            LOGGER.info("[ Init test stub failed ! ]")
            return None

    def init_test(self, params):
        """init the test envrionment"""
        self.__test_set_name = ""

        global TEST_FLAG
        LOCK_OBJ.acquire()
        TEST_FLAG = 0
        LOCK_OBJ.release()

        if "testset-name" in params:
            self.__test_set_name = params["testset-name"]
        if "client-command" in params and params['client-command'] is not None:
            self.opts['test_type'] = "webapi"
            return self.__init_webtest_opt(params)
        else:
            self.opts['test_type'] = "coreapi"
            return str(uuid.uuid1())

    def __run_core_test(self, sessionid, test_set_name, exetype, cases):
        """
            process the execution for core api test
        """
        self.opts['async_core'] = CoreTestWorker(self.conn, test_set_name, exetype, cases)
        self.opts['async_core'].start()
        return True

    def __run_jqt_test(self, sessionid, test_set_name, exetype, cases):
        """
            process the execution for Qunit testing
        """
        global TEST_SERVER_RESULT, TEST_SERVER_STATUS
        if self.opts['self_exec']:
            if self.conn.check_widget_process(self.opts['test_wgt']):
                self.opts['async_shell'] = QUTestWorker(self.conn,
                                                        sessionid,
                                                        test_set_name,
                                                        cases)
                self.opts['async_shell'].start()
            else:
                LOGGER.info(
                    "[ launch widget \"%s\" failed! ]" % self.opts['test_wgt'])
                TEST_SERVER_STATUS = {"finished": 1}
                TEST_SERVER_RESULT = {"resultfile": ""}
            return True

        if self.opts['self_repeat']:
            result_file = os.path.expanduser(
                "~") + os.sep + sessionid + "_uifw.xml"
            b_ok = self.conn.download_file(UIFW_RESULT, result_file)
            for test_case in cases:
                LOGGER.info("[uifw] execute case: %s # %s"
                            % (test_set_name, test_case['case_id']))

            if b_ok:
                TEST_SERVER_RESULT = {"resultfile": result_file}
                TEST_SERVER_STATUS = {"finished": 1}
            else:
                TEST_SERVER_RESULT = {"resultfile": ""}
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
        if case_count % self.opts['block_size'] == 0:
            blknum = case_count / self.opts['block_size']
        else:
            blknum = case_count / self.opts['block_size'] + 1

        idx = 1
        test_set_blocks = []
        while idx <= blknum:
            block_data = {}
            block_data["exetype"] = exetype
            block_data["type"] = ctype
            block_data["totalBlk"] = str(blknum)
            block_data["currentBlk"] = str(idx)
            block_data["casecount"] = str(case_count)
            start = (idx - 1) * self.opts['block_size']
            if idx == blknum:
                end = case_count
            else:
                end = idx * self.opts['block_size']
            block_data["cases"] = cases[start:end]
            test_set_blocks.append(block_data)
            idx += 1
        self.opts['async_http'] = WebTestWorker(self.server_url, 
                                                self.opts['testsuite_name'],
                                                test_set_blocks, exetype)
        self.opts['async_http'].start()
        return True

    def run_test(self, sessionid, test_set):
        """
            process the execution for a test set
        """
        if sessionid is None:
            return False
        if not "cases" in test_set:
            return False

        # start debug thread
        dlogfile = test_set['current_set_name'].replace('.xml', '.dlog')
        self.opts['dlog_file'] = dlogfile
        self.conn.start_debug(self.opts['dlog_file'])
        time.sleep(0.5)

        cases, exetype, ctype = test_set["cases"], test_set["exetype"], test_set["type"]
        if self.opts['test_type'] == "webapi":
            return self.__run_web_test(self.__test_set_name,exetype, ctype, cases)
        elif self.opts['test_type'] == "coreapi":
            return self.__run_core_test(sessionid, self.__test_set_name, exetype, cases)
        elif self.opts['test_type'] == "jqunit":
            return self.__run_jqt_test(sessionid, self.__test_set_name, exetype, cases)
        else:
            LOGGER.info("[ unsupported test suite type ! ]")
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

        # uninstall widget
        if self.opts['test_type'] == "webapi" and self.opts['auto_iu']:
            self.conn.uninstall_widget(self.opts['test_wgt'])

        # stop debug thread
        self.conn.stop_debug()

        # add dlog output for debug
        if self.opts['debug_mode']:
            _print_dlog(self.opts['dlog_file'])

        return True

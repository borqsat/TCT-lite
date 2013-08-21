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
""" The implementation for HD (host device) test mode"""

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

APP_QUERY_STR = "sdb -s %s shell ps aux | grep '%s' | awk '{print $2}'"
APP_KILL_STR = "sdb -s %s shell kill -9 %s"
WRT_INSTALL_STR = "sdb -s %s shell wrt-installer -i /opt/%s/%s.wgt"
WRT_QUERY_STR = "sdb -s %s shell wrt-launcher -l | grep '%s'|awk '{print $2\":\"$NF}'"
WRT_START_STR = "sdb -s %s shell wrt-launcher -s %s"
WRT_KILL_STR = "sdb -s %s shell wrt-launcher -k %s"
WRT_UNINSTL_STR = "sdb -s %s shell wrt-installer -un %s"
UIFW_RESULT = "/opt/media/Documents/tcresult.xml"


class TizenMobile:

    """ Implementation for transfer data
        between Host and Tizen Mobile Device
    """

    def __init__(self, deviceid=None):
        self._device_id = deviceid

    def get_device_ids(self):
        """get tizen deivce list of ids"""
        result = []
        exit_code, ret = shell_command("sdb devices")
        for line in ret:
            if str.find(line, "\tdevice") != -1:
                result.append(line.split("\t")[0])
        return result

    def get_device_info(self):
        """get tizen deivce inforamtion"""
        device_info = {}
        resolution_str = ""
        screen_size_str = ""
        device_model_str = ""
        device_name_str = ""
        build_id_str = ""
        os_version_str = ""

        # get resolution and screen size
        exit_code, ret = shell_command("sdb -s %s shell xrandr" % deviceid)
        pattern = re.compile("connected (\d+)x(\d+).* (\d+mm) x (\d+mm)")
        for line in ret:
            match = pattern.search(line)
            if match:
                resolution_str = "%s x %s" % (match.group(1), match.group(2))
                screen_size_str = "%s x %s" % (match.group(3), match.group(4))

        # get architecture
        exit_code, ret = shell_command("sdb -s %s shell uname -m" % deviceid)
        if len(ret) > 0:
            device_model_str = ret[0]

        # get hostname
        exit_code, ret = shell_command("sdb -s %s shell uname -n" % deviceid)
        if len(ret) > 0:
            device_name_str = ret[0]

        # get os version
        exit_code, ret = shell_command(
            "sdb -s %s shell cat /etc/issue" % deviceid)
        for line in ret:
            if len(line) > 1:
                os_version_str = "%s %s" % (os_version_str, line)

        # get build id
        exit_code, ret = shell_command(
            "sdb -s %s shell cat /etc/os-release" % deviceid)
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


    def get_forward_connect(remote_port=None):
        """forward request a host tcp port to targe tcp port"""
        if remote_port is None:
            return None

        os.environ['no_proxy'] = LOCAL_HOST_NS
        host = LOCAL_HOST_NS
        inner_port = 9000
        time_out = 2
        bflag = False
        while True:
            sock_inner = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock_inner.settimeout(time_out)
            try:
                sock_inner.bind((host, inner_port))
                sock_inner.close()
                bflag = False
            except socket.error as error:
                if error.errno == 98 or error.errno == 13:
                    bflag = True
            if bflag:
                inner_port += 1
            else:
                break
        host_port = str(inner_port)
        cmd = "sdb -s %s forward tcp:%s tcp:%s" % \
            (deviceid, host_port, remote_port)
        exit_code, ret = shell_command(cmd)
        url_forward = "http://%s:%s" % (host, host_port)
        return url_forward


    def download_file(remote_path, local_path):
        """download file from device"""
        cmd = "sdb -s %s pull %s %s" % (deviceid, remote_path, local_path)
        exit_code, ret = shell_command(cmd)
        if exit_code != 0:
            error = ret[0].strip('\r\n') if len(ret) else "sdb shell timeout"
            LOGGER.info("[ Download file \"%s\" from target failed, error: %s ]"
                        % (remote_path, error))
            return False
        else:
            return True


    def upload_file(remote_path, local_path):
        """upload file to device"""
        cmd = "sdb -s %s push %s %s" % (deviceid, local_path, remote_path)
        exit_code, ret = shell_command(cmd)
        if exit_code != 0:
            error = ret[0].strip('\r\n') if len(ret) else "sdb shell timeout"
            LOGGER.info("[ Upload file \"%s\" failed,"
                        " get error: %s ]" % (local_path, error))
            return False
        else:
            return True

    def install_package(self, deviceid, pkgpath):
        """install a package on tizen device:
        push package and install with shell command
        """
        cmd = "sdb -s %s shell rpm -ivh %s" % (deviceid, pkgpath)
        exit_code, ret = shell_command(cmd)
        return ret

    def get_installed_package(self, deviceid):
        """get list of installed package from device"""
        cmd = "sdb -s %s shell rpm -qa | grep tct" % (deviceid)
        exit_code, ret = shell_command(cmd)
        return ret

    def download_file(self, deviceid, remote_path, local_path):
        """download file from device"""
        return _download_file(deviceid, remote_path, local_path)

    def upload_file(self, deviceid, remote_path, local_path):
        """upload file to device"""
        return _upload_file(deviceid, remote_path, local_path)

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
                cmd = WRT_INSTALL_STR % (deviceid, test_suite, test_wgt)
                exit_code, ret = shell_command(cmd)
                if exit_code == -1:
                    LOGGER.info("[ failed to install widget \"%s\" in target ]"
                                % test_wgt)
                    cmd = APP_QUERY_STR % (deviceid, "wrt-installer -i")
                    exit_code, ret = shell_command(cmd)
                    for line in ret:
                        cmd = APP_KILL_STR % (deviceid, line.strip('\r\n'))
                        exit_code, ret = shell_command(cmd)
                    return None
            else:
                test_wgt = test_suite

            # query the whether test widget is installed ok
            cmd = WRT_QUERY_STR % (deviceid, test_wgt)
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
        stub_app = params.get('stub-name', 'testkit-stub')
        stub_port = params.get('stub-port', '8000')
        test_launcher = params.get('external-test', '')
        testsuite_name = params.get('testsuite-name', '')
        testset_name = params.get('testset-name', '')
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

        # enable debug information
        if self.__st['debug_mode']:
            debug_opt = '--debug'

        # init testkit-stub deamon process
        timecnt = 0
        blaunched = False
        while timecnt < 3:
            exit_code, ret = shell_command(
                APP_QUERY_STR % (deviceid, stub_app))
            if len(ret) < 1:
                LOGGER.info("[ attempt to launch stub: %s ]" % stub_app)
                cmdline = "sdb -s %s shell '%s --port:%s %s; sleep 2s' " \
                    % (deviceid, stub_app, stub_port, debug_opt)
                exit_code, ret = shell_command(cmdline)
                time.sleep(2)
                timecnt += 1
            else:
                blaunched = True
                break

        if not blaunched:
            LOGGER.info("[ init test stub failed, please check target! ]")
            return None

        if self.__st['server_url'] is None:
            self.__st['server_url'] = _get_forward_connect(deviceid, stub_port)

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
            cmdline = WRT_START_STR % (
                self.__st['device_id'], self.__st['test_wgt'])
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
            b_ok = _download_file(self.__st['device_id'],
                                  UIFW_RESULT,
                                  result_file)
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

        cmdline = 'sdb -s %s dlog -c' % self.__st['device_id']
        exit_code, ret = shell_command(cmdline)
        cmdline = 'sdb -s %s dlog WRT:D -v time' % self.__st['device_id']
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

    def uninstall_widget(self, wgt_name):
        cmd = WRT_UNINSTL_STR % (self.__st['device_id'], wgt_name)
        exit_code, ret = shell_command(cmd)
        return True

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
            self.uninstall_widget(self.__st['test_wgt'])
        return True


def get_target_conn():
    """ Get connection for Test Target"""
    return TizenMobile()

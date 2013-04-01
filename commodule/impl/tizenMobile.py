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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# Authors:
#              Liu ChengTao <liux.chengtao@intel.com>

import os
import sys
import time
import socket
import threading
import subprocess
import requests
import json
import re
import uuid

def get_url(baseurl, api):
    """get full url string"""
    return "%s%s" % (baseurl, api)

def http_request(url, rtype="POST", data=None):
    """http request to the device http server"""
    result = None
    if rtype == "POST":
        headers = {'content-type': 'application/json'}
        try:
            ret = requests.post(url, data=json.dumps(data), headers=headers)
            if ret:
                result = ret.json()
        except Exception, e:
            pass
    elif rtype == "GET":
        try:        
            ret = requests.get(url, params=data)
            if ret: 
                result = ret.json()
        except Exception, e:
            pass

    return result

def shell_command(cmdline):
    """sdb communication for quick return in sync mode"""
    proc = subprocess.Popen(cmdline,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    result = proc.stdout.readlines()
    return result

def get_forward_connect(device_id, remote_port=None):
    """forward request a host port to a device-side port"""
    if remote_port is None:
        return None

    HOST = "127.0.0.1"
    inner_port = 9000
    TIME_OUT = 2
    bflag = False
    while True:
        sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sk.settimeout(TIME_OUT)
        try:
            sk.bind((HOST, inner_port))
            sk.close()
            bflag = False
        except socket.error, e:
            if e.errno == 98 or e.errno == 13:
                bflag = True
        if bflag: inner_port += 1
        else: break
    host_port = str(inner_port)
    cmd = "sdb -s %s forward tcp:%s tcp:%s" % \
          (device_id, host_port, remote_port)
    result = shell_command(cmd)
    url_forward = "http://%s:%s" % (HOST, host_port)
    return url_forward

lockobj = threading.Lock()
test_server_result = []
test_server_status = {}
class StubExecThread(threading.Thread):
    """sdb communication for serve_forever app in async mode"""
    def __init__(self, cmd=None, sessionid=None):
        super(StubExecThread, self).__init__()
        self.stdout = []
        self.stderr = []
        self.cmdline = cmd
        self.sessionid = sessionid

    def run(self):        
        BUFFILE1 = os.path.expanduser("~") + os.sep + self.sessionid + "_stdout"
        BUFFILE2 = os.path.expanduser("~") + os.sep + self.sessionid + "_stderr"

        LOOP_DELTA = 0.2
        wbuffile1 = file(BUFFILE1, "w")
        wbuffile2 = file(BUFFILE2, "w")
        rbuffile1 = file(BUFFILE1, "r")
        rbuffile2 = file(BUFFILE2, "r")
        proc = subprocess.Popen(self.cmdline,
                                shell=True,
                                stdout=wbuffile1,
                                stderr=wbuffile2)
        def print_log():
            """
            print the stdout/stderr log
            """
            sys.stdout.write(rbuffile1.read())
            sys.stdout.write(rbuffile2.read())
            sys.stdout.flush()

        rbuffile1.seek(0)
        rbuffile2.seek(0)
        while True:
            if not proc.poll() is None:
                break
            print_log()
            time.sleep(LOOP_DELTA)
        # print left output
        print_log()
        wbuffile1.close()
        wbuffile2.close()
        rbuffile1.close()
        rbuffile2.close()
        os.remove(BUFFILE1)
        os.remove(BUFFILE2)

class TestSetExecThread(threading.Thread):
    """sdb communication for serve_forever app in async mode"""
    def __init__(self, server_url, test_set_name, test_data_queue):
        super(TestSetExecThread, self).__init__()
        self.server_url = server_url
        self.test_set_name = test_set_name
        self.data_queue = test_data_queue
        global test_server_result
        lockobj.acquire()
        test_server_result = {"cases":[]}
        lockobj.release()

    def set_result(self, result_data):
        """set http result response to the result buffer"""
        if not result_data is None:
            global test_server_result
            lockobj.acquire()
            test_server_result["cases"].extend(result_data["cases"])
            lockobj.release()

    def run(self):
        if self.data_queue is None:
            return

        global test_server_status
        set_finished = False
        cur_block = 0
        err_cnt = 0
        total_block = len(self.data_queue)
        for test_block in self.data_queue:
            cur_block += 1
            ret = http_request(get_url(self.server_url, "/init_test"), \
                               "POST", test_block)
            if ret is None or ret is {}:
                break

            while True:
                ret = http_request(get_url(self.server_url, "/check_server_status"), \
                                   "GET", {})
                if ret is None or ret is {}:
                    err_cnt += 1
                    if err_cnt >= 10:
                        lockobj.acquire()
                        test_server_status = {"finished": 1}
                        lockobj.release()
                        break
                elif "finished" in ret:
                    lockobj.acquire()
                    test_server_status = ret
                    lockobj.release()
                    err_cnt = 0
                    print "[ test suite: %s, block: %d/%d , finished: %s ]" % \
                          (self.test_set_name, cur_block, total_block, ret["finished"])
                    ### check if current test set is finished
                    if ret["finished"] == 1:
                        set_finished = True
                        ret = http_request(get_url(self.server_url, "/get_test_result"), \
                                           "GET", {})
                        self.set_result(ret)
                        break
                    ### check if current block is finished
                    elif ret["block_finished"] == 1:
                        ret =  http_request(get_url(self.server_url, "/get_test_result"), \
                                            "GET", {})
                        self.set_result(ret)
                        break
                time.sleep(2)

            if set_finished:
                break

class TizenMobile:
    """ Implementation for transfer data between Host and Tizen Mobile Device"""

    def __init__(self):
        self.__forward_server_url = "http://127.0.0.1:9000"
        self.__test_async_shell = None
        self.__test_async_http = None
        self.__test_set_block = 100
        self.__test_type = None

    def get_device_ids(self):
        """get tizen deivce list of ids"""
        result = []
        ret = shell_command("sdb devices")
        for line in ret:
            if str.find(line, "\tdevice\t") != -1: 
                result.append(line.split("\t")[0])
        return result

    def get_device_info(self, deviceid=None):
        """get tizen deivce inforamtion"""
        device_info = {}
        resolution_str = "Empty resolution"
        screen_size_str = "Empty screen_size"
        device_model_str = "Empty device_model"
        device_name_str = "Empty device_name"
        os_version_str = ""

        # get resolution and screen size
        ret = shell_command("sdb -s %s shell xrandr" % deviceid)
        pattern = re.compile("connected (\d+)x(\d+).* (\d+mm) x (\d+mm)")
        for line in ret:
            match = pattern.search(line)
            if match:
                resolution_str = "%s x %s" % (match.group(1), match.group(2))
                screen_size_str = "%s x %s" % (match.group(3), match.group(4))
        # get architecture
        ret = shell_command("sdb -s %s shell uname -m" % deviceid)
        if len(ret) > 0:
            device_model_str = ret[0]
        # get hostname
        ret = shell_command("sdb -s %s shell uname -n" % deviceid)
        if len(ret) > 0:
            device_name_str = ret[0]
        # get os version
        ret = shell_command("sdb -s %s shell cat /etc/issue" % deviceid)
        for line in ret:
            if len(line) > 1:
                os_version_str = "%s %s" % (os_version_str, line)
        os_version_str = os_version_str[0:-1]
        device_info["resolution"] = resolution_str
        device_info["screen_size"] = screen_size_str
        device_info["device_model"] = device_model_str
        device_info["device_name"] = device_name_str
        device_info["os_version"] = os_version_str
        return device_info

    def install_package(self, deviceid, pkgpath):
        """install a package on tizen device: push package and install with shell command"""
        filename = os.path.split(pkgpath)[1]
        devpath = "/tmp/%s" % filename
        cmd = "sdb -s %s push %s %s" % (deviceid, pkgpath, devpath)
        ret =  shell_command(cmd)
        cmd = "sdb shell rpm -ivh %s" % devpath
        ret =  shell_command(cmd)
        return ret

    def get_installed_package(self, deviceid):
        """get list of installed package from device"""
        cmd = "sdb -s %s shell rpm -qa | grep tct" % (deviceid)
        ret =  shell_command(cmd)
        return ret

    def download_file(self, deviceid, remote_path, local_path):
        """get list of installed package from device"""
        cmd = "sdb -s %s pull %s %s" % (deviceid, remote_path, local_path)
        ret =  shell_command(cmd)
        return ret

    def upload_file(self, deviceid, remote_path, local_path):
        """get list of installed package from device"""
        cmd = "sdb -s %s push %s %s" % (deviceid, local_path, remote_path)
        ret =  shell_command(cmd)
        return ret

    def __init_test_stub(self, deviceid, params):
        """init the test runtime, mainly process the star up of test stub"""
        result = None
        if params is None:
            return result
        stub_name = ""
        stub_server_port = "8000"
        testsuite_name = ""
        client_command = ""       
        stub_name = params["stub-name"]
        capability_opt = None

        if "capability" in params:
            capability_opt = params["capability"]

        if "stub-port" in params:
            stub_server_port = params["stub-port"]

        if not "testsuite-name" in params:
            print "\"testsuite-name\" is required for web tests!"
            return result
        else:
            testsuite_name = params["testsuite-name"]

        if not "client-command" in params:
            print "\"client-command\" is required for web tests!"
            return result
        else:
            client_command = params["client-command"]

        cmd = "sdb -s %s shell wrt-launcher -l | grep %s | awk '{print $NF}'" % \
              (deviceid, testsuite_name)
        ret = shell_command(cmd)
        if len(ret) == 0:
            print "[ test suite \"%s\" not found in device! ]" % testsuite_name
            return result
        else:
            testsuite_name = ret[0].strip('\r\n')

        ###kill the stub process###
        cmd = "sdb shell killall %s " % stub_name
        ret =  shell_command(cmd)
        print "[ waiting for kill http server ]"
        time.sleep(3)

        ###set forward between host and device###        
        self.__forward_server_url = get_forward_connect(deviceid, stub_server_port)
        print "[ forward server %s ]" % self.__forward_server_url

        ###launch an new stub process###
        session_id = str(uuid.uuid1())
        print "[ launch the stub app ]"
        stub_entry = "%s --testsuite:%s --client-command:%s" % \
                     (stub_name, testsuite_name, client_command)
        cmdline = "sdb -s %s shell %s" % (deviceid, stub_entry)
        self.__test_async_shell = StubExecThread(cmd=cmdline, sessionid=session_id)
        self.__test_async_shell.start()
        time.sleep(2)

        ###check if http server is ready for data transfer### 
        timecnt = 0
        while timecnt < 10:
            ret = http_request(get_url(self.__forward_server_url, "/check_server_status"), "GET", {})
            if ret is None:
                print "[ check server status, not ready yet! ]"
                time.sleep(0.3)
                timecnt += 1
            else:
                if "error_code" in ret:
                    result = None
                    print "[ check server status, get error code %d ! ]" % ret["error_code"]
                else:
                    result = session_id
                    print "[ check server status, get ready! ]"
                    if capability_opt is not None:
                        ret = http_request(get_url(self.__forward_server_url, "/set_capability"), "POST", capability_opt)
                break
        return result

    def init_test(self, deviceid, params):
        """init the test envrionment"""
        if params is not None and "stub-name" in params:
            self.__test_type = "webapi"
            return self.__init_test_stub(deviceid, params)
        else:
            self.__test_type = "coreapi"
            return str(uuid.uuid1())

    def __run_core_test(self, test_set_name, exetype, ctype, cases):
        """
            process the execution for core api test
        """
        return True

    def __run_web_test(self, test_set_name, exetype, ctype, cases):
        """
            process the execution for web api test
            may be splitted to serveral blocks, with the unit size defined by block_size
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
            block_data["casecount"] = case_count
            start = (idx - 1) * self.__test_set_block
            if idx == blknum:
                end = case_count
            else:
                end = idx * self.__test_set_block
            block_data["cases"] = cases[start:end]
            test_set_blocks.append(block_data)
            idx += 1
        self.__test_async_http = TestSetExecThread(self.__forward_server_url, test_set_name, test_set_blocks)
        self.__test_async_http.start()
        return True

    # def run_test(self, sessionid, test_set):
    #     """
    #         process the execution for a test set
    #     """
    #     if sessionid is None:
    #         return False
    #     if not "cases" in test_set:
    #         return False
    #     test_set_name = os.path.split(test_set["current_set_name"])[1]
    #     cases = test_set["cases"]
    #     exetype = test_set["exetype"]
    #     ctype = test_set["type"]

    #     if self.__test_type == "webapi":
    #         return self.__run_web_test(test_set_name, exetype, ctype, cases)
    #     else:
    #         return self.__run_core_test(test_set_name, exetype, ctype, cases)

    def run_test(self, sessionid, test_set):
        """
            process the execution for a test set
            may be split to serveral blocks, which decided by the block_size
        """
        if sessionid is None: 
            return False
        if not "casecount" in test_set : 
            return False
        test_set_name = os.path.split(test_set["current_set_name"])[1]
        case_count = int(test_set["casecount"])
        cases = test_set["cases"]

        if case_count % self.__test_set_block == 0:
            blknum = case_count / self.__test_set_block
        else:
            blknum = case_count / self.__test_set_block + 1

        idx = 1
        test_set_blocks = []
        while idx <= blknum:
            block_data = {}
            block_data["totalBlk"] = str(blknum)
            block_data["currentBlk"] = str(idx)
            block_data["casecount"] = test_set["casecount"]
            block_data["exetype"] = test_set["exetype"]
            block_data["type"] = test_set["type"]
            start = (idx - 1) * self.__test_set_block
            if idx == blknum: 
                end = case_count
            else: 
                end = idx * self.__test_set_block
            block_data["cases"] = cases[start:end]
            test_set_blocks.append(block_data)
            idx += 1

        self.__test_async_http = TestSetExecThread(self.__forward_server_url, test_set_name, test_set_blocks)
        self.__test_async_http.start()
        return True

    def get_test_status(self, sessionid):
        """poll the test task status"""
        if sessionid is None: 
            return None
        result = {}
        result["msg"] = []
        global test_server_status
        lockobj.acquire()
        if "finished" in test_server_status:
            result["finished"] = str(test_server_status["finished"])
        else:
            result["finished"] = "0"
        test_server_status = {"finished": 0}
        lockobj.release()

        return result

    def get_test_result(self, sessionid):
        """get the test result for a test set """
        result = {}
        if sessionid is None:
            return result
        try:
            global test_server_result
            lockobj.acquire()
            result = test_server_result
            lockobj.release()
        except Exception, e:
            print e

        return result

    def finalize_test(self, sessionid):
        """clear the test stub and related resources"""
        if sessionid is None: 
            return False

        if self.__test_type == "webapi":
            ret = http_request(get_url(self.__forward_server_url, "/shut_down_server"), "GET", {})
        return True

testremote = TizenMobile()
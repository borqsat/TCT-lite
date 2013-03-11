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
import string
import threading, thread
import subprocess
import requests
import json
import re

def http_request(url, rtype="POST", data=None):
    """http request to the device http server"""
    result = None
    if rtype == "POST":
        headers = {'content-type': 'application/json'}
        try:
            ret = requests.post(url, data=json.dumps(data), headers=headers)
            if ret: 
                result = ret.json()
        except requests.exceptions.ConnectionError:
            result = None
    elif rtype == "GET":
        try:        
            ret = requests.get(url, params=data)
            if ret: 
                result = ret.json()
        except requests.exceptions.ConnectionError:
            result = None

    return result

def shell_command(cmdline):
    """sdb communication for quick return in sync mode"""
    proc = subprocess.Popen(cmdline,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    stdout = proc.stdout.readlines()
    return stdout

test_server_result = []
test_server_status = {}
stdout_buffer = []
stderr_buffer = []
lockobj = threading.Lock()
lockcmd = threading.Lock()

class SdbCommThread(threading.Thread):
    """sdb communication for serve_forever app in async mode"""
    def __init__(self, cmd=None, endflag=None):
        super(SdbCommThread, self).__init__()
        self.stdout = []
        self.stderr = []
        self.cmdline = cmd
        self.endflag = endflag

    def run(self):
        proc = subprocess.Popen(self.cmdline,
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        
        while True:
            outlines, errlines = proc.communicate()

            global stdout_buffer
            lockcmd.acquire()
            stdout_buffer.extend(outlines)
            lockcmd.release()
            # break_flag = False
            # for line in outlines:
            #     if string.find(line, self.endflag) != -1:
            #         break_flag = True
            #         break
            if not proc.poll() is None:
                break
            time.sleep(0.5)

class HttpCommThread(threading.Thread):

    """sdb communication for serve_forever app in async mode"""
    def __init__(self, test_block_queue):
        super(HttpCommThread, self).__init__()
        self.data_queue = test_block_queue
        global test_server_result
        lockobj.acquire()
        test_server_result = {"cases":[]}
        lockobj.release()

    def set_result(self, result_data):
        """set http result response to the result buffer"""
        if "cases" in result_data:
            global test_server_result
            lockobj.acquire()
            test_server_result["cases"].extend(result_data["cases"])
            lockobj.release()

    def run(self):
        if self.data_queue is None:
            return

        set_finished = False
        for test_block in self.data_queue:
            ret = http_request("http://127.0.0.1:8080/init_test", "POST", test_block)
            if ret is None:
                break

            while True:
                ret =  http_request("http://127.0.0.1:8080/check_server_status", "GET", {})
                if ret is None:
                    break

                global test_server_status                    
                lockobj.acquire()
                test_server_status = ret
                lockobj.release()

                ### check if test set is finished
                if ret["finished"] == 1:
                    set_finished = True
                    ret = http_request("http://127.0.0.1:8080/generate_xml", "GET", {})
                    if not ret is None:
                        self.set_result(ret)
                    break
                ### check if current test block is finished
                elif ret["block_finished"] == 1:
                    ret =  http_request("http://127.0.0.1:8080/generate_xml", "GET", {})
                    if not ret is None:
                        self.set_result(ret)
                    break
                
                time.sleep(3)

            if set_finished:
                break

class TizenMobile:
    """ Implementation for transfer data between Host and Tizen Mobile Device"""

    def __init__(self):
        self.__test_listen_port = "8080"
        self.__test_async_shell = None
        self.__test_set_block = 20
        self.__test_set_casecount = 0

    def __set_forward_tcp(self, hport=None, dport=None):
        """forward request a host port to a device-side port"""
        if hport is None: 
            return None
        if dport is None: 
            return None
        cmd = "sdb forward %s:tcp %s:tcp" % (hport, dport)
        result = shell_command(cmd)
        return result

    def __get_url(self, api):
        url = "http://127.0.0.1:%s%s" % (self.__test_listen_port, api)
        return url

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
        if len(ret) > 1:
            device_model_str = ret[0]
        # get hostname
        ret = shell_command("sdb -s %s shell uname -m" % deviceid)
        if len(ret) > 1:
            device_name_str = ret[0]
        # get os version
        ret = shell_command("sdb -s %s shell cat /etc/issue" % deviceid)
        for line in ret:
            if len(line) > 1:os_version_str = "%s %s" % (os_version_str, line)
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
        cmd = "sdb -s %s shell rpm -qa | grep cts" % (deviceid)
        ret =  shell_command(cmd)
        return ret

    def remove_package(self, deviceid, pkgid):
        """remove a installed package from device"""
        cmd = "sdb -s %s shell rpm -e %s" % (deviceid, pkgid)
        ret =  shell_command(cmd)
        return ret

    def init_test(self, deviceid, params):
        """init the test runtime, mainly process the star up of test stub"""

        print "init_test entry"
        if params is None:
            return None

        if not "stub-name" in params:
            print "\"stub-name\" is required for launch!"
            return None

        if not "testsuite-name" in params:
            print "\"testsuite-name\" is required for launch!"
            return None

        if not "client-command" in params:
            print "\"client-command\" is required for launch!"
            return None

        stub_entry = "%s --testsuite:%s --client-command:%s" % \
                    (params["stub-name"], params["testsuite-name"], params["client-command"])
        cmd = "sdb -s %s shell %s" % (deviceid, stub_entry)
        print "stub startup", cmd
        self.__test_async_shell = SdbCommThread(cmd, "bye")
        self.__test_async_shell.start()
        time.sleep(2)
        ret = self.__set_forward_tcp(self.__test_listen_port, "8000")
        print "__set_forward_tcp"

        timecnt = 0
        result = ""
        print "startup server..."
        while timecnt < 5:
            ret = http_request(self.__get_url("/check_server"), "GET", {})
            print "startup result", ret
            if ret is None:
                time.sleep(1)
                timecnt += 1
            else:
                result = "11223344"
                break
        return result

    def run_test(self, sessionid, test_set):
        """process the execution of a test set"""

        print "run_test entry"

        if sessionid is None: 
            return False
        if not "casecount" in test_set : 
            return False
        data = test_set
        casecount = int(data["casecount"])
        cases = data["cases"]

        self.__test_set_casecount = casecount
        if casecount % self.__test_set_block == 0:
            blknum = casecount / self.__test_set_block
        else:
            blknum = casecount / self.__test_set_block + 1

        idx = 1
        test_set_blocks = []
        while idx <= blknum:
            block_data = {}
            block_data["totalBlk"] = str(blknum)
            block_data["currentBlk"] = str(idx)
            block_data["casecount"] = data["casecount"]
            block_data["exetype"] = data["exetype"] 
            block_data["type"] = data["type"]
            start = (idx - 1) * self.__test_set_block
            if idx == blknum: 
                end = casecount
            else: 
                end = idx * self.__test_set_block
            block_data["cases"] = cases[start:end]
            test_set_blocks.append(block_data)
            idx += 1

        self.__test_async_http = HttpCommThread(test_set_blocks)
        self.__test_async_http.start()

        return True

    def get_test_status(self, sessionid):
        """poll the test task status"""
        if sessionid is None: 
            return None
        data = {"sessionid": sessionid}
        result = {"finished": "0"}
        global test_server_status
        lockobj.acquire()     
        result["finished"] = str(test_server_status["finished"])
        if "block_finished" in test_server_status:
            result["block_finished"] = str(test_server_status["block_finished"])          
        lockobj.release()

        global stdout_buffer
        lockcmd.acquire()
        output = []
        output.extend(stdout_buffer)
        stdout_buffer = []
        lockcmd.release()
        print "[server_test_status]:", result
        print "[server_test_msg]:", output
        if not output is None:
            result["msg"] = output
        else:
            result["msg"] = []
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
            print "[server_test_result]:" % result
        except Exception, e:
            print e

        return result

    def finalize_test(self, sessionid):
        """clear the test stub and related resources"""
        if sessionid is None: return False
        self.__test_async_shell.kill()
        data = {"sessionid": sessionid}
        ret = http_request(self.__get_url("/shut_down_server"), "GET", {})
        if not ret is None:
            return True
        else:
            return False

testremote = TizenMobile()
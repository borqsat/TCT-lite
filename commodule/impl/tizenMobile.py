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
import threading
import subprocess
import requests
import json

class sdbCommAsync(threading.Thread):
    def __init__(self, cmd=None, trigger=None):
        self.stdout = []
        self.stderr = []
        self.trigger = trigger
        self.cmd = cmd
        threading.Thread.__init__(self)

    def communicate(self):
        stdout = self.stdout
        stderr = self.stderr
        self.stdout = []
        self.stderr = []
        return stdout, stderr

    def run(self):
        proc = subprocess.Popen(self.cmd,
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        while True:
            outLine = proc.stdout.readline().rstrip()
            if outLine:
                self.stdout.append(outLine)

            errLine = proc.stderr.readline().rstrip()
            if errLine:
                self.stderr.append(errLine)

            if not proc.poll is None:
                break

class sdbCommSync:
    def __init__(self, cmd=None):
        self.stdout = []
        self.stderr = []
        self.cmd = cmd

    def communicate(self):
        result = ""
        print '%s' % self.cmd
        proc = subprocess.Popen(self.cmd,
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        while True:
            outLine = proc.stdout.readline().rstrip()
            if outLine:
                self.stdout.append(outLine)

            errLine = proc.stderr.readline().rstrip()
            if not proc.poll is None:
                break
        return self.stdout

class tizenMobile:
    """ Implementation for transfer data between Host and Tizen Mobile Device"""

    def __init__(self):
        print 'init tizenMobile instance'
        self.__hport = "8888"
        self.__async_shell = None

    def __shell_command(self, cmd=None):
        result = []
        if not cmd is None:
            proc = sdbCommSync(cmd)
            result = proc.communicate()
        return result

    def __set_forward_tcp(self, hport=None, dport=None):
        if hport is None: return None
        if dport is None: return None
        cmd = "sdb forward %s:tcp %s:tcp" % (hport, dport)
        return self.__shell_command(cmd)

    def __http_request(self, api, xtype="POST", data=None):
        result = None
        url = "http://127.0.0.1:%s%s" % (self.__hport, api)
        if xtype == "POST":
            headers = {'content-type': 'application/json'}
            ret = requests.post(url, data=json.dumps(data), headers=headers)
            result = ret.json()
        elif xtype == "GET":
            ret = requests.get(url, params=data)
            result = ret.json()
        return result

    def get_device_ids(self):
        cmd = "sdb devices"
        ret = self.__shell_command(cmd)
        return ret

    def get_device_info(self, deviceid=None):
        cmd = "sdb -s %s shell rpm -qa | grep cts" % deviceid
        ret =  self.__shell_command(cmd)
        return ret

    def install_package(self, deviceid, pkgpath):
        filename = os.path.split(pkgpath)[1]
        devpath = "/tmp/%s" % filename
        cmd = "sdb -s %s push %s %s" % (deviceid, pkgpath, devpath)
        ret =  self.__shell_command(cmd)
        cmd = "sdb shell rpm -ivh %s" % devpath
        ret =  self.__shell_command(cmd)
        return ret

    def remove_package(self, deviceid, pkgid):
        cmd = "sdb -s %s shell rpm -e %s" % (deviceid, pkgid)
        ret =  self.__shell_command(cmd)
        return ret

    def init_test(self, deviceid, params):
        if not "stub-entry" in params: 
            stub_entry = "testkit-stub"
        else:
            stub_entry = params["stub_entry"]
        if not "stub_server_port" in params:
            stub_server_port = "8000"
        else:
            stub_server_port = params["stub_server_port"]
        cmd = "sdb -s %s shell %s" % (deviceid, stub_entry)
        self.__async_shell = sdbCommAsync(cmd, None)
        ret = self.__set_forward_tcp(self.__hport, stub_server_port)
        return 0

    def run_test(self, sessionid, test_set):
        data = test_set
        ret = self.__http_request("/check_server_status", "POST", data)
        return ret

    def get_test_status(self, sessionid):
        if sessionid is None: return []
        data = {"sessionid": sessionid}
        ret = self.__http_request("/check_server_status", "GET", data)
        return ret

    def get_test_result(self, sessionid):
        if sessionid is None: return []
        data = {"sessionid": sessionid}
        ret = self.__http_request("/get_test_result", "GET", data)
        return ret

    def finalize_test(self, sessionid):
        data = {"sessionid": sessionid}
        ret = self.__http_request("/shut_down", "GET", data)
        return ret
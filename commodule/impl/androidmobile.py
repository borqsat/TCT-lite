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

""" The implementation of Android communication driver"""

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

LOCAL_HOST_NS = "127.0.0.1"
APP_QUERY_STR = "adb -s %s shell ps | grep %s | awk '{print $2}' "
APK_INSTALL = "adb -s %s shell pm install %s"
APK_UNINSTALL = "adb -s %s shell pm uninstall %s"
APK_LIST = "adb -s %s shell pm list packages |grep '%s'|cut -d ':' -f2"
DLOG_CLEAR = "adb -s %s shell logcat -c"
DLOG_WRT = "adb -s %s shell logcat -c"


def debug_trace(cmdline, logfile):
    global debug_flag, metux
    wbuffile = file(logfile, "w")
    import subprocess
    exit_code = None
    proc = subprocess.Popen(args=cmdline,
                            shell=True,
                            stdout=wbuffile,
                            stderr=None)
    while True:
        exit_code = proc.poll()
        if exit_code is not None:
            break
        time.sleep(0.5)
        metux.acquire()
        proc_flag = debug_flag
        metux.release()
        if not proc_flag:
            break
    wbuffile.close()
    if exit_code is None:
        killall(proc.pid)


def _get_device_ids():
    """get android deivce list of ids"""
    result = []
    exit_code, ret = shell_command("adb devices")
    for line in ret:
        if str.find(line, "\tdevice") != -1:
            result.append(line.split("\t")[0])
    return result


class AndroidMobile:

    """ Implementation for transfer data
        between Host and Android Mobile Device
    """
    get_device_ids = _get_device_ids

    def __init__(self, device_id=None):
        self.deviceid = device_id

    def shell_cmd(self, cmd="", timeout=15):
        cmdline = "sdb -s %s shell %s" % (self.deviceid, cmd)
        return shell_command(cmdline, timeout)

    def check_process(self, process_name):
        exit_code, ret = shell_command(APP_QUERY_STR % (self.deviceid, process_name))
        return len(ret)

    def shell_cmd_ext(self,
                      cmd="",
                      timeout=None,
                      boutput=False,
                      stdout_file=None,
                      stderr_file=None):
        cmdline = "sdb -s %s shell '%s; echo returncode=$?'" % (self.deviceid, cmd)
        return shell_command_ext(cmdline, timeout, boutput, stdout_file, stderr_file)

    def get_device_info(self):
        """get android deivce inforamtion"""
        device_info = {}
        device_info["device_id"] = self.deviceid
        device_info["resolution"] = "N/A"
        device_info["screen_size"] = "N/A"
        device_info["device_model"] = "N/A"
        device_info["device_name"] = "N/A"
        device_info["os_version"] = "N/A"
        device_info["build_id"] = "N/A"
        return device_info

    def download_file(self, remote_path, local_path):
        """download file from device"""
        cmd = "adb -s %s pull %s %s" % (self.deviceid, remote_path, local_path)
        exit_code, ret = shell_command(cmd)
        if exit_code != 0:
            error = ret[0].strip('\r\n') if len(ret) else "sdb shell timeout"
            LOGGER.info("[ Download file \"%s\" from target failed, error: %s ]"
                        % (remote_path, error))
            return False
        else:
            return True

    def upload_file(self, remote_path, local_path):
        """upload file to device"""
        cmd = "adb -s %s push %s %s" % (self.deviceid, local_path, remote_path)
        exit_code, ret = shell_command(cmd)
        if exit_code != 0:
            error = ret[0].strip('\r\n') if len(ret) else "sdb shell timeout"
            LOGGER.info("[ Upload file \"%s\" failed,"
                        " get error: %s ]" % (local_path, error))
            return False
        else:
            return True

    def get_launcher_opt(self, test_launcher, test_suite, test_set, auto_iu, fuzzy_match):
        """get test option dict """
        test_opt = {}
        test_opt["suite_name"] = test_suite
        test_opt["launcher"] = test_launcher
        test_opt["suite_id"] = test_suite
        if test_launcher.startswith('xwalk'):
            test_opt["suite_id"] = 'org.xwalk.app.template'
        return test_opt

    def get_server_url(self, remote_port="8000"):
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
        cmd = "adb -s %s forward tcp:%s tcp:%s" % \
            (self.deviceid, host_port, remote_port)
        exit_code, ret = shell_command(cmd)
        url_forward = "http://%s:%s" % (host, host_port)
        return url_forward

    def install_package(self, pkgpath):
        """install a package on android device:
        push package and install with shell command
        """
        cmd = APK_INSTALL % (self.deviceid, pkgpath)
        exit_code, ret = shell_command(cmd)
        return ret

    def uninstall_package(self, pkgname):
        """install a package on android device:
        push package and install with shell command
        """
        cmd = APK_UNINSTALL % (self.deviceid, pkgname)
        exit_code, ret = shell_command(cmd)
        return ret

    def get_installed_package(self):
        """get list of installed package from device"""
        cmd = APK_LIST % self.deviceid
        exit_code, ret = shell_command(cmd)
        return ret

    def start_debug(self, dlogfile):
        global debug_flag, metux
        debug_flag = True
        metux = threading.Lock()
        cmdline = DLOG_CLEAR % self.deviceid
        exit_code, ret = shell_command(cmdline)
        cmdline = DLOG_WRT % self.deviceid
        threading.Thread(target=debug_trace, args=(cmdline, dlogfile)).start()

    def stop_debug(self):
        global debug_flag, metux
        metux.acquire()
        debug_flag = False
        metux.release()


def get_target_conn(device_id=None):
    """ Get connection for Test Target"""
    if device_id is None:
        dev_list = _get_device_ids()
        device_id = dev_list[0] if len(dev_list) else None
    return AndroidMobile(device_id)

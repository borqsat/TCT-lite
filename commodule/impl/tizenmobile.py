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
from commodule.autoexec import shell_command, shell_command_ext


LOCAL_HOST_NS = "127.0.0.1"
APP_QUERY_STR = "sdb -s %s shell ps aux | grep '%s' | awk '{print $2}'"
APP_KILL_STR = "sdb -s %s shell kill -9 %s"
WRT_INSTALL_STR = "sdb -s %s shell wrt-installer -i /opt/%s/%s.wgt"
WRT_QUERY_STR = "sdb -s %s shell wrt-launcher -l | grep '%s'|awk '{print $2\":\"$NF}'"
WRT_START_STR = "sdb -s %s shell wrt-launcher -s %s"
WRT_KILL_STR = "sdb -s %s shell wrt-launcher -k %s"
WRT_UNINSTL_STR = "sdb -s %s shell wrt-installer -un %s"


def _get_device_ids():
    """get tizen deivce list of ids"""
    result = []
    exit_code, ret = shell_command("sdb devices")
    for line in ret:
        if str.find(line, "\tdevice") != -1:
            result.append(line.split("\t")[0])
    return result


class TizenMobile:
    """
    Implementation for transfer data
    between Host and Tizen Mobile Device
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
        return shell_command_ext(cmd, timeout, boutput, stdout_file, stderr_file)

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
        exit_code, ret = shell_command("sdb -s %s shell xrandr" % self.deviceid)
        pattern = re.compile("connected (\d+)x(\d+).* (\d+mm) x (\d+mm)")
        for line in ret:
            match = pattern.search(line)
            if match:
                resolution_str = "%s x %s" % (match.group(1), match.group(2))
                screen_size_str = "%s x %s" % (match.group(3), match.group(4))

        # get architecture
        exit_code, ret = shell_command("sdb -s %s shell uname -m" % self.deviceid)
        if len(ret) > 0:
            device_model_str = ret[0]

        # get hostname
        exit_code, ret = shell_command("sdb -s %s shell uname -n" % self.deviceid)
        if len(ret) > 0:
            device_name_str = ret[0]

        # get os version
        exit_code, ret = shell_command(
            "sdb -s %s shell cat /etc/issue" % self.deviceid)
        for line in ret:
            if len(line) > 1:
                os_version_str = "%s %s" % (os_version_str, line)

        # get build id
        exit_code, ret = shell_command(
            "sdb -s %s shell cat /etc/os-release" % self.deviceid)
        for line in ret:
            if line.find("BUILD_ID=") != -1:
                build_id_str = line.split('=')[1].strip('\"\r\n')

        os_version_str = os_version_str[0:-1]
        device_info["device_id"] = self.deviceid
        device_info["resolution"] = resolution_str
        device_info["screen_size"] = screen_size_str
        device_info["device_model"] = device_model_str
        device_info["device_name"] = device_name_str
        device_info["os_version"] = os_version_str
        device_info["build_id"] = build_id_str
        return device_info

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
        cmd = "sdb -s %s forward tcp:%s tcp:%s" % \
            (self.deviceid, host_port, remote_port)
        exit_code, ret = shell_command(cmd)
        url_forward = "http://%s:%s" % (host, host_port)
        return url_forward


    def download_file(self, remote_path, local_path):
        """download file from device"""
        cmd = "sdb -s %s pull %s %s" % (self.deviceid, remote_path, local_path)
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
        cmd = "sdb -s %s push %s %s" % (self.deviceid, local_path, remote_path)
        exit_code, ret = shell_command(cmd)
        if exit_code != 0:
            error = ret[0].strip('\r\n') if len(ret) else "sdb shell timeout"
            LOGGER.info("[ Upload file \"%s\" failed,"
                        " get error: %s ]" % (local_path, error))
            return False
        else:
            return True

    def get_launcher_opt(self, test_launcher, test_suite, test_set, fuzzy_match, auto_iu):
        """
        get test option dict
        """
        test_opt = {}
        cmd = ""
        test_opt["suite_name"] = test_suite
        test_opt["launcher"] = test_launcher
        suite_id = None
        if test_launcher.find('WRTLauncher') != -1:
            test_opt["launcher"] = "wrt-launcher"
            # test suite need to be installed by commodule
            if auto_iu:
                test_wgt = test_set
                cmd = WRT_INSTALL_STR % (self.deviceid, test_suite, test_wgt)
                exit_code, ret = shell_command(cmd)
                if exit_code == -1:
                    LOGGER.info("[ failed to install widget \"%s\" in target ]"
                                % test_wgt)
                    cmd = APP_QUERY_STR % (self.deviceid, "wrt-installer -i")
                    exit_code, ret = shell_command(cmd)
                    for line in ret:
                        cmd = APP_KILL_STR % (self.deviceid, line.strip('\r\n'))
                        exit_code, ret = shell_command(cmd)
                    return None
            else:
                test_wgt = test_suite

            # query the whether test widget is installed ok
            cmd = WRT_QUERY_STR % (self.deviceid, test_wgt)
            exit_code, ret = shell_command(cmd)
            if exit_code == -1:
                return None
            for line in ret:
                items = line.split(':')
                if len(items) < 1:
                    continue
                if (fuzzy_match and items[0].find(test_wgt) != -1) or items[0] == test_wgt:
                    suite_id = items[1].strip('\r\n')
                    break

            if suite_id is None:
                LOGGER.info("[ test widget \"%s\" not found in target ]"
                            % test_wgt)
                return None
            else:
                test_opt["suite_id"] = suite_id
        return test_opt

    def install_package(self, pkgpath):
        """install a package on tizen device:
        push package and install with shell command
        """
        cmd = "sdb -s %s shell rpm -ivh %s" % (self.deviceid, pkgpath)
        exit_code, ret = shell_command(cmd)
        return ret

    def get_installed_package(self):
        """get list of installed package from device"""
        cmd = "sdb -s %s shell rpm -qa | grep tct" % (self.deviceid)
        exit_code, ret = shell_command(cmd)
        return ret

    def download_debug(self, dlogfile):
        cmdline = 'dlog -c'
        exit_code, ret = shell_cmd(cmdline)
        cmdline = 'dlog WRT:D -v time'
        self.tsop['dlog_file'] = dlogfile
        self.tsop['dlog_shell'] = DlogThread(cmdline, dlogfile)
        self.tsop['dlog_shell'].start()

    def uninstall_widget(self, wgt_name):
        cmd = WRT_UNINSTL_STR % (self.deviceid, wgt_name)
        exit_code, ret = shell_command(cmd)
        return True


def get_target_conn(device_id=None):
    """ Get connection for Test Target"""
    if device_id is None:
        dev_list = _get_device_ids()
        device_id = dev_list[0] if len(dev_list) else None
    return TizenMobile(device_id)

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

LOCAL_HOST_NS = "127.0.0.1"
CNT_RETRY = 10
LOCK_OBJ = threading.Lock()
TEST_SERVER_RESULT = {}
TEST_SERVER_STATUS = {}
TEST_FLAG = 0
DATE_FORMAT_STR = "%Y-%m-%d %H:%M:%S"
APP_QUERY_STR = "adb -s %s shell ps | grep %s | awk '{print $2}' "
WRT_INSTALL_STR = "adb -s %s shell pm install /opt/%s/%s.apk"
WRT_QUERY_STR = "adb -s %s shell pm list packages |grep '%s'|cut -d ':' -f2"
WRT_UNINSTL_STR = "adb -s %s shell pm uninstall %s"


class AndroidMobile:

    """ Implementation for transfer data
        between Host and Android Mobile Device
    """

    def __init__(self, device_id=None):
        self.deviceid = device_id

    def get_device_ids(self):
        """get android deivce list of ids"""
        result = []
        exit_code, ret = shell_command("adb devices")
        for line in ret:
            if str.find(line, "\tdevice") != -1:
                result.append(line.split("\t")[0])
        return result

    def get_device_info(self):
        """get android deivce inforamtion"""
        device_info = {}
        resolution_str = ""
        screen_size_str = ""
        device_model_str = ""
        device_name_str = ""
        build_id_str = ""
        os_version_str = ""

        # get resolution and screen size
        exit_code, ret = shell_command("adb -s %s shell xrandr" % self.deviceid)
        pattern = re.compile("connected (\d+)x(\d+).* (\d+mm) x (\d+mm)")
        for line in ret:
            match = pattern.search(line)
            if match:
                resolution_str = "%s x %s" % (match.group(1), match.group(2))
                screen_size_str = "%s x %s" % (match.group(3), match.group(4))

        # get architecture
        exit_code, ret = shell_command("adb -s %s shell uname -m" % self.deviceid)
        if len(ret) > 0:
            device_model_str = ret[0]

        # get hostname
        exit_code, ret = shell_command("adb -s %s shell uname -n" % self.deviceid)
        if len(ret) > 0:
            device_name_str = ret[0]

        # get os version
        exit_code, ret = shell_command(
            "adb -s %s shell cat /etc/issue" % self.deviceid)
        for line in ret:
            if len(line) > 1:
                os_version_str = "%s %s" % (os_version_str, line)

        # get build id
        exit_code, ret = shell_command(
            "adb -s %s shell cat /etc/os-release" % self.deviceid)
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

    def install_package(self, pkgpath):
        """install a package on android device:
        push package and install with shell command
        """
        filename = os.path.split(pkgpath)[1]
        devpath = "/tmp/%s" % filename
        cmd = "adb -s %s push %s %s" % (self.deviceid, pkgpath, devpath)
        exit_code, ret = shell_command(cmd)
        cmd = "adb shell rpm -ivh %s" % devpath
        exit_code, ret = shell_command(cmd)
        return ret

    def get_installed_package(self):
        """get list of installed package from device"""
        cmd = "adb -s %s shell pm list packages| grep tct" % (self.deviceid)
        exit_code, ret = shell_command(cmd)
        return ret

    def download_file(self, remote_path, local_path):
        """download file from device"""
        return _download_file(self.deviceid, remote_path, local_path)

    def upload_file(self, remote_path, local_path):
        """upload file to device"""
        return _upload_file(self.deviceid, remote_path, local_path)

    def __get_test_options(self, test_launcher, test_suite,
                           test_set):
        """get test option dict """
        test_opt = {}
        test_opt["suite_name"] = test_suite
        test_opt["launcher"] = test_launcher
        if test_launcher.startswith('xwalk'):
            test_opt["suite_id"] = 'org.xwalk.app.template'

        return test_opt

    def get_server_url(remote_port="8000"):
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

def get_target_conn():
    """ Get connection for Test Target"""
    return AndroidMobile(self.deviceid)

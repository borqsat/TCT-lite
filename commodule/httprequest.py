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
""" The http request process module"""

import requests
import json


def get_url(baseurl, api):
    """get full url string"""
    return "%s%s" % (baseurl, api)


def http_request(url, rtype="POST", data=None, time_out=10):
    """
    http request to the device http server
    """
    result = None
    if rtype == "POST":
        headers = {'content-type': 'application/json'}
        try:
            ret = requests.post(url, data=json.dumps(
                data), headers=headers, timeout=time_out)

            if ret:
                result = ret.json()
        except Exception as error:
            pass
    elif rtype == "GET":
        try:
            ret = requests.get(url, params=data, timeout=time_out)
            if ret:
                result = ret.json()
        except Exception as error:
            pass
    return result

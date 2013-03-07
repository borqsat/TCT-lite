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
# Foundation, Inc.,
# 51 Franklin Street,
# Fifth Floor,
# Boston, MA  02110-1301, USA.
#
# Authors:
#              Zhang, Huihui <huihuix.zhang@intel.com>
#              Wendong,Sui  <weidongx.sun@intel.com>
#              Yuanyuan,Zou  <yuanyuan.zou@borqs.com>
""" prepare run , split xml ,run case , merge result """

import os
import platform
import time
import sys
import traceback
import collections
from datetime import datetime
from shutil import copyfile
import xml.etree.ElementTree as etree
import ConfigParser
from tempfile import mktemp
from shutil import move
from os import remove


JOIN = os.path.join
DIRNAME = os.path.dirname
BASENAME = os.path.basename
EXISTS = os.path.exists
ABSPATH = os.path.abspath


class TRunner:
    """
    Parse the testdefinition.xml files.
    Apply filter for each run.
    Conduct tests execution.
    """
    def __init__(self, connector):
        """ init all self parameters here """
        # dryrun
        self.bdryrun = False
        # non_active
        self.non_active = False
        # enable_memory_collection
        self.enable_memory_collection = False
        # result file
        self.resultfile = None
        # external test
        self.external_test = None
        # filter rules
        self.filter_rules = None
        self.fullscreen = False
        self.resultfiles = set()
        self.core_auto_files = []
        self.core_manual_files = []
        self.skip_all_manual = False
        self.testsuite_dict = {}
        self.exe_sequence = []
        self.testresult_dict = {"pass": 0, "fail": 0,
                                "block": 0, "not_run": 0}
        self.current_test_xml = "none"
        self.first_run = True
        self.deviceid = None
        self.session_id = None
        self.pid_log = None
        self.set_parameters = {}
        self.connector = connector

    def set_global_parameters(self, options):
        "get all options "
        # apply dryrun
        if options.bdryrun:
            self.bdryrun = options.bdryrun
        # release memory when the free memory is less than 100M
        if options.enable_memory_collection:
            self.enable_memory_collection = options.enable_memory_collection
        # Disable set the result of core manual cases from the console
        if options.non_active:
            self.non_active = options.non_active
        # apply user specify test result file
        if options.resultfile:
            self.resultfile = options.resultfile
        # set device_id
        if options.device_serial:
            self.deviceid = options.device_serial
        if options.fullscreen:
            self.fullscreen = True
        # set the external test WRTLauncher
        if options.exttest:
            self.external_test = options.exttest

    def set_pid_log(self, pid_log):
        """ get pid_log file """
        self.pid_log = pid_log

    def add_filter_rules(self, **kargs):
        """
        kargs:  key:values - "":["",]
        """
        self.filter_rules = kargs

    def set_session_id(self, session_id):
        """ set the set test session id which is get form com_module """
        self.session_id = session_id

    def prepare_run(self, testxmlfile, resultdir=None):
        """
        testxmlfile: target testxml file
        execdir and resultdir: should be the absolute path since TRunner
        is the common lib
        """
        # resultdir is set to current directory by default
        if not resultdir:
            resultdir = os.getcwd()
        ok_prepare = True
        if ok_prepare:
            try:
                filename = testxmlfile
                filename = os.path.splitext(filename)[0]
                if platform.system() == "Linux":
                    filename = filename.split('/')[-2]
                else:
                    filename = filename.split('\\')[-2]
                if self.filter_rules["execution_type"] == ["manual"]:
                    resultfile = "%s.manual.xml" % filename
                else:
                    resultfile = "%s.auto.xml" % filename
                resultfile = JOIN(resultdir, resultfile)
                if not EXISTS(resultdir):
                    os.mkdir(resultdir)
                print "[ analysis test xml file: %s ]" % resultfile
                self.__prepare_result_file(testxmlfile, resultfile)
                self.__split_test_xml(resultfile, resultdir)
            except IOError, error:
                traceback.print_exc()
                print error
                ok_prepare &= False
        return ok_prepare

    def __split_test_xml(self, resultfile, resultdir):
        """ split_test_xml into auto and manual"""
        casefind = etree.parse(resultfile).getiterator('testcase')
        if casefind:
            test_file_name = "%s" % BASENAME(resultfile)
            test_file_name = os.path.splitext(test_file_name)[0]
            if self.external_test:
                self.__splite_external_test(
                    resultfile, test_file_name, resultdir)
            else:
                self.__splite_core_test(resultfile)

    def __splite_core_test(self, resultfile):
        """select core test"""
        if self.filter_rules["execution_type"] == ["auto"]:
            self.core_auto_files.append(resultfile)
        else:
            self.core_manual_files.append(resultfile)
        self.resultfiles.add(resultfile)

    def __splite_external_test(self, resultfile, test_file_name, resultdir):
        """select external_test"""
        testsuite_dict_value_list = []
        testsuite_dict_add_flag = 0
        filename_diff = 1

        parser = etree.parse(resultfile)
        for tsuite in parser.getiterator('suite'):
            root = etree.Element('test_definition')
            suitefilename = os.path.splitext(resultfile)[0]
            suitefilename += ".suite_%s.xml" % filename_diff
            suitefilename = JOIN(resultdir, suitefilename)
            tsuite.tail = "\n"
            root.append(tsuite)
            try:
                with open(suitefilename, 'w') as output:
                    tree = etree.ElementTree(element=root)
                    tree.write(output)
            except IOError, error:
                print "[ Error: create filtered result file: %s failed,\
                 error: %s ]" % (suitefilename, error)
            case_suite_find = etree.parse(
                suitefilename).getiterator('testcase')
            if case_suite_find:
                if tsuite.get('launcher'):
                    if tsuite.get('launcher').find('WRTLauncher'):
                        self.__splite_core_test(suitefilename)
                    else:
                        testsuite_dict_value_list.append(suitefilename)
                        if testsuite_dict_add_flag == 0:
                            self.exe_sequence.append(test_file_name)
                        testsuite_dict_add_flag = 1
                        self.resultfiles.add(suitefilename)
                else:
                    if self.filter_rules["execution_type"] == ["auto"]:
                        self.core_auto_files.append(suitefilename)
                    else:
                        self.core_manual_files.append(suitefilename)
                    self.resultfiles.add(suitefilename)
            filename_diff += 1
        if testsuite_dict_add_flag:
            self.testsuite_dict[test_file_name] = testsuite_dict_value_list

    def __prepare_result_file(self, testxmlfile, resultfile):
        """ write the test_xml content to resultfile"""
        try:
            parse_tree = etree.parse(testxmlfile)
            suiteparent = parse_tree.getroot()
            no_test_definition = 1
            if parse_tree.getiterator('test_definition'):
                no_test_definition = 0
            if no_test_definition:
                suiteparent = etree.Element('test_definition')
                suiteparent.tail = "\n"
                for suite in parse_tree.getiterator('suite'):
                    suite.tail = "\n"
                    suiteparent.append(suite)
            self.apply_filter(suiteparent)
            try:
                with open(resultfile, 'w') as output:
                    tree = etree.ElementTree(element=suiteparent)
                    tree.write(output)
            except IOError, error:
                print "[ Error: create filtered result file: %s failed,\
                    error: %s ]" % (resultfile, error)
        except IOError, error:
            print error
            return False

    def run_case(self, latest_dir):
        """ run case """
        # run core auto cases
        self.__run_core_auto()

        # run webAPI cases
        self.__run_webapi_test(latest_dir)

        # run core manual cases
        self.__run_core_manual()

    def __run_core_auto(self):
        """ core auto cases run"""
        self.core_auto_files.sort()
        for core_auto_file in self.core_auto_files:
            temp_test_xml = os.path.splitext(core_auto_file)[0]
            temp_test_xml = os.path.splitext(temp_test_xml)[0]
            temp_test_xml = os.path.splitext(temp_test_xml)[0]
            temp_test_xml += ".auto"
            # print identical xml file name
            if self.current_test_xml != temp_test_xml:
                time.sleep(3)
                print "\n[ testing xml: %s.xml ]" % temp_test_xml
                self.current_test_xml = temp_test_xml
            self.execute(core_auto_file, core_auto_file)

    def __run_core_manual(self):
        """ core manual cases run """
        self.core_manual_files.sort()
        for core_manual_file in self.core_manual_files:
            temp_test_xml = os.path.splitext(core_manual_file)[0]
            temp_test_xml = os.path.splitext(temp_test_xml)[0]
            temp_test_xml = os.path.splitext(temp_test_xml)[0]
            temp_test_xml += ".manual"
            # print identical xml file name
            if self.current_test_xml != temp_test_xml:
                time.sleep(3)
                print "\n[ testing xml: %s.xml ]" % temp_test_xml
                self.current_test_xml = temp_test_xml
            if self.non_active:
                self.skip_all_manual = True
            self.execute(core_manual_file, core_manual_file)

    def __run_webapi_test(self, latest_dir):
        """ run webAPI test"""

        list_auto = []
        list_manual = []
        for i in self.exe_sequence:
            if i[-4::1] == "auto":
                list_auto.append(i)
            if i[-6::1] == "manual":
                list_manual.append(i)
        list_auto.sort()
        list_manual.sort()
        self.exe_sequence = []
        self.exe_sequence.extend(list_auto)
        self.exe_sequence.extend(list_manual)

        for webapi_total_file in self.exe_sequence:
            for webapi_file in self.testsuite_dict[webapi_total_file]:
                # print identical xml file name
                if self.current_test_xml != JOIN(latest_dir, webapi_total_file):
                    time.sleep(3)
                    print "\n[ testing xml: %s.xml ]\n" \
                        % JOIN(latest_dir, webapi_total_file)
                    self.current_test_xml = JOIN(latest_dir, webapi_total_file)
                try:
                    # prepare test set list
                    test_xml_set_list = self.__split_xml_to_set(webapi_file)
                    # create temporary parameter
                    for test_xml_set in test_xml_set_list:
                        print "\n[ run set: %s ]" % test_xml_set
                        # init test here
                        self.__init_com_module(test_xml_set)
                        # prepare the test JSON
                        self.__prepare_external_test_json(test_xml_set)
                        # send set JSON Data to com_module
                        self.connector.run_test(
                            self.session_id, self.set_parameters)
                        while True:
                            time.sleep(1)
                            # check the test status ,if the set finished,get
                            # the set_result,and finalize_test
                            if self.__check_test_status():
                                set_result = self.connector.get_test_result(
                                    self.session_id)
                                # write_result to set_xml
                                self.__write_set_result(
                                    test_xml_set, set_result)
                                # shut down server
                                try:
                                    print '[ show down server ]'
                                    self.connector.finalize_test(
                                        self.session_id)
                                except Exception, error:
                                    print "[ Error: fail to close webapi http server, error: %s ]" % error

                                break
                except IOError, error:
                    print "[ Error: fail to run webapi test xml, error: %s ]" % error

    def __split_xml_to_set(self, webapi_file):
        """split xml by <set>"""

        print "[ split xml: %s by <set> ]" % webapi_file
        print "[ this might take some time, please wait ]"
        set_number = 1
        test_xml_set_list = []
        self.resultfiles.discard(webapi_file)
        test_xml_temp = etree.parse(webapi_file)
        for test_xml_temp_suite in test_xml_temp.getiterator('suite'):
            while set_number <= len(test_xml_temp_suite.getiterator('set')):
                copy_url = os.path.splitext(webapi_file)[0]
                copy_url += "_set_%s.xml" % set_number
                copyfile(webapi_file, copy_url)
                test_xml_set_list.append(copy_url)
                self.resultfiles.add(copy_url)
                set_number += 1
        time.sleep(3)
        set_number -= 1
        print "[ total set number is: %s ]" % set_number

        # only keep one set in each xml file and remove empty set
        test_xml_set_list_empty = []
        for test_xml_set in test_xml_set_list:
            test_xml_set_tmp = etree.parse(test_xml_set)
            set_keep_number = 1
            print "[ process set: %s ]" % test_xml_set
            for test_xml_set_temp_suite in test_xml_set_tmp.getiterator('suite'):
                for test_xml_set_temp_set in test_xml_set_temp_suite.getiterator('set'):
                    if set_keep_number != set_number:
                        test_xml_set_temp_suite.remove(test_xml_set_temp_set)
                    else:
                        if not test_xml_set_temp_set.getiterator('testcase'):
                            test_xml_set_list_empty.append(test_xml_set)
                    set_keep_number += 1
            set_number -= 1
            test_xml_set_tmp.write(test_xml_set)
            # with open(test_xml_set, 'w') as output:
            #     root = test_xml_set_tmp.getroot()
            #     tree = etree.ElementTree(element=root)
            #     tree.write(output)
        for empty_set in test_xml_set_list_empty:
            print "[ remove empty set: %s ]" % empty_set
            test_xml_set_list.remove(empty_set)
            self.resultfiles.discard(empty_set)

        return test_xml_set_list

    def merge_resultfile(self, start_time, latest_dir):
        """ merge_result_file """
        mergefile = mktemp(suffix='.xml', prefix='tests.', dir=latest_dir)
        mergefile = os.path.splitext(mergefile)[0]
        mergefile = os.path.splitext(mergefile)[0]
        mergefile = "%s.result" % BASENAME(mergefile)
        mergefile = "%s.xml" % mergefile
        mergefile = JOIN(latest_dir, mergefile)
        end_time = datetime.today().strftime("%Y-%m-%d_%H_%M_%S")
        print "\n[ test complete at time: %s ]" % end_time
        print "[ start merging test result xml files, this might take some time, please wait ]"
        print "[ merge result files into %s ]" % mergefile
        root = etree.Element('test_definition')
        root.tail = "\n"
        totals = set()
        # create core and webapi set
        resultfiles_core = set()
        for auto_file in self.core_auto_files:
            resultfiles_core.add(auto_file)
        for manual_file in self.core_manual_files:
            resultfiles_core.add(manual_file)
        resultfiles_webapi = self.resultfiles
        for resultfile_core in resultfiles_core:
            resultfiles_webapi.discard(resultfile_core)
        # merge core result files
        totals = self.__merge_result(resultfiles_core, totals)
        # merge webapi result files
        totals = self.__merge_result(resultfiles_webapi, totals)

        for total in totals:
            result_xml = etree.parse(total)
            for suite in result_xml.getiterator('suite'):
                suite.tail = "\n"
                root.append(suite)
        # print test summary
        self.__print_summary()
        # generate actual xml file
        print "[ generate result xml: %s ]" % mergefile
        if self.skip_all_manual:
            print "[ some results of core manual cases are N/A, \
            please refer to the above result file ]"
        print "[ merge complete, write to the result file, \
        this might take some time, please wait ]"
        # get useful info for xml
        # add environment node
        # add summary node
        root.insert(0, self.__get_summary(start_time, end_time))
        root.insert(0, self.__get_environment())
        # add XSL support to testkit-lite
        declaration_text = """<?xml version="1.0" encoding="UTF-8"?>
        <?xml-stylesheet type="text/xsl" href="testresult.xsl"?>\n"""
        try:
            with open(mergefile, 'w') as output:
                output.write(declaration_text)
                tree = etree.ElementTree(element=root)
                tree.write(output, xml_declaration=False, encoding='utf-8')
        except IOError, error:
            print "[ Error: merge result file failed, error: %s ]" % error
        # change &lt;![CDATA[]]&gt; to <![CDATA[]]>
        replace_cdata(mergefile)
        # copy result to -o option
        try:
            if self.resultfile:
                copyfile(mergefile, self.resultfile)
        except IOError, error:
            print "[ Error: fail to copy the result file to: %s, \
            please check if you have created its parent directory, \
            error: %s ]" % (self.resultfile, error)

    def __merge_result(self, setresultfiles, totals):
        """ merge set result to total"""
        resultfiles = setresultfiles
        for resultfile in resultfiles:
            totalfile = os.path.splitext(resultfile)[0]
            totalfile = os.path.splitext(totalfile)[0]
            totalfile = os.path.splitext(totalfile)[0]
            totalfile = "%s.total" % totalfile
            totalfile = "%s.xml" % totalfile
            total_xml = etree.parse(totalfile)

            print "|--[ merge webapi result file: %s ]" % resultfile
            result_xml = etree.parse(resultfile)
            for total_suite in total_xml.getiterator('suite'):
                for total_set in total_suite.getiterator('set'):
                    for result_suite in result_xml.getiterator('suite'):
                        for result_set in result_suite.getiterator('set'):
                            # when total xml and result xml have same suite
                            # name and set name
                            if result_set.get('name') == total_set.get('name') and result_suite.get('name') == total_suite.get('name'):
                                # set cases that doesn't have result in result set to N/A
                                # append cases from result set to total set
                                result_case_iterator = result_set.getiterator(
                                    'testcase')
                                if result_case_iterator:
                                    print "`----[ suite: %s, set: %s, time: %s ]" % (result_suite.get('name'), result_set.get('name'), datetime.today().strftime("%Y-%m-%d_%H_%M_%S"))
                                    for result_case in result_case_iterator:
                                        try:
                                            self.__count_result(result_case)
                                            total_set.append(result_case)
                                        except IOError, error:
                                            print "[ Error: fail to append %s, error: %s ]" % (result_case.get('id'), error)
            total_xml.write(totalfile)
            totals.add(totalfile)
        return totals

    def __count_result(self, result_case):
        """ record the pass,failed,block,N/A case number"""

        if not result_case.get('result'):
            result_case.set('result', 'N/A')
            # add empty result node structure for N/A case
            resinfo_elm = etree.Element('result_info')
            res_elm = etree.Element('actual_result')
            start_elm = etree.Element('start')
            end_elm = etree.Element('end')
            stdout_elm = etree.Element('stdout')
            stderr_elm = etree.Element('stderr')
            resinfo_elm.append(res_elm)
            resinfo_elm.append(start_elm)
            resinfo_elm.append(end_elm)
            resinfo_elm.append(stdout_elm)
            resinfo_elm.append(stderr_elm)
            result_case.append(resinfo_elm)
            res_elm.text = 'N/A'
        if result_case.get('result') == "PASS":
            self.testresult_dict["pass"] += 1
        if result_case.get('result') == "FAIL":
            self.testresult_dict["fail"] += 1
        if result_case.get('result') == "BLOCK":
            self.testresult_dict["block"] += 1
        if result_case.get('result') == "N/A":
            self.testresult_dict["not_run"] += 1

    def __get_environment(self):
        """ get environment """
        device_info = self.connector.get_device_info(self.deviceid)
        # add environment node
        environment = etree.Element('environment')
        environment.attrib['device_id'] = ""
        environment.attrib['device_model'] = device_info["device_model"]
        environment.attrib['device_name'] = device_info["device_name"]
        environment.attrib['firmware_version'] = ""
        environment.attrib['host'] = ""
        environment.attrib['os_version'] = device_info["os_version"]
        environment.attrib['resolution'] = device_info["resolution"]
        environment.attrib['screen_size'] = device_info["screen_size"]
        environment.attrib['cts_version'] = get_version_info()
        other = etree.Element('other')
        other.text = ""
        environment.append(other)
        environment.tail = "\n"

        return environment

    def __get_summary(self, start_time, end_time):
        """ set summary node """
        summary = etree.Element('summary')
        summary.attrib['test_plan_name'] = "Empty test_plan_name"
        start_at = etree.Element('start_at')
        start_at.text = start_time
        end_at = etree.Element('end_at')
        end_at.text = end_time
        summary.append(start_at)
        summary.append(end_at)
        summary.tail = "\n  "
        return summary

    def __print_summary(self):
        """ print test summary infomation"""
        print "[ test summary ]"
        total_case_number = int(self.testresult_dict["pass"]) \
            + int(self.testresult_dict["fail"]) \
            + int(self.testresult_dict["block"]) \
            + int(self.testresult_dict["not_run"])
        print "  [ total case number: %s ]" % (total_case_number)
        if total_case_number == 0:
            print "[Warning: found 0 case from the result files, \
            if it's not right, please check the test xml files, or the filter values ]"
        else:
            print "  [ pass rate: %.2f%% ]" \
                % (int(self.testresult_dict["pass"]) * 100 / int(total_case_number))
            print "  [ PASS case number: %s ]" % self.testresult_dict["pass"]
            print "  [ FAIL case number: %s ]" % self.testresult_dict["fail"]
            print "  [ BLOCK case number: %s ]" % self.testresult_dict["block"]
            print "  [ N/A case number: %s ]" % self.testresult_dict["not_run"]

    def __prepare_external_test_json(self, resultfile):
        """Run external test"""
        if self.bdryrun:
            print "[ WRTLauncher mode does not support dryrun ]"
            return True
        parameters = {}
        xml_set_tmp = resultfile
        # split set_xml by <case> get case parameters
        print "[ split xml: %s by <case> ]" % xml_set_tmp
        print "[ this might take some time, please wait ]"
        try:
            parse_tree = etree.parse(xml_set_tmp)
            root_em = parse_tree.getroot()
            case_tmp = []
            for tset in root_em.getiterator('set'):
                case_order = 1
                parameters.setdefault(
                    "casecount", str(len(tset.getiterator('testcase')))
                )
                for tcase in tset.getiterator('testcase'):
                    case_detail_tmp = {}
                    parameters.setdefault(
                        "exetype", tcase.get('execution_type')
                    )

                    parameters.setdefault("type", tcase.get('type'))
                    case_detail_tmp.setdefault("case_id", tcase.get('id'))
                    case_detail_tmp.setdefault("purpose", tcase.get('purpose'))
                    case_detail_tmp.setdefault("order", str(case_order))
                    case_detail_tmp.setdefault("test_script_entry", "none")
                    case_detail_tmp.setdefault("step_desc", "none")
                    case_detail_tmp.setdefault("expected", "none")
                    case_detail_tmp.setdefault("pre_condition", "none")
                    case_detail_tmp.setdefault("post_condition", "none")

                    if tcase.find('description/test_script_entry') is not None:
                        case_detail_tmp.setdefault(
                            "test_script_entry", tcase.find(
                                'description/test_script_entry').text
                        )
                    for this_step in tcase.getiterator("step"):
                        if this_step.find("step_desc") is not None:
                            case_detail_tmp.setdefault(
                                "step_desc",
                                this_step.find("step_desc").text
                            )

                        if this_step.find("expected") is not None:
                            case_detail_tmp.setdefault(
                                "expected",
                                this_step.find("expected").text
                            )

                    if tcase.find('description/pre_condition') is not None:
                        case_detail_tmp.setdefault(
                            "pre_condition",
                            tcase.find('description/pre_condition').text
                        )

                    if tcase.find('description/post_condition') is not None:
                        case_detail_tmp.setdefault(
                            "post_condition",
                            tcase.find('description/post_condition').text
                        )

                    case_tmp.append(case_detail_tmp)
                    case_order += 1
            parameters.setdefault("cases", case_tmp)
            self.set_parameters = parameters
        except IOError, error:
            print "[ Error: fail to prepare cases parameters, \
            error: %s ]\n" % error
            return False
        return True

    def apply_filter(self, root_em):
        """ apply filter """
        rules = self.filter_rules
        for tsuite in root_em.getiterator('suite'):
            if rules.get('suite'):
                if tsuite.get('name') not in rules['suite']:
                    root_em.remove(tsuite)
            for tset in tsuite.getiterator('set'):
                if rules.get('set'):
                    if tset.get('name') not in rules['set']:
                        tsuite.remove(tset)

        for tset in root_em.getiterator('set'):
            for tcase in tset.getiterator('testcase'):
                if not self.__apply_filter_case_check(tcase):
                    tset.remove(tcase)

    def __apply_filter_case_check(self, tcase):
        """filter cases"""
        rules = self.filter_rules
        for key in rules.iterkeys():
            if key in ["suite", "set"]:
                continue
            # Check attribute
            t_val = tcase.get(key)
            if t_val:
                if not t_val in rules[key]:
                    return False
            else:
                # Check sub-element
                items = tcase.getiterator(key)
                if items:
                    t_val = []
                    for i in items:
                        t_val.append(i.text)
                    if len(set(rules[key]) & set(t_val)) == 0:
                        return False
        return True

    def execute(self, testxmlfile, resultfile):
        """core test cases execute"""
        def exec_testcase(case, total_number, current_number):
            """ run core test cases """
            case_result = "BLOCK"
            return_code = None
            stderr = "none"
            stdout = "none"
            start_time = datetime.today().strftime("%Y-%m-%d_%H_%M_%S")
            # print case info
            test_script_entry = "none"
            expected_result = "0"
            actual_result = "none"
            testentry_elm = case.find('description/test_script_entry')
            if testentry_elm is not None:
                test_script_entry = testentry_elm.text
                expected_result = testentry_elm.get(
                    'test_script_expected_result', "0")
            print "\n[case] execute case:\nTestCase: %s\nTestEntry: %s\nExpected Result: %s\nTotal: %s, Current: %s" % (case.get("id"), test_script_entry, expected_result, total_number, current_number)
            # execute test script
            if testentry_elm is not None:
                if self.bdryrun:
                    return_code, stderr, stdout = "none", "Dryrun error info", "Dryrun output"
                else:
                    print "[ execute test script, this might take some time, please wait ]"
                    if testentry_elm.text is None:
                        print "[ Warnning: test script is empty, please check your test xml file ]"
                    else:
                        try:
                            # run auto core test here
                            # if testentry_elm.get("timeout")
                            #    case = testentry_elm.text
                            #    time_out = str2number(testentry_elm.get("timeout"))
                            #
                            if return_code is not None:
                                actual_result = str(return_code)
                            print "Script Return Code: %s" % actual_result
                        except Exception, error:
                            print "[ Error: fail to execute test script, \
                            error: %s ]\n" % error
            # Construct result info node
            resinfo_elm = etree.Element('result_info')
            res_elm = etree.Element('actual_result')
            start_elm = etree.Element('start')
            end_elm = etree.Element('end')
            stdout_elm = etree.Element('stdout')
            stderr_elm = etree.Element('stderr')
            resinfo_elm.append(res_elm)
            resinfo_elm.append(start_elm)
            resinfo_elm.append(end_elm)
            resinfo_elm.append(stdout_elm)
            resinfo_elm.append(stderr_elm)
            case.append(resinfo_elm)
            start_elm.text = start_time
            res_elm.text = actual_result
            stdout_elm.text = stdout
            stderr_elm.text = stderr

            # sdx@kooltux.org: add notes to xml result
            insert_notes(case, stdout)
            self.__insert_measures(case, stdout)

            # handle manual core cases
            if case.get('execution_type') == 'manual':
                case.set('result', 'BLOCK')
                try:
                    # print pre-condition info
                    precondition_elm = case.find('description/pre_condition')
                    if precondition_elm is not None:
                        print "\n****\nPre-condition: %s\n ****\n" % precondition_elm.text
                    # print step info
                    for this_step in case.getiterator("step"):
                        step_desc = "none"
                        expected = "none"
                        order = this_step.get("order")
                        stepdesc_elm = this_step.find("step_desc")
                        expected_elm = this_step.find("expected")
                        if stepdesc_elm is not None:
                            step_desc = stepdesc_elm.text
                        if expected_elm is not None:
                            expected = expected_elm.text
                        print "********************\nStep Order: %s" % order
                        print "Step Desc: %s" % step_desc
                        print "Expected: %s\n********************\n" % expected
                    if self.skip_all_manual:
                        case_result = "N/A"
                    else:
                        while True:
                            test_result = raw_input(
                                '[ please input case result ] (p^PASS, f^FAIL, b^BLOCK, n^Next, d^Done):')
                            if test_result == 'p':
                                case_result = "PASS"
                                break
                            elif test_result == 'f':
                                case_result = "FAIL"
                                break
                            elif test_result == 'b':
                                case_result = "BLOCK"
                                break
                            elif test_result == 'n':
                                case_result = "N/A"
                                break
                            elif test_result == 'd':
                                case_result = "N/A"
                                self.skip_all_manual = True
                                break
                            else:
                                print "[ Warnning: you input: '%s' is invalid, \
                                please try again ]" % test_result
                except Exception, error:
                    print "[ Error: fail to get core manual test step, \
                    error: %s ]\n" % error
            # handle auto core cases
            else:
                case_result = "BLOCK"
                end_elm.text = datetime.today().strftime("%Y-%m-%d_%H_%M_%S")
                # set test result
                if return_code is not None:
                    # sdx@kooltux.org:
                    # if retcode is 69 ("service unavailable" in sysexits.h),
                    # test environment is not correct
                    if actual_result == "69":
                        case_result = "N/A"
                    elif actual_result == "time_out":
                        case_result = "BLOCK"
                    else:
                        if expected_result == actual_result:
                            case_result = "PASS"
                        else:
                            case_result = "FAIL"
            case.set('result', case_result)
            print "Case Result: %s" % case_result
            # Check performance test
            measures = case.getiterator('measurement')
            for measure in measures:
                ind = measure.get('name')
                fname = measure.get('file')
                if fname and EXISTS(fname):
                    try:
                        config = ConfigParser.ConfigParser()
                        config.read(fname)
                        val = config.get(ind, 'value')
                        measure.set('value', val)
                    except Exception, error:
                        print "[ Error: fail to parse performance value, \
                        error: %s ]\n" % error
            # record end time
            end_elm.text = datetime.today().strftime("%Y-%m-%d_%H_%M_%S")
        # execute cases
        try:
            parse_tree = etree.parse(testxmlfile)
            root_em = parse_tree.getroot()
            total_number = 0
            current_number = 0
            for tsuite in root_em.getiterator('suite'):
                for tset in tsuite.getiterator('set'):
                    for tcase in tset.getiterator('testcase'):
                        total_number += 1
            for tsuite in root_em.getiterator('suite'):
                for tset in tsuite.getiterator('set'):
                    for tcase in tset.getiterator('testcase'):
                        current_number += 1
                        exec_testcase(tcase, total_number, current_number)
            parse_tree.write(resultfile)
            return True
        except IOError, error:
            print "[ Error: fail to run core test case, error: %s ]\n" % error
            traceback.print_exc()
            return False

    # sdx@kooltux.org: parse measures returned by test script
    # and insert in XML result
    # see xsd/test_definition.xsd: measurementType
    _MEASURE_ATTRIBUTES = ['name', 'value', 'unit',
                           'target', 'failure', 'power']

    def __insert_measures(self, case, buf, pattern="###[MEASURE]###"):
        """ get measures """
        measures = self.__extract_measures(buf, pattern)
        for measure in measures:
            m_elm = etree.Element('measurement')
            for key in measure:
                m_elm.attrib[key] = measure[key]
            case.append(m_elm)

    def __extract_measures(self, buf, pattern):
        """
        This function extracts lines from <buf> containing the defined <pattern>.
        For each line containing the pattern, it extracts the string to the end of line
        Then it splits the content in multiple fields using the defined separator <field_sep>
        and maps the fields to measurement attributes defined in xsd
        Finally, a list containing all measurement objects found in input buffer is returned
        """
        out = []
        for line in buf.split("\n"):
            pos = line.find(pattern)
            if pos < 0:
                continue

            measure = {}
            elts = collections.deque(line[pos + len(pattern):].split(':'))
            for k in self._MEASURE_ATTRIBUTES:
                if len(elts) == 0:
                    measure[k] = ''
                else:
                    measure[k] = elts.popleft()

            # don't accept unnamed measure
            if measure['name'] != '':
                out.append(measure)
        return out

    def __init_com_module(self, testxml):
        """
            send init test to com_module
            if webapi test,com_module will start httpserver
            else com_module send the test case to devices
        """
        starup_prms = self.__prepare_starup_parameters(testxml)
        try:
            # init stub and get the session_id
            session_id = self.connector.init_test(self.deviceid, starup_prms)
            self.set_session_id(session_id)
            return True
        except Exception, error:
            print "[ Error: Initialization Error, error: %s ]" % error
            return False

    def __prepare_starup_parameters(self, testxml):
        """ prepare_starup_parameters """

        starup_parameters = {}
        print "[ prepare_starup_parameters ]"
        try:
            parse_tree = etree.parse(testxml)
            tsuite = parse_tree.getroot().getiterator('suite')[0]
            starup_parameters['stub-entry'] = tsuite.get("launcher")
            starup_parameters['pkg-name'] = tsuite.get("name")
        except IOError, error:
            print "[ Error: prepare starup parameters, error: %s ]" % error
        return starup_parameters

    def __write_set_result(self, testxmlfile, result):
        '''
            get the result JSON form com_module,
            write them to orignal testxmlfile

        '''
        # write the set_result to set_xml
        set_result_json = result
        set_result_xml = testxmlfile
        # covert JOSN to python dict string
        set_result = set_result_json
        case_results = set_result["cases"]
        try:
            parse_tree = etree.parse(set_result_xml)
            root_em = parse_tree.getroot()
            for tset in root_em.getiterator('set'):
                for tcase in tset.getiterator('testcase'):
                    for case_result in case_results:
                        if tcase.get("id") == case_result['case_id']:
                            tcase.set('result', case_result['result'])
            parse_tree.write(set_result_xml)
            print "[ cases result saved to resultfile ]\n"
        except IOError, error:
            print "[ Error: fail to write cases result, error: %s ]\n" % error

    def __check_test_status(self):
        '''
            get_test_status from com_module
            check the status
            if end ,return ture; else return False
        '''
        # check test running or end
        # if the status id end return True ,else return False

        session_status = self.connector.get_test_status(self.session_id)
        # session_status["finished"] == "0" is running
        # session_status["finished"] == "1" is end
        if session_status["finished"] == "0":
            progress_msg_list = session_status["msg"]
            for line in progress_msg_list:
                print line,
            return False
        elif session_status["finished"] == "1":
            return True
        else:
            print "[ session status error ,pls finilize test ]\n"
            return False


def get_version_info():
    """
        get testkit tool version ,just read the version in VERSION file
        VERSION file must put in /opt/testkit/lite/
    """
    try:
        config = ConfigParser.ConfigParser()
        if platform.system() == "Linux":
            config.read('/opt/testkit/lite/VERSION')
        else:
            version_file = os.path.join(sys.path[0], 'VERSION')
            config.read(version_file)
        version = config.get('public_version', 'version')
        return version
    except KeyError, error:
        print "[ Error: fail to parse version info, error: %s ]\n" % error
        return ""


def replace_cdata(file_name):
    """ replace some character"""
    try:
        abs_path = mktemp()
        new_file = open(abs_path, 'w')
        old_file = open(file_name)
        for line in old_file:
            line_temp = line.replace('&lt;![CDATA', '<![CDATA')
            new_file.write(line_temp.replace(']]&gt;', ']]>'))
        new_file.close()
        old_file.close()
        remove(file_name)
        move(abs_path, file_name)
    except IOError, error:
        print "[ Error: fail to replace cdata in the result file, \
            error: %s ]\n" % error


def extract_notes(buf, pattern):
    """util func to split lines in buffer, search for pattern on each line
    then concatenate remaining content in output buffer"""
    out = ""
    for line in buf.split("\n"):
        pos = line.find(pattern)
        if pos >= 0:
            out += line[pos + len(pattern):] + "\n"
    return out

# sdx@kooltux.org: parse notes in buffer and insert them in XML result


def insert_notes(case, buf, pattern="###[NOTE]###"):
    """ insert notes"""
    desc = case.find('description')
    if desc is None:
        return

    notes_elm = desc.find('notes')
    if notes_elm is None:
        notes_elm = etree.Element('notes')
        desc.append(notes_elm)
    if notes_elm.text is None:
        notes_elm.text = extract_notes(buf, pattern)
    else:
        notes_elm.text += "\n" + extract_notes(buf, pattern)

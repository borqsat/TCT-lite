#include <string>
#include <json/json.h>

#include "testcase.h"

using namespace std;

TestCase::TestCase()
{
    result = "N/A";

    std_out = "";

    is_executed = false;
}

TestCase::~TestCase()
{
}

void TestCase::init(const Json::Value value)
{
        order = value["order"].asString();
        case_id = value["case_id"].asString();
        purpose = value["purpose"].asString();
        entry = value["test_script_entry"].asString();
        pre_con = value["pre_condition"].asString();
        post_con = value["post_condition"].asString();
        steps = value["step_desc"].asString();
        e_result = value["expected"].asString();
        onload_delay = value["onload_delay"].asString();
}

void TestCase::print_info_string()
{
        cout << "\n[case] execute case:\nTestCase: " << purpose << "\nTestEntry: " << entry << "\nOnloadDelay: " << onload_delay << endl;
        /*try:
            print "\n[case] execute case:\nTestCase: %s\nTestEntry: %s" % (self.purpose, self.entry)
        except Exception, e:
            print "\n[case] execute case:\nTestCase: %s\nTestEntry: %s" % (str2str(self.purpose), str2str(self.entry))
            print "[ Error: found unprintable character in case purpose, error: %s ]\n" % e
        */
}

Json::Value TestCase::to_json()
{
    Json::Value root;

    root["purpose"] = purpose;
    root["entry"] = entry;
    root["expected"] = e_result;
    root["case_id"] = case_id;
    root["pre_condition"] = pre_con;
    root["post_condition"] = post_con;
    root["step_desc"] = steps;
    root["order"] = order;
    root["onload_delay"] = onload_delay;

    return root;
}

Json::Value TestCase::result_to_json()
{
    Json::Value root;

    root["order"] = order;
    root["case_id"] = case_id;
    root["result"] = result;

    if (std_out != "")
    {
        root["stdout"] = std_out;
        root["start_at"] = start_at;
        root["end_at"] = end_at;
    }

    return root;
}

void TestCase::set_result(string test_result, string test_msg, char* end_time)
{
        is_executed = true;
        //cancel_time_check();// don't cancel timer

        result = test_result;

        std_out = test_msg;

        if (end_time) 
        {
            end_at = end_time;
        }
}

void TestCase::set_start_at(char *start_time)
{
        start_at = start_time;
}

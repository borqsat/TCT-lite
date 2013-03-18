#include <stdio.h>
#include <string.h>

#include <signal.h>
#include <sys/time.h>

#include <string>
using namespace std;

#include <json/json.h>

class TestCase
{
public:
    TestCase();
    virtual ~TestCase();

public:
    string result; // "pass" or "fail", "block", "N/A"
    string e_type;
    string start_at;
    string end_at;
    string std_out;
    bool is_executed;

    // below 9 value are sent from Com-module for each case.
    string onload_delay;
    string order; // case order
    string case_id;
    string purpose;
    string entry;
    string pre_con;
    string post_con;
    string steps;
    string e_result; // expect result

public:
    void init(const Json::Value value);// the case_node should be a string in json format
    void print_info_string();
    Json::Value to_json();
    Json::Value result_to_json();
    void set_result(string test_result, string test_msg, char* end_time);
    void set_start_at(char* start_time);

protected:
};

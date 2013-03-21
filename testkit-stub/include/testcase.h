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

    // below m_case are sent from Com-module for each case.
    Json::Value m_case;
    string purpose;

    char m_str_time[32];// to store the time string
public:
    void init(const Json::Value value);// the case_node should be a string in json format
    void print_info_string();
    Json::Value to_json();
    Json::Value result_to_json();
    void set_result(string test_result, string test_msg);
    void set_start_at();
    void getCurrentTime();

protected:
};

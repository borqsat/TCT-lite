#include "testcase.h"

#include <glib-object.h>
#include <json-glib/json-glib.h>

TestCase::TestCase()
{
        case_id = NULL;
        purpose = NULL;
        entry = NULL;
        e_result = NULL;
        pre_con = NULL;
        post_con = NULL;
        steps = NULL;

        timeout = 90;
}

TestCase::~TestCase()
{
        if (case_id) {
                delete[] case_id;
                case_id = NULL;
        }
        if (purpose) {
                delete[] purpose;
                purpose = NULL;
        }
        if (entry) {
                delete[] entry;
                entry = NULL;
        }
        if (e_result) {
                delete[] e_result;
                e_result = NULL;
        }
        if (pre_con) {
                delete[] pre_con;
                pre_con = NULL;
        }
        if (post_con) {
                delete[] post_con;
                post_con = NULL;
        }
        if (steps) {
                delete steps;
                steps = NULL;
        }

        if (msg) {
                delete msg;
                msg = NULL;
        }
}

void TestCase::get_string_value(JsonReader *reader, const char* key, char** value)
{
        json_reader_read_member (reader, key);
        const char* tmp = json_reader_get_string_value (reader);
        json_reader_end_member (reader);
        if (!tmp) return;

        printf("=========%s:%s\n", key, tmp);
        *value = new char[strlen(tmp)+1];
        if (!*value) return;
        memset(*value, 0, strlen(tmp)+1);
        strcpy(*value, tmp);
}

void TestCase::init(char* case_node)
{
        g_type_init ();
        printf("=========%s\n", case_node);

        JsonParser *parser = json_parser_new ();
        json_parser_load_from_data (parser, case_node, -1, NULL);

        JsonReader *reader = json_reader_new (json_parser_get_root (parser));

        json_reader_read_member (reader, "order");
        order = json_reader_get_int_value (reader);
        json_reader_end_member (reader);

        get_string_value(reader, "case_id", &case_id);
        get_string_value(reader, "purpose", &purpose);
        get_string_value(reader, "test_script_entry", &entry);
        get_string_value(reader, "pre_condition", &pre_con);
        get_string_value(reader, "post_condition", &post_con);
        get_string_value(reader, "step_desc", &steps);
        get_string_value(reader, "expected", &e_result);

        g_object_unref (reader);
        g_object_unref (parser);
}

void TestCase::print_info_string()
{
        printf("\n[case] execute case:\nTestCase: %s\nTestEntry: %s", purpose, entry);
        /*try:
            print "\n[case] execute case:\nTestCase: %s\nTestEntry: %s" % (self.purpose, self.entry)
        except Exception, e:
            print "\n[case] execute case:\nTestCase: %s\nTestEntry: %s" % (str2str(self.purpose), str2str(self.entry))
            print "[ Error: found unprintable character in case purpose, error: %s ]\n" % e
        */
}

bool TestCase::is_manual()
{
        return (strcmp(e_type, "auto") != 0);
}

void TestCase::to_json(char* str)
{
        sprintf(str, "{\"purpose\":%s, \"entry\":%s, \"expected\":%s, \"case_id\":%s, \"pre_condition\":%s, \"post_condition\":%s, \"steps\":%s, \"order\":%d}", purpose, entry, e_result, case_id, pre_con, post_con, steps, order);
}

void TestCase::set_result(char* test_result, char* test_msg)
{
        is_executed = true;
        cancel_time_check();

        strcpy(result, test_result);

        if (msg) delete[] msg;
        msg = new char[strlen(test_msg)+1];
        if (msg) strcpy(msg, test_msg);

        /*self.xml_node.set("result", test_result)
        if self.xml_node.find("./result_info") is not None:
            self.xml_node.remove(self.xml_node.find("./result_info"))

        result_info = ElementTree.SubElement(self.xml_node, "result_info")
        actual_result = ElementTree.SubElement(result_info, "actual_result")
        actual_result.text = str(test_result)
        
        start  = ElementTree.SubElement(result_info, "start")
        end    = ElementTree.SubElement(result_info, "end")
        stdout = ElementTree.SubElement(result_info, "stdout") 

        start.text  = str(self.start_at)
        end.text    = str(datetime.now())
        stdout.text = self.msg*/ 
}

void TestCase::set_start_at(int start_at, void(*fn)(int))
{
        this->start_at = start_at;
        if (timeout > 0) {
            memset ( &sa, 0, sizeof ( sa ) ) ;

            sa.sa_handler = fn;
            sigaction ( SIGALRM, &sa, NULL );

            timer.it_value.tv_sec = 0 ;
            timer.it_value.tv_usec = 100000;
            timer.it_interval.tv_sec = 0;
            timer.it_interval.tv_usec = 100000 ;

            setitimer ( ITIMER_REAL, &timer, NULL ) ;
        }
}

void TestCase::cancel_time_check()
{
        timer.it_value.tv_sec = 0 ;
        timer.it_value.tv_usec = 0;
        timer.it_interval.tv_sec = 0;
        timer.it_interval.tv_usec = 0;
        setitimer ( ITIMER_REAL, &timer, NULL ); // set timer with value 0 will stop the timer
        // refer to http://linux.die.net/man/2/setitimer, each process only have 1 timer of the same type.
}

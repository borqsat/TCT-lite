#include "../testcase.h"

int case_count = 3; // suppose we have 3 cases
TestCase* testcase_array[3];// array of pointer of testcase
char* current_case_id = NULL;

void timer_handler ( int signum)
{
	for (int i = 0; i < case_count; i++) // go through the case array to check which case should be handle
		if (testcase_array[i]) 
			if (strcmp(current_case_id, testcase_array[i]->case_id) == 0) {
            printf("time out %d\n", testcase_array[i]->timer.it_value.tv_usec);
            testcase_array[i]->cancel_time_check();
            testcase_array[i]->check_result();
    }
}

int main()
{
        char* tmp = "{\"order\":1, \"case_id\":\"css3_3Dtransforms_tests_entry2257\", \"purpose\":\"Boundaries with 'transform: perspective(200px); transform-style: preserve-3d' on test div's grandparent, 'transform: rotate3d(0, 0.6, 0.8, 90deg); transform-style: preserve-3d' on test div's parent, 'transform: rotate3d(0, 0.6, 0.8, 90deg)' on test div, set via setAttribute(); switch style 3\", \"test_script_entry\":\"/opt/cts-webapi-w3c-css3-tests/3DTransforms/csswg/3d-transforms.html?total_num=3893&amp;amp;locator_key=id&amp;amp;value=2257\", \"pre_condition\":\"\", \"post_condition\":\"\", \"step_desc\":\"Use WRT to visit the 'Test script entry' to check Boundaries with 'transform: perspective(200px); transform-style: preserve-3d' on test div's grandparent, 'transform: rotate3d(0, 0.6, 0.8, 90deg); transform-style: preserve-3d' on test div's parent, 'transform: rotate3d(0, 0.6, 0.8, 90deg)' on test div, set via setAttribute(); switch style 3\", \"expected\":\"All test results must be compliance with relevant pages' descriptions.\"}";

        for (int i = 0; i < case_count; i++) testcase_array[i] = NULL;
	    int i = 0;
        testcase_array[i] = new TestCase();
        testcase_array[i]->init(tmp);
        current_case_id = new char[strlen(testcase_array[i]->case_id) + 1];
        if (!current_case_id) return -1;
        strcpy(current_case_id, testcase_array[i]->case_id);

        testcase_array[i]->set_start_at(10, &timer_handler);

for (;;);

        delete[] current_case_id;
        for (int i = 0; i < case_count; i++) 
        	if (testcase_array[i]) delete testcase_array[i];

        return 0;
}

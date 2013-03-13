#include "../httpserver.h"

int main()
{
        HttpServer httpserver;

        httpserver.m_block_case_count = 3;// suppose we have 3 cases
        httpserver.m_test_cases =  new TestCase[httpserver.m_block_case_count];

        char* result = "N/A";
        char* msg = "";
        char* tmp = "{\"order\":\"1\", \"case_id\":\"css3_3Dtransforms_tests_entry2257\", \"purpose\":\"Boundaries with 'transform: perspective(200px); transform-style: preserve-3d' on test div's grandparent, 'transform: rotate3d(0, 0.6, 0.8, 90deg); transform-style: preserve-3d' on test div's parent, 'transform: rotate3d(0, 0.6, 0.8, 90deg)' on test div, set via setAttribute(); switch style 3\", \"test_script_entry\":\"/opt/cts-webapi-w3c-css3-tests/3DTransforms/csswg/3d-transforms.html?total_num=3893&amp;amp;locator_key=id&amp;amp;value=2257\", \"pre_condition\":\"\", \"post_condition\":\"\", \"step_desc\":\"Use WRT to visit the 'Test script entry' to check Boundaries with 'transform: perspective(200px); transform-style: preserve-3d' on test div's grandparent, 'transform: rotate3d(0, 0.6, 0.8, 90deg); transform-style: preserve-3d' on test div's parent, 'transform: rotate3d(0, 0.6, 0.8, 90deg)' on test div, set via setAttribute(); switch style 3\", \"expected\":\"All test results must be compliance with relevant pages' descriptions.\"}";
        httpserver.m_test_cases[0].init(tmp);
        //httpserver.m_test_cases[0].set_result(result, msg, "1");

        tmp = "{\"order\":\"2\", \"case_id\":\"css3_3Dtransforms_tests_entry2258\", \"purpose\":\"ut-cases\", \"test_script_entry\":\"/opt/cts-webapi-w3c-css3-tests/3DTransforms/csswg/3d-transforms.html?total_num=3893&amp;amp;locator_key=id&amp;amp;value=2257\", \"pre_condition\":\"\", \"post_condition\":\"\", \"step_desc\":\"Use WRT to visit the 'Test script entry' to check Boundaries with 'transform: perspective(200px); transform-style: preserve-3d' on test div's grandparent, 'transform: rotate3d(0, 0.6, 0.8, 90deg); transform-style: preserve-3d' on test div's parent, 'transform: rotate3d(0, 0.6, 0.8, 90deg)' on test div, set via setAttribute(); switch style 3\", \"expected\":\"All test results must be compliance with relevant pages' descriptions.\"}";
        httpserver.m_test_cases[1].init(tmp);
        //httpserver.m_test_cases[1].set_result(result, msg, "2");

        tmp = "{\"order\":\"3\", \"case_id\":\"css3_3Dtransforms_tests_entry2259\", \"purpose\":\"Boundaries with 'transform: perspective(200px); transform-style: preserve-3d' on test div's grandparent, 'transform: rotate3d(0, 0.6, 0.8, 90deg); transform-style: preserve-3d' on test div's parent, 'transform: rotate3d(0, 0.6, 0.8, 90deg)' on test div, set via setAttribute(); switch style 3\", \"test_script_entry\":\"/opt/cts-webapi-w3c-css3-tests/3DTransforms/csswg/3d-transforms.html?total_num=3893&amp;amp;locator_key=id&amp;amp;value=2257\", \"pre_condition\":\"\", \"post_condition\":\"\", \"step_desc\":\"Use WRT to visit the 'Test script entry' to check Boundaries with 'transform: perspective(200px); transform-style: preserve-3d' on test div's grandparent, 'transform: rotate3d(0, 0.6, 0.8, 90deg); transform-style: preserve-3d' on test div's parent, 'transform: rotate3d(0, 0.6, 0.8, 90deg)' on test div, set via setAttribute(); switch style 3\", \"expected\":\"All test results must be compliance with relevant pages' descriptions.\"}";
        httpserver.m_test_cases[2].init(tmp);
        //httpserver.m_test_cases[2].set_result(result, msg, "3");

        //httpserver.killAllWidget();

	    struct HttpRequest httprequest;
    	httprequest.content = NULL;


    	httprequest.path = new char[1024];

		httpserver.g_client_command = new char[128];
		sprintf(httpserver.g_client_command, "aul_test launch api3nonw3c");
		//sprintf(httpserver.g_client_command, "aul_test launch api1alarm0");
		//sprintf(httpserver.g_client_command, "aul_test launch api1nfc000");
        httpserver.start_client(httpserver.g_client_command);

    	//memset(httprequest.path, 0, 1024);
    	//strcpy(httprequest.path, "/init_test");
        //httpserver.processpost(1, &httprequest);

    	memset(httprequest.path, 0, 1024);
    	strcpy(httprequest.path, "/check_server");
        httpserver.processpost(1, &httprequest);

    	memset(httprequest.path, 0, 1024);
    	strcpy(httprequest.path, "/check_server_status");
        httpserver.processpost(1, &httprequest);

    	memset(httprequest.path, 0, 1024);
    	strcpy(httprequest.path, "/shut_down_server");
        httpserver.processpost(1, &httprequest);

    	memset(httprequest.path, 0, 1024);
    	strcpy(httprequest.path, "/ask_next_step");
        httpserver.processpost(1, &httprequest);

    	memset(httprequest.path, 0, 1024);
    	strcpy(httprequest.path, "/init_session_id?session_id=1024");
        httpserver.processpost(1, &httprequest);

    	memset(httprequest.path, 0, 1024);
    	strcpy(httprequest.path, "/auto_test_task?session_id=1024");
    	httprequest.content = "session_id=1024";
        httpserver.processpost(1, &httprequest);

    	memset(httprequest.path, 0, 1024);
    	strcpy(httprequest.path, "/manual_cases");
        httpserver.processpost(1, &httprequest);

    	memset(httprequest.path, 0, 1024);
    	strcpy(httprequest.path, "/case_time_out");
        httpserver.processpost(1, &httprequest);

    	memset(httprequest.path, 0, 1024);
    	httprequest.content = "purpose=ut-cas&result=N/A";
    	strcpy(httprequest.path, "/commit_manual_result");
        httpserver.processpost(1, &httprequest);

    	memset(httprequest.path, 0, 1024);
    	strcpy(httprequest.path, "/check_execution_progress");
        httpserver.processpost(1, &httprequest);

    	memset(httprequest.path, 0, 1024);
    	strcpy(httprequest.path, "/generate_xml");
        httpserver.processpost(1, &httprequest);

    	memset(httprequest.path, 0, 1024);
    	strcpy(httprequest.path, "/commit_result");
        httpserver.processpost(1, &httprequest);

    	memset(httprequest.path, 0, 1024);
    	strcpy(httprequest.path, "/check_execution_progress");
        httpserver.processpost(1, &httprequest);

        httpserver.StartUp();

	    if(httprequest.path != NULL) delete[] httprequest.path;

        return 0;
}

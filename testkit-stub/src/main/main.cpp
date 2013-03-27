#include <string>
#include <json/json.h>

#include "httpserver.h"

#define SERVER_PORT 8000
#define MAX_BUF 8192

#define GET_COMMON   0
#define GET_CGI   1
#define HEAD   2
#define POST   3
#define TRACR  4
#define BAD_REQUEST -1

int gServerStatus = 0;
int gIsRun = 0;

FILE *pfilelog = NULL;

//parse the cmd line parameters
void parse(int count, char *argv[], HttpServer *httpserver) {
	for (int i = 1; i < count; ++i) {
		string argvstr = argv[i];
		int sepindex = argvstr.find(":");
		if (sepindex > -1) {
			string key = argvstr.substr(0, sepindex);
			string value = argvstr.substr(sepindex + 1);

			if (key == "--port") {
				httpserver->g_port = value;
			} else if (key == "--hidestatus") {
				httpserver->g_hide_status = value;
			} else if (key == "--pid_log") {
				httpserver->g_pid_log = value;
			} else if (key == "--testsuite") {
				httpserver->g_test_suite = value;
				httpserver->run_cmd("wrt-launcher -l | grep " + value + " | awk '{print $NF}'", "", true);
				if (httpserver->m_output == "")
					httpserver->m_invalid_suite = true;
				else {
					httpserver->g_launch_cmd = "wrt-launcher -s " + httpserver->m_output;
					httpserver->g_kill_cmd = "wrt-launcher -k " + httpserver->m_output;
				}
			} else if (key == "--exe_sequence") {
				httpserver->g_exe_sequence = value;
			} else if (key == "--enable_memory_collection") {
				httpserver->g_enable_memory_collection = value;
			}
		}
	}
}

int main(int argc, char *argv[]) {
	HttpServer httpserver;
	if (argc > 1) {
		parse(argc, argv, &httpserver);
	}
	httpserver.StartUp();
	return 0;
}


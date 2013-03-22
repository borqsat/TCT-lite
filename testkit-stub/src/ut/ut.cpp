#include "httpserver.h"

int main() {
	HttpServer* httpserver = new HttpServer();

	httpserver->parse_json_str("test.json");

	struct HttpRequest httprequest;

	httprequest.path = "/init_test";
	httpserver->processpost(1, &httprequest);

	httpserver->g_test_suite = "api3nonw3c";

	httprequest.path = "/check_server";
	httpserver->processpost(1, &httprequest);

	httprequest.path = "/check_server_status";
	httpserver->processpost(1, &httprequest);

	httprequest.path = "/shut_down_server";
	httpserver->processpost(1, &httprequest);

	httprequest.path = "/ask_next_step";
	httpserver->processpost(1, &httprequest);

	httprequest.path = "/init_session_id?session_id=1024";
	httpserver->processpost(1, &httprequest);

	httprequest.path = "/auto_test_task?session_id=1024";
	httprequest.content = "session_id=1024";
	httpserver->processpost(1, &httprequest);

	httprequest.path = "/manual_cases";
	httpserver->processpost(1, &httprequest);

	httprequest.content = "purpose=ut-cas&result=N/A";
	httprequest.path = "/commit_manual_result";
	httpserver->processpost(1, &httprequest);

	httprequest.path = "/check_execution_progress";
	httpserver->processpost(1, &httprequest);

	httprequest.path = "/generate_xml";
	httpserver->processpost(1, &httprequest);

	httprequest.path = "/commit_result";
	httpserver->processpost(1, &httprequest);

	httprequest.path = "/check_execution_progress";
	httpserver->processpost(1, &httprequest);

	httpserver->StartUp();

	delete httpserver;

	return 0;
}

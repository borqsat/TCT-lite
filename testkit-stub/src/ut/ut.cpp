#include "httpserver.h"

int main() {
	HttpServer* httpserver = new HttpServer();

	httpserver->parse_json_str("src/ut/test.json");

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

	httprequest.content = "purpose=Verify setter of Uint16Array&result=N/A";
	httprequest.path = "/commit_result";
	httpserver->processpost(1, &httprequest);

	httprequest.path = "/check_execution_progress";
	httpserver->processpost(1, &httprequest);

	httprequest.path = "/set_capability";
	httprequest.content = "{\"name1\":true, \"name2\":45, \"name3\":\"678\"}";
	httpserver->processpost(1, &httprequest);

	httprequest.path = "/capability";
	httprequest.content = "name=name1";
	httpserver->processpost(1, &httprequest);

	httprequest.path = "/capability?name=name2&value=45";
	httprequest.content = "name=name2&value=45";
	httpserver->processpost(1, &httprequest);

	httprequest.path = "/capability?name=name3&value=678";
	httprequest.content = "name=name3&value=678";
	httpserver->processpost(1, &httprequest);

	httprequest.path = "/capability?name=name4";
	httprequest.content = "name=name4";
	httpserver->processpost(1, &httprequest);

	httprequest.path = "/set_capability";
	httprequest.content = "{\"bluetooth\":true, \"nfc\":true, \"multiTouchCount\":true, \"inputKeyboard\":true, \"wifi\":true, \"wifiDirect\":true, \"openglesVersion1_1\":true, \"openglesVersion2_0\":true, \"fmRadio\":true, \"platformVersion\":true, \"webApiVersion\":true, \"nativeApiVersion\":true, \"platformName\":true, \"cameraFront\":true, \"cameraFrontFlash\":true, \"cameraBack\":true, \"cameraBackFlash\":true, \"location\":true, \"locationGps\":true, \"locationWps\":true, \"microphone\":true, \"usbHost\":true, \"usbAccessory\":true, \"screenOutputRca\":true, \"screenOutputHdmi\":true, \"platformCoreCpuArch\":true, \"platformCoreFpuArch\":true, \"sipVoip\":true, \"duid\":true, \"speechRecognition\":true, \"accelerometer\":true, \"barometer\":true, \"gyroscope\":true, \"magnetometer\":true, \"proximity\":true}";
	httpserver->processpost(1, &httprequest);

	httpserver->StartUp();

	delete httpserver;

	return 0;
}

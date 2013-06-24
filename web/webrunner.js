
var iTest = 0;

var Tests;
var statusNode;
var oTestFrame;
var statusFrame;
var frmset;
var xmldoc;

var startTime;
var defTime = 2000;
var timeout;
var winCloseTimeout = 5000;
var blockCheckTime = 10;

var server = "http://127.0.0.1:8000";
var need_ajax = true;

var hidestatus;
var ttestsuite;
var tpriority;
var tstatus;
var ttype;
var tcategory;
var texecutiontype;

var manualcaseslist;

var cursuite;
var curset;

var last_test_page = "";
var current_page_uri = "";

var activetest = true;

var manualcases = function() {
	this.casesid = "";
	this.index = 0;
	this.result = "";
};

function getTestPageParam(uri, param) {
	var uri_local = uri;
	var iLen = param.length;
	var iStart = uri_local.indexOf(param);
	if (iStart == -1)
		return "";
	iStart += iLen + 1;
	var iEnd = uri_local.indexOf("&", iStart);
	if (iEnd == -1)
		return uri_local.substring(iStart);

	return uri_local.substring(iStart, iEnd);
}

function Parm(data, name) {
	var p;
	ts = $(data).find(name);
	if (ts) {
		t = $(ts).get(0);
		if (t)
			p = $(t).text().trim();
	}

	if (p) {
		var rawVal = decodeURI(p);
		if (rawVal.indexOf(',') < 0)
			p = rawVal;
		else
			p = rawVal.split(',');
	}

	return p;
}

function getParms() {
	var parms = new Array();
	var str = location.search.substring(1);
	var items = str.split('&');
	for ( var i = 0; i < items.length; i++) {
		var pos = items[i].indexOf('=');
		if (pos > 0) {
			var key = items[i].substring(0, pos);
			var val = items[i].substring(pos + 1);
			if (!parms[key]) {
				var rawVal = decodeURI(val);
				if (rawVal.indexOf(',') < 0)
					parms[key] = rawVal;
				else
					parms[key] = rawVal.split(',');
			}
		}
	}

	ttestsuite = parms["testsuite"];
	tpriority = parms["priority"];
	hidestatus = parms["hidestatus"];
	tstatus = parms["status"];
	ttype = parms["type"];
	tcategory = parms["category"];
	texecutiontype = parms["execution_type"];
	if (need_ajax) {
		$.ajax({
			async : false,
			type : "GET",
			url : server + "/get_params",
			dataType : "xml",
			success : function(data) {
				hidestatus = Parm(data, 'hidestatus');
			},
			error : function(x, t, e) {
				print_error_log("getParms", e);
			}
		});
	}
}

function runTestsuite_nofilter(xml) {
	xmldoc = xml;
	Tests = $(xml).find("testcase");
	doTest();
}

function runTestsuite(xml) {
	xmldoc = xml;
	$(xml).find("testcase").each(
			function() {
				var v, vType;
				v = $(this).attr('execution_type');

				if (texecutiontype && texecutiontype == "manual")
					vType = "manual";
				else if (texecutiontype && texecutiontype == "auto")
					vType = "auto";
				else if (!texecutiontype)
					vType = [ "auto", "manual" ];
				else
					vType = "auto";

				if (v != vType && $.inArray(v, vType) < 0)
					$(this).remove();
				v = $(this).attr('priority');
				if (tpriority && v != tpriority
						&& $.inArray(v, tpriority) < 0)
					$(this).remove();
				v = $(this).attr('status');
				if (tstatus && v != tstatus && $.inArray(v, tstatus) < 0)
					$(this).remove();
				v = $(this).attr('type');
				if (ttype && v != ttype && $.inArray(v, ttype) < 0)
					$(this).remove();
				var categories = $(this).find("categories > category");
				if (categories.length > 0 && tcategory) {
					var i;
					var found = false;
					for (i = 0; i < categories.length; i++) {
						var category = $(categories).get(i);
						if ($(category).text().trim() != tcategory
								&& $.inArray($(category).text().trim(),
										tcategory) < 0) {
							found = true;
							break;
						}
					}
					if (!found)
						$(this).remove();
				}

				$(this).attr('result', "N/A");
			});
	Tests = $(xml).find("testcase");
	xmldoc = xml;
	save_result();
	doTest();
}

function precheck_init() {
	server_url = "http://127.0.0.1:8000/check_server";
	$.ajax({
		async : false,
		url : server_url,
		type : "GET",
		success : init_test,
		error : function(x, t, e) {
			print_error_log("can't find a http server",
					"run widget in the standalone mode");
			need_ajax = false;
			init();
		}
	});
}

function init() {
	getParms();

	oTestFrame = document.getElementById('testframe');
	if (!oTestFrame)
		return;

	statusFrame = document.getElementById('statusframe');
	if (!statusFrame)
		return;

	var statusWin = statusFrame.contentWindow;
	if (!statusWin)
		return;

	statusNode = statusWin.document.createElement("div");
	if (!statusNode)
		return;
	statusWin.document.body.appendChild(statusNode);

	frmset = $($('#main')).get(0);
	if (!frmset)
		return;

	if (hidestatus && hidestatus == "1")
		$(frmset).attr('rows', "0, *");
	if (need_ajax) {
		$.ajax({
			async : false,
			type : "GET",
			url : server + '/get_testsuite',
			dataType : "xml",
			success : runTestsuite_nofilter,
			error : function(x, t, e) {
				print_error_log("init", e);
			}
		});
	}
	if (!xmldoc) {
		if (!ttestsuite) {
			ttestsuite = 'tests.xml';
		}
		$.ajax({
			async : false,
			type : "GET",
			url : ttestsuite,
			dataType : "xml",
			success : runTestsuite,
			error : function(x, t, e) {
				print_error_log("init", e);
			}
		});
	}
}

function escape_html(s) {
	return s.replace(/\&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g,
			"&quot;").replace(/'/g, "&#39;");
}

function check_timeout(time) {
	if (time == 11) {
		report('BLOCK', "Time is out");
	}
	sleep_time = time * 50;
	setTimeout("CheckResult('yes', " + time + ")", sleep_time);
}

function CheckResult(need_check_block, sleep_time) {
	var message = "";
	var total_num = "";
	var locator_key = "";
	var value = "";

	var oTestWin = oTestFrame.contentWindow;
	var oTestDoc = oTestWin.document;
	var case_uri = current_page_uri;

	try {
		if (oTestWin.document.readyState == "complete") {
			total_num = getTestPageParam(case_uri, "total_num");
			locator_key = getTestPageParam(case_uri, "locator_key");
			value = getTestPageParam(case_uri, "value");

			oPass = $(oTestDoc).find(".pass");
			oFail = $(oTestDoc).find(".fail");

			// Test page has parameters
			if (total_num != "" && locator_key != "" && value != "") {
				if (locator_key == "id") {
					var results;
					var passes;
					var fails;

					var oRes = $(oTestDoc).find("table#results");
					if (oRes) {
						results = $(oRes).find('tr');
						passes = $(oRes).find('tr.pass');
						fails = $(oRes).find('tr.fail');
					}

					if (passes.length + fails.length == total_num) {
						var i = 1;
						for (i = 1; i <= total_num; i++) {
							if (i.toString() != value) {
								continue;
							}
							var rest = results[i].childNodes[0].innerText;
							var desc = results[i].childNodes[1].innerText;
							var msg = results[i].childNodes[2].innerText;
							if (rest && rest.toUpperCase() == "PASS")
								report('PASS', msg);
							else
								report('FAIL', msg);
							break;
						}
					} else {
						var i;
						for (i = 0; i < fails.length; i++) {
							var desccell = fails[i].childNodes[1];
							if (desccell)
								message += "###Test Start###"
										+ desccell.innerText
										+ "###Test End###";
							var msgcell = fails[i].childNodes[2];
							if (msgcell)
								message += "###Error1 Start###"
										+ msgcell.innerText
										+ "###Error1 End###";
						}
						report('FAIL', message);
					}
				} else if (locator_key == "test_name") {
					// Place holder
				} else if (locator_key == "msg") {
					// Place holder
				} else {
					alert("Unknown locator key");
				}
			} else if (oPass.length > 0 && oFail.length == 0) {
				if (oTestWin.resultdiv)
					message = oTestWin.resultdiv.innerHTML;
				report('PASS', message);
			} else if (oFail.length > 0) {
				var oRes = $($(oTestDoc).find("table#results")).get(0);
				// Get error log
				if (oRes) {
					var fails = $(oRes).find('tr.fail');
					var i;
					for (i = 0; i < fails.length; i++) {
						var desccell = fails[i].childNodes[1];
						if (desccell)
							message += "###Test Start###"
									+ desccell.innerText + "###Test End###";
						var msgcell = fails[i].childNodes[2];
						if (msgcell)
							message += "###Error2 Start###"
									+ msgcell.innerText
									+ "###Error2 End###";
					}
				}
				report('FAIL', message);
			} else // oFail.length==0 && oPass.length==0
			if (need_check_block == 'yes') {
				next_sleep_time = sleep_time + 1;
				check_timeout(next_sleep_time);
				return;
			}
		} else // not complete
		if (need_check_block == 'yes') {
			next_sleep_time = sleep_time + 1;
			check_timeout(next_sleep_time);
			return;
		}
	} catch (e) {
		report('BLOCK', e);
	}
}

function report(result, log) {

	if (iTest >= Tests.length)
		return;
	$(Tests[iTest]).attr('result', result);
	var doc = $.parseXML("<result_info>" + "<actual_result>" + result
			+ "</actual_result>" + "<start>" + startTime + "</start>"
			+ "<end>" + new Date() + "</end>" + "<stdout>"
			+ escape_html(log) + "</stdout>" + "</result_info>");
	$(Tests[iTest]).append(doc.documentElement);

	statusNode.innerHTML = "Test #" + (iTest + 1) + "/" + Tests.length
			+ "(" + result + ") " + current_page_uri;

	try {
		var starts = log.indexOf('value:');
		var stops = log.lastIndexOf(',');
		var resultinfo = log.substring(starts + 6, stops);
		$(Tests[iTest]).find("measurement").attr('value', resultinfo);
	} catch (e) {
	}

	iTest++;

	if (activetest) {
		doTest();
	} else {
		activetest = true;
	}
}

function doTest() {
	while (iTest < Tests.length) {
		if ($(Tests[iTest]).attr('execution_type') != 'auto') {
			iTest++;
			continue;
		}
		var ts = $(Tests[iTest]).find('test_script_entry');
		if (ts.length == 0) {
			iTest++;
			continue;
		}
		var it = $(ts).get(0);
		var tstr = $(it).attr('timeout');
		if (!tstr)
			timeout = 8 * defTime;
		else {
			var t;
			try {
				t = parseInt(tstr) * 1000;
			} catch (e) {
				t = 8 * defTime;
			}
			timeout = t;
		}

		pset = $(Tests[iTest]).parent().attr('name');
		psuite = $(Tests[iTest]).parent().parent().attr('name');

		startTime = new Date();

		current_page_uri = $(it).text();
		var index = current_page_uri.indexOf("?");
		var test_page = "";
		if (need_ajax) {
			var svr = server + "/test_hint";
			$.ajax({
				async : false,
				type : "POST",
				url : svr,
				data : {
					suite : psuite,
					set : pset,
					testcase : current_page_uri
				},
				error : function(x, t, e) {
					print_error_log("doTest", e);
				}
			});
		}
		if (index >= 0)
			test_page = current_page_uri.substring(0, index);
		else
			test_page = current_page_uri;

		// Don't load the same test page again
		if (test_page == last_test_page) {
			print_error_log("test page url is the same as the last one",
					test_page);
			activetest = false;
			CheckResult('yes', 0);
			continue;
		}

		if ((current_page_uri.indexOf("2DTransforms") != -1)
				|| (current_page_uri.indexOf("3DTransforms") != -1)) {
			oTestFrame.height = 500000 + "px";
		} else {
			oTestFrame.height = 2500 + "px";
		}
		oTestFrame.src = current_page_uri;
		last_test_page = test_page;
		if (oTestFrame.attachEvent) {
			oTestFrame.attachEvent("onload", function() {
				CheckResult('yes', 0);
			});
		} else {
			oTestFrame.onload = function() {
				CheckResult('yes', 0);
			};
		}
		return;
	}
	doManualTest();
}

function doManualTest() {
	manualcaseslist = new Array();
	var iTemp1 = 0, iTemp2 = 0;
	while (iTemp1 < Tests.length) {
		if ($(Tests[iTemp1]).attr('execution_type') == 'manual') {
			parent.document.getElementById("statusframe").height = 385 + "px";
			manualcaseslist[iTemp2] = new manualcases();
			manualcaseslist[iTemp2].casesid = $(Tests[iTemp1]).attr('id');
			manualcaseslist[iTemp2].index = iTemp1;
			manualcaseslist[iTemp2].result = $(Tests[iTemp1])
					.attr('result');
			iTemp2++;
		}
		iTemp1++;
	}
	if (iTemp2 > 0) {
		winCloseTimeout = 50000;
		statusFrame.src = "./manualharness.html";
		$(frmset).attr('rows', "100,*");
	} else if (iTest == Tests.length) {
		setTimeout("PublishResult()", 2000);
	}
	oTestFrame.src = '';
}

function PublishResult() {
	$(frmset).attr('rows', "0, *");
	results = oTestFrame.contentWindow;
	var resultXML;
	resultXML = "<title>HTML5 Test Result XML</title>";
	resultXML += "<head> <style type='text/css'>\
html {font-family:DejaVu Sans, Bitstream Vera Sans, Arial, Sans;}\
section#summary {margin-bottom:1em;}\
table#results {\
border-collapse:collapse;\
table-layout:fixed;\
width:80%;\
}\
table#results th:first-child,\
table#results td:first-child {\
width:40%;\
}\
table#results th:last-child,\
table#results td:last-child {\
width:30%;\
}\
table#results th {\
padding:0;\
padding-bottom:0.5em;\
text-align:left;\
border-bottom:medium solid black;\
}\
table#results td {\
padding:1em;\
padding-bottom:0.5em;\
border-bottom:thin solid black;\
}\
</style><head>";

	resultXML += "<section id='summary'>";
	resultXML += "<h2>Summary</h2>";
	var ipass = $(xmldoc).find("testcase[result='PASS']").length;
	var failList = $(xmldoc).find("testcase[result='FAIL']");
	var ifail = failList.length;
	resultXML += "<h3>Total:" + Tests.length
			+ " Pass:<span style='color:green;'>" + ipass
			+ "</span> Fail:<span style='color:red;'>" + ifail
			+ "</span></h3>";
	resultXML += "</section>";

	resultXML += "<p><table id='results'> <tr> <th> TestSet </th> <th> Pass </th> <th> Fail </th></tr>";
	var Sets = $(xmldoc).find("set");
	var i = 0;
	for (i = 0; i < Sets.length; i++) {
		ipass = $(Sets[i]).find("testcase[result='PASS']").length;
		ifail = $(Sets[i]).find("testcase[result='FAIL']").length;
		resultXML += "<tr>";
		resultXML += "<td>" + $(Sets[i]).attr('name') + "</td>";
		resultXML += "<td style='color:green;'>" + ipass
				+ "</td><td style='color:red;'>" + ifail + "</td>";
		resultXML += "</tr>";
	}
	resultXML += "</table>";

	if (ifail > 0) {
		resultXML += "<section id='failedlist'>";
		resultXML += "<h2>Fails</h2>";
		resultXML += "<ul>";
		for (i = 0; i < failList.length; i++) {
			var ts = $(failList[i]).find("test_script_entry");
			if (ts.length > 0) {
				var t = ts.get(0);
				resultXML += "<li style='color:red;'>" + $(t).text()
						+ "</li>";
			}
		}
		resultXML += "</ul>";
		resultXML += "</section>";
	}

	resultXML += "<h2>Details</h2>";
	resultXML += "<form method='post' id='resultform'> <textarea id='results' style='width: 80%; height: 90%;' name='filecontent' disabled='disabled'>"
			+ save_result() + "</textarea></form>";
	setTimeout("window.open('','_self','');window.close()", winCloseTimeout);
	results.document.writeln(resultXML);
}

function save_result() {
	var svr = server + "/save_result";
	var testid = (new Date()).getTime();
	var contents = (new XMLSerializer()).serializeToString(xmldoc);
	if (need_ajax) {
		$.ajax({
			async : false,
			type : "POST",
			url : svr,
			data : {
				filename : testid,
				filecontent : contents
			},
			error : function(x, t, e) {
				print_error_log("doTest", e);
			}
		});
	}
	return contents;
}
// merge code from application.js
function init_test() {
	var session_id = Math.round(Math.random() * 10000);
	init_message_frame();
	save_session_id(session_id);
	sync_session_id(session_id);
	start_test();
}

function init_message_frame() {
	messageFrame = document.getElementById('messageframe');
	messageWin = messageFrame.contentWindow;
	messageNode = messageWin.document.getElementById('message_div');
	if (null == messageNode) {
		messageNode = messageWin.document.createElement("div");
		messageNode.id = "message_div";
		messageWin.document.body.appendChild(messageNode);
		messageNode.innerHTML = "Message Area";
	}
	return messageNode;
}

function print_error_log(command, message) {
	messageFrame = document.getElementById('messageframe');
	messageFrame.height = 160 + "px";
	messageNode = init_message_frame();
	messageNode.innerHTML = "Message Area<div id=\"log_title\"></div><br/>Command: <div id=\"log_command\">"
			+ command
			+ "</div><br/>Message: <div id=\"log_message\">"
			+ message + "</div>";
}

function save_session_id(session_id) {
	statusFrame = document.getElementById('statusframe');
	statusFrame.height = 270 + "px";
	statusWin = statusFrame.contentWindow;
	sessionIdNode = statusWin.document.getElementById('session_id_div');
	if (null == sessionIdNode) {
		sessionIdNode = statusWin.document.createElement("div");
		sessionIdNode.id = "session_id_div";
		statusWin.document.body.appendChild(sessionIdNode);
		sessionIdNode.innerHTML = "Session ID: <div id=\"session_id\">"
				+ session_id
				+ "</div><br/><div id=\"execution_progress\"></div><br/>";
	}
}

function sync_session_id(session_id) {
	var server_url = server + "/init_session_id";
	server_url += "?session_id=" + session_id;
	$.ajax({
		async : false,
		url : server_url,
		type : "GET",
		error : function(x, t, e) {
			print_error_log("sync_session_id", e);
		}
	});
}

function get_session_id() {
	statusFrame = document.getElementById('statusframe');
	statusWin = statusFrame.contentWindow;
	sessionIdNode = statusWin.document.getElementById('session_id');
	return sessionIdNode.innerHTML;
}

function close_window(){
	//for webapi-nonw3c-webgl-tests run by tizen-tool emulator html,window.parent.close() no function,must call window.close, why?
	if(window.parent != window.self){
		window.open('','_self','');
		window.close();
		window.parent.onbeforeunload = null;
		window.parent.close();
	}
	else{
		window.open('','_self','');
		window.close();
	}
}
function start_test() {
	try {
		var task = ask_test_task();
	} catch (e) {
		print_error_log("start_test_ask_test_task", e);
	}
	try {
		if (task == 1) {
			print_error_log("start_test_execute_test_task",
					"Invalid session");
		} else if (task == -1) {
			print_error_log("restart client process activated",
					"this window will be closed in 2sec");
			close_window();
			//setTimeout("window.open('','_self','');window.close()", 2000);
		} else if (task == null) {
			print_error_log(
					"get auto case failed, client will be restarted later",
					"this window will be closed in 2sec");
			close_window();
			//setTimeout("window.open('','_self','');window.close()", 2000);
		} else if (task != 0) {
			var progress = check_execution_progress();
			execute_test_task(task, progress);
		} else {
			execute_manual_test();
		}
	} catch (e) {
		print_error_log("start_test_execute_test_task", e);
	}
}

function ask_generate_xml() {
	var server_url = server + "/generate_xml";
	$.ajax({
		async : false,
		url : server_url,
		type : "GET",
		error : function(x, t, e) {
			print_error_log("ask_generate_xml", e);
		}
	});
	close_window();
	//setTimeout("window.open('','_self','');window.close()", winCloseTimeout);
}

function extract_all_manual() {
	var server_url = server + "/manual_cases";
	var tasks = null;
	$.ajax({
		async : false,
		url : server_url,
		type : "GET",
		dataType : "text",
		success : function(txt) {
			task = $.parseJSON(txt);
			if (0 == task.none) {
				task = null;
			}
		},
		error : function(x, t, e) {
			print_error_log("extract_all_manual", e);
		}
	});
	return task;
}

function ask_test_task() {
	var server_url = server + "/auto_test_task";
	var task = null;
	session_id = get_session_id();
	server_url += "?session_id=" + session_id;
	$.ajax({
		async : false,
		url : server_url,
		type : "GET",
		dataType : "text",
		success : function(txt) {
			task = $.parseJSON(txt);
			if (task.none == 0) {
				task = 0;
			}
			if (task.invalid == 0) {
				task = 1;
			}
			if (task.stop == 0) {
				task = -1;
			}
		},
		error : function(x, t, e) {
			print_error_log("ask_test_task", e);
		}
	});
	return task;
}

function check_execution_progress() {
	var server_url = server + "/check_execution_progress";
	var progress = null;
	session_id = get_session_id();
	server_url += "?session_id=" + session_id;
	$.ajax({
		async : false,
		url : server_url,
		type : "GET",
		dataType : "text",
		success : function(txt) {
			progress = $.parseJSON(txt);
		},
		error : function(x, t, e) {
			print_error_log("check_execution_progress", e);
		}
	});
	return progress;
}

function ask_next_step() {
	var server_url = server + "/ask_next_step";
	var next_step = null;
	session_id = get_session_id();
	server_url += "?session_id=" + session_id;
	$.ajax({
		async : false,
		url : server_url,
		type : "GET",
		dataType : "text",
		success : function(txt) {
			next_step = $.parseJSON(txt);
		},
		error : function(x, t, e) {
			print_error_log("ask_next_step", e);
		}
	});
	return next_step;
}

function init_status_frame() {
	statusFrame = document.getElementById('statusframe');
	statusWin = statusFrame.contentWindow;
	statusNode = statusWin.document.getElementById('status_div');
	if (null == statusNode) {
		statusNode = statusWin.document.createElement("div");
		statusNode.id = "status_div";
		statusWin.document.body.appendChild(statusNode);
	}
	return statusNode;
}

function execute_test_task(json_task, json_progress) {
	try {
		oTestFrame = document.getElementById('testframe');
		statusNode = init_status_frame();
		// update execution progress
		statusFrame = document.getElementById('statusframe');
		statusWin = statusFrame.contentWindow;
		progressNode = statusWin.document
				.getElementById('execution_progress');
		progressNode.innerHTML = "Total:" + json_progress.total
				+ ", Current:" + json_progress.current;
		// update case info
		statusNode.innerHTML = "Test Purpose:<div id=\"test_purpose_div\">"
				+ json_task.purpose
				+ "</div><br/>Test Entry:<div id=\"test_entry_div\">"
				+ json_task.entry
				+ "</div><br/>Last Test Result:<div id=\"test_result_div\">"
				+ json_progress.last_test_result + "</div>";
		current_page_uri = json_task.entry;
		case_id_str = json_task.case_id;
		var index = current_page_uri.indexOf("?");
		var test_page = "";
		if (index >= 0)
			test_page = current_page_uri.substring(0, index);
		else
			test_page = current_page_uri;
		// Get how many times to check BLOCK result
		if (json_task.onload_delay) {
			calculate_block_check_time(parseInt(json_task.onload_delay) * 1000);
		} else {
			print_error_log("execute_test_task",
					"can't get attribute onload_delay from task: "
							+ json_task.purpose);
		}
		// Don't load the same test page again
		if (test_page == last_test_page) {
			print_error_log("test page url is the same as the last one",
					test_page);
			extract_case_result('yes', 0);
			return;
		}
		if ((current_page_uri.indexOf("2DTransforms") != -1)
				|| (current_page_uri.indexOf("3DTransforms") != -1)) {
			oTestFrame.height = 500000 + "px";
		} else {
			oTestFrame.height = 2500 + "px";
		}
		oTestFrame.src = current_page_uri;
		last_test_page = test_page;
		if (oTestFrame.attachEvent) {
			oTestFrame.attachEvent("onload", function() {
				extract_case_result('yes', 0);
			});
		} else {
			oTestFrame.onload = function() {
				extract_case_result('yes', 0);
			};
		}
	} catch (e) {
		print_error_log("execute_test_task", e);
	}
}

function calculate_block_check_time(onload_delay) {
	blockCheckTime = Math.ceil((Math.sqrt(onload_delay * 4 + 25) - 5) / 10);
}

function check_block_result_again(time) {
	sleep_time = time * 50;
	if (time == blockCheckTime) {
		setTimeout("extract_case_result('no', " + time + ")", sleep_time);
		return;
	}
	setTimeout("extract_case_result('yes', " + time + ")", sleep_time);
}

function extract_case_result(need_check_block, sleep_time) {
	oTestFrame = document.getElementById('testframe');
	var oTestWin = oTestFrame.contentWindow;
	var oTestDoc = oTestFrame.contentWindow.document;
	var result = "BLOCK";
	var case_msg = "";

	oPass = $(oTestDoc).find(".pass");
	oFail = $(oTestDoc).find(".fail");
	case_uri = current_page_uri;

	total_num = getTestPageParam(case_uri, "total_num");
	locator_key = getTestPageParam(case_uri, "locator_key");
	value = getTestPageParam(case_uri, "value");

	if (total_num != "" && locator_key != "" && value != "") {
		if (locator_key == "id") {
			var results;
			var passes;
			var fails;

			var oRes = $(oTestDoc).find("table#results");
			if (oRes) {
				results = $(oRes).find('tr');
				passes = $(oRes).find('tr.pass');
				fails = $(oRes).find('tr.fail');
			}
			if (passes.length + fails.length == total_num) {
				var i = 1;
				for (i = 1; i <= total_num; i++) {
					if (i.toString() != value) {
						continue;
					}
					var rest = results[i].childNodes[0].textContent;
					var desc = results[i].childNodes[1].textContent;
					case_msg = results[i].childNodes[2].textContent;

					if (rest && rest.toUpperCase() == "PASS") {
						result = "PASS";
					} else {
						result = "FAIL";
					}
					break;
				}
			} else {
				var i;
				for (i = 0; i < fails.length; i++) {
					var desccell = fails[i].childNodes[1];
					if (desccell) {
						case_msg += "###Test Start###" + desccell.innerText
								+ "###Test End###";
					}
					var msgcell = fails[i].childNodes[2];
					if (msgcell) {
						case_msg += "###Error1 Start###"
								+ msgcell.innerText + "###Error1 End###";
					}
				}
				result = "FAIL";
			}
		}
	} else if (oPass.length > 0 && oFail.length == 0) {
		if (oTestWin.resultdiv) {
			case_msg = oTestWin.resultdiv.innerHTML;
		}
		result = "PASS";
	} else if (oFail.length > 0) {
		var oRes = $($(oTestDoc).find("table#results")).get(0);
		// Get error log
		if (oRes) {
			var fails = $(oRes).find('tr.fail');
			var i;
			for (i = 0; i < fails.length; i++) {
				var desccell = fails[i].childNodes[1];
				if (desccell) {
					case_msg += "###Test Start###" + desccell.innerText
							+ "###Test End###";
				}
				var msgcell = fails[i].childNodes[2];
				if (msgcell) {
					case_msg += "###Error2 Start###" + msgcell.innerText
							+ "###Error2 End###";
				}
			}
		}
		result = "FAIL";
	} else {
		if (need_check_block == 'yes') {
			next_sleep_time = sleep_time + 1;
			check_block_result_again(next_sleep_time);
			return;
		}
	}
	var next_step = ask_next_step();
	commit_test_result(result, case_msg);
	if (next_step.step == "continue") {
		start_test();
	} else {
		print_error_log("memory collection process activated",
				"this window will be closed in 2sec");
		close_window();
		//setTimeout("window.open('','_self','');window.close()", 2000);
	}
}

var manual_test_step = function() {
	this.order = 0;
	this.desc = "";
	this.expected = "";
};

var manual_cases = function() {
	this.casesid = "";
	this.index = 0;
	this.result = "";
	this.entry = "";
	this.pre_con = "";
	this.post_con = "";
	this.purpose = "";
	this.steps = new Array();
};

function execute_manual_test() {
	manualcaseslist = new Array();
	tasks = extract_all_manual();
	if (tasks != null){
		for ( var i = 0; i < tasks.length; i++) {
			if (parent.document.getElementById("statusframe"))
				parent.document.getElementById("statusframe").height = 385 + "px";
			manualcaseslist[i] = new manual_cases();
			manualcaseslist[i].casesid = tasks[i].case_id;
			manualcaseslist[i].index = i;
			manualcaseslist[i].entry = tasks[i].entry;
			manualcaseslist[i].pre_con = tasks[i].pre_condition;
			manualcaseslist[i].post_con = tasks[i].post_condition;
			manualcaseslist[i].purpose = tasks[i].purpose;

			if (tasks[i].steps != undefined) {
				for ( var j = 0; j < tasks[i].steps.length; j++) {
					this_manual_step = new manual_test_step();
					this_manual_step.order = parseInt(tasks[i].steps[j].order);
					this_manual_step.desc = tasks[i].steps[j].step_desc;
					this_manual_step.expected = tasks[i].steps[j].expected;
					manualcaseslist[i].steps[this_manual_step.order - 1] = this_manual_step;
				}
			}
		}
		if (tasks.length > 0) {
			statusFrame.src = "./manual_harness.html";
			$($($('#main')).get(0)).attr('rows', "100,*");
		}
		oTestFrame = document.getElementById('testframe');
		oTestFrame.src = '';
	}
	else {
		// No manual cases, generate the result.
		ask_generate_xml();
	}
}

function commit_test_result(result, msg) {
	statusFrame = document.getElementById('statusframe');
	purposeNode = statusWin.document.getElementById('test_purpose_div');
	session_id = get_session_id();
	var purpose_str = purposeNode.innerHTML
	var server_url = server + "/commit_result";
	$.ajax({
		async : false,
		url : server_url,
		type : "POST",
		data : {
			"case_id" : case_id_str,
			"purpose" : purpose_str,
			"result" : result,
			"msg" : "[Message]" + msg,
			"session_id" : session_id
		},
		dataType : "json",
		beforeSend : function(x) {
			if (x && x.overrideMimeType) {
				x.overrideMimeType("application/j-son;charset=UTF-8");
			}
		},
		error : function(x, t, e) {
			print_error_log("commit_test_result", e);
		}
	});
}

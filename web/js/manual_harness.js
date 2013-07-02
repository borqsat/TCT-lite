var iTestsManual = 0;

function fillCasesInfo(){
    oTestFrame = window.parent.document.getElementById('testframe');
	oTestFrame.src = '';
	document.getElementById("caseslist").options[iTestsManual].selected=true;
	if(window.parent.manualcaseslist[iTestsManual].result == "PASS"){
		document.getElementById("passradio").checked=true;
        document.getElementById("passradio").tag=1;
		document.getElementById("failradio").checked=false;
        document.getElementById("failradio").tag=0;
        document.getElementById("blockradio").checked=false;
        document.getElementById("blockradio").tag=0;
	} else if(window.parent.manualcaseslist[iTestsManual].result == "FAIL"){
		document.getElementById("passradio").checked=false;
        document.getElementById("passradio").tag=0;
        document.getElementById("failradio").checked=true;
        document.getElementById("failradio").tag=1;
        document.getElementById("blockradio").checked=false;
        document.getElementById("blockradio").tag=0;
	} else if(window.parent.manualcaseslist[iTestsManual].result == "BLOCK"){
        document.getElementById("passradio").checked=false;
        document.getElementById("passradio").tag=0;
        document.getElementById("failradio").checked=false;
        document.getElementById("failradio").tag=0;
        document.getElementById("blockradio").checked=true;
        document.getElementById("blockradio").tag=1;
        }else {
		document.getElementById("passradio").checked=false;
        document.getElementById("passradio").tag=0;
        document.getElementById("failradio").checked=false;
        document.getElementById("failradio").tag=0;
        document.getElementById("blockradio").checked=false;
        document.getElementById("blockradio").tag=0;
	}

	var scriptPathText = window.parent.manualcaseslist[iTestsManual].entry;
	if(scriptPathText != undefined && scriptPathText.trim().length > 0){
		document.getElementById("runbutton").disabled = false;
	}else {
		document.getElementById("runbutton").disabled = true;
	}
	
	document.getElementById("casesinfo").value="";
    document.getElementById("casesinfo").value+="Descriptions: "+window.parent.manualcaseslist[iTestsManual].purpose +"\n";
    var preC = window.parent.manualcaseslist[iTestsManual].pre_con;
    if (preC && preC.length > 0){
        document.getElementById("casesinfo").value+= "PreCondition: "+preC+"\n";
    }

    var posC = window.parent.manualcaseslist[iTestsManual].post_con;
    if (posC && posC.length > 0){
        document.getElementById("casesinfo").value+= "PostCondition: "+posC+"\n";
    }

    var steps = window.parent.manualcaseslist[iTestsManual].steps;
    if(steps.length > 0){
        for(var i=0; i<steps.length; i++){
            document.getElementById("casesinfo").value+= "Step-"+steps[i].order+": "+steps[i].desc+"\n";
            document.getElementById("casesinfo").value+= "Expected"+": "+steps[i].expected+"\n";
        }
    }
}

function initManual(){
    alert("manu_harness");
    for(var i = 0; i < window.parent.manualcaseslist.length; i++){
        var id_temp = window.parent.manualcaseslist[i].casesid;
        if(id_temp.length > 32){
            var prefix = id_temp.substring(0,9);
            var postfix = id_temp.substring(15);
            var item = new Option(prefix + " ... " + postfix, window.parent.manualcaseslist[i].index);
        } else {
            var item = new Option(window.parent.manualcaseslist[i].casesid, window.parent.manualcaseslist[i].index);
        }
        document.getElementById("caseslist").options.add(item);
    }
	fillCasesInfo();
}

function runTest(){
	var scriptPathText = window.parent.manualcaseslist[iTestsManual].entry;
	if(scriptPathText){
		window.parent.document.getElementById('testframe').src = scriptPathText;
	}
}

function nextTest(){
	submitTest();
	iTestsManual++;
	if(iTestsManual >= window.parent.manualcaseslist.length)
		iTestsManual=0;
	fillCasesInfo();
}

function prevTest(){
	submitTest();
    iTestsManual--;
    if(iTestsManual < 0)
        iTestsManual = window.parent.manualcaseslist.length - 1;
	fillCasesInfo();
}

function submitTest(){
	var iResult="N/A";
	var optionsColor="white";
	if(document.getElementById("passradio").tag == 1){
		iResult="PASS";
		optionsColor="greenyellow";
	} else if(document.getElementById("failradio").tag == 1){
		iResult="FAIL";
		optionsColor="orangered";
	} else if(document.getElementById("blockradio").tag == 1){
        iResult="BLOCK";
        optionsColor="gray";
    }
	window.parent.manualcaseslist[iTestsManual].result = iResult;
	document.getElementById("caseslist").options[iTestsManual].style.backgroundColor = optionsColor;

	var server_url = "http://127.0.0.1:8000/commit_manual_result";
    jQuery.ajax({
        async: false,
        url: server_url,
        type: "POST",
        data: {"case_id": window.parent.manualcaseslist[iTestsManual].casesid,"purpose": window.parent.manualcaseslist[iTestsManual].purpose, "result": iResult},
        dataType: "json",
        beforeSend: function(x) {
            if (x && x.overrideMimeType) {
              x.overrideMimeType("application/json;charset=UTF-8");
            }
        },
        success: function(result) {
        }
    });
}

function completeTest(){
	window.parent.ask_generate_xml();
}

function passRadio()
{
	var radio = document.getElementById("passradio");
	if (radio.tag==1){
		radio.checked=false;
		radio.tag=0;
	}else{
		radio.checked=true;
		radio.tag=1;
		document.getElementById("failradio").checked=false;
        document.getElementById("failradio").tag=0;
        document.getElementById("blockradio").checked=false;
        document.getElementById("blockradio").tag=0;
	}
}

function failRadio()
{
    var radio = document.getElementById("failradio");
    if (radio.tag==1){
        radio.checked=false;
        radio.tag=0;
    }else{
        radio.checked=true;
        radio.tag=1;
        document.getElementById("passradio").checked=false;
        document.getElementById("passradio").tag=0;
        document.getElementById("blockradio").checked=false;
        document.getElementById("blockradio").tag=0;

    }
}

function blockRadio()
{
    var radio = document.getElementById("blockradio");
    if (radio.tag==1){
        radio.checked=false;
        radio.tag=0;
    }else{
        radio.checked=true;
        radio.tag=1;
        document.getElementById("passradio").checked=false;
        document.getElementById("passradio").tag=0;
        document.getElementById("failradio").checked=false;
        document.getElementById("failradio").tag=0;
    }
}

function listUpdate(){
	iTestsManual = document.getElementById("caseslist").selectedIndex;
	fillCasesInfo();
}

function passLabel(){
    var radio = document.getElementById("passradio");
    if (radio.tag==1){
        radio.checked=false;
        radio.tag=0;
    }else{
        radio.checked=true;
        radio.tag=1;
        document.getElementById("failradio").checked=false;
        document.getElementById("failradio").tag=0;
        document.getElementById("blockradio").checked=false;
        document.getElementById("blockradio").tag=0;
    }
}

function failLabel(){
	var radio = document.getElementById("failradio");
    if (radio.tag==1){
        radio.checked=false;
        radio.tag=0;
    }else{
        radio.checked=true;
        radio.tag=1;
        document.getElementById("passradio").checked=false;
        document.getElementById("passradio").tag=0;
        document.getElementById("blockradio").checked=false;
        document.getElementById("blockradio").tag=0;
    }
}

function blockLabel(){
    var radio = document.getElementById("blockradio");
    if (radio.tag==1){
        radio.checked=false;
        radio.tag=0;
    }else{
        radio.checked=true;
        radio.tag=1;
        document.getElementById("passradio").checked=false;
        document.getElementById("passradio").tag=0;
        document.getElementById("failradio").checked=false;
        document.getElementById("failradio").tag=0;
    }
}
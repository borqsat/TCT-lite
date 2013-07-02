var iTestsManual = 0;

function fillCasesInfo(){
	window.parent.oTestFrame.src = '';
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
    } else {
        document.getElementById("passradio").checked=false;
        document.getElementById("passradio").tag=0;
        document.getElementById("failradio").checked=false;
        document.getElementById("failradio").tag=0;
        document.getElementById("blockradio").checked=false;
        document.getElementById("blockradio").tag=0;
	}

	var scriptPathText = $(window.parent.Tests[window.parent.manualcaseslist[iTestsManual].index]).find('test_script_entry').get(0);
	if(scriptPathText){
		if($(scriptPathText).text().trim() == "")
			document.getElementById("runbutton").disabled = true;
		else
			document.getElementById("runbutton").disabled = false;
	}else {
		document.getElementById("runbutton").disabled = true;
	}
	
	document.getElementById("casesinfo").value="";
    document.getElementById("casesinfo").value+="Descriptions: "+$(window.parent.Tests[window.parent.manualcaseslist[iTestsManual].index]).attr('purpose')+"\n";
    var preC = $(window.parent.Tests[window.parent.manualcaseslist[iTestsManual].index]).find('pre_condition');
    if (preC && preC.length > 0){
        var preCText = $(window.parent.Tests[window.parent.manualcaseslist[iTestsManual].index]).find('pre_condition').get(0);
        document.getElementById("casesinfo").value+= "PreCondition: "+$(preCText).text().trim()+"\n";
    }

    var posC = $(window.parent.Tests[window.parent.manualcaseslist[iTestsManual].index]).find('post_condition');
    if (posC && posC.length > 0){
        var posCText = $(posC).get(0);
        document.getElementById("casesinfo").value+= "PostCondition: "+$(posCText).text().trim()+"\n";
    }
    var stepInfo = $(window.parent.Tests[window.parent.manualcaseslist[iTestsManual].index]).find('step_desc');
    var stepExp = $(window.parent.Tests[window.parent.manualcaseslist[iTestsManual].index]).find('expected');
    for(var j=0;j<stepInfo.length;j++){
		var stepsnum = j + 1;
		if(stepInfo){
        	var stepInfoText = $(stepInfo[j]).get(0);
        	document.getElementById("casesinfo").value+= "Step-"+stepsnum+": "+$(stepInfoText).text().trim()+"\n";
		}
		if(stepExp){
        	var stepExpText = $(stepExp[j]).get(0);
        	document.getElementById("casesinfo").value+= "Expected"+": "+$(stepExpText).text().trim()+"\n";
		}
    }
}

function initManual(){   
    alert("manuharness");  
    for(var i = 0; i < window.parent.manualcaseslist.length; i++){
        var id_temp = window.parent.manualcaseslist[i].casesid;
        if(window.parent.manualcaseslist[i].casesid.length > 32){
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
	var scriptPathText = $(window.parent.Tests[window.parent.manualcaseslist[iTestsManual].index]).find('test_script_entry').get(0);
	if(scriptPathText){
		window.parent.oTestFrame.src = $(scriptPathText).text().trim();
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
	if (window.parent.manualcaseslist[iTestsManual].index >= window.parent.Tests.length)
        return;
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

    $(window.parent.Tests[window.parent.manualcaseslist[iTestsManual].index]).attr('result', iResult);
	if($(window.parent.Tests[window.parent.manualcaseslist[iTestsManual].index]).find('result_info').length > 0)
		$(window.parent.Tests[window.parent.manualcaseslist[iTestsManual].index]).find('result_info').remove();

    	var doc=$.parseXML("<result_info>" + "<actual_result>" + iResult +"</actual_result>" + "<start>" + "</start>" + "<end>" + "</end>" + "<stdout>" + "</stdout>" + "</result_info>");
    	$(window.parent.Tests[window.parent.manualcaseslist[iTestsManual].index]).append(doc.documentElement);

//    	window.parent.statusNode.innerHTML =  "Test #" + (window.parent.manualcaseslist[iTestsManual].index+1) + "/" + window.parent.Tests.length + "(" + iResult + ") " + window.parent.oTestFrame.src;
}

function completeTest(){
	window.parent.PublishResult();
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
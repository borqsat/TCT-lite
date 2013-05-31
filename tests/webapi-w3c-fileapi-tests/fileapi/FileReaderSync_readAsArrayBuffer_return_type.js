/*
Copyright (c) 2012 Intel Corporation.

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met:

* Redistributions of works must retain the original copyright notice, this list 
  of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the original copyright notice, 
  this list of conditions and the following disclaimer in the documentation 
  and/or other materials provided with the distribution.
* Neither the name of Intel Corporation nor the names of its contributors 
  may be used to endorse or promote products derived from this work without 
  specific prior written permission.

THIS SOFTWARE IS PROVIDED BY INTEL CORPORATION "AS IS" 
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE 
ARE DISCLAIMED. IN NO EVENT SHALL INTEL CORPORATION BE LIABLE FOR ANY DIRECT, 
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, 
BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, 
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY 
OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING 
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, 
EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.  
  
Authors:
        Fan,Weiwei <weiwix.fan@intel.com>

*/
    var fileReaderSync = new FileReaderSync();
    if (!fileReaderSync) {
        postMessage("Fail to get FileReaderSync object");
    }
    if (!fileReaderSync.readAsArrayBuffer) {
        postMessage("The readAsArrayBuffer method is not exist");
    }
    try {
        //obtain a Blob object
        self.BlobBuilder = self.BlobBuilder || self.WebKitBlobBuilder || self.MozBlobBuilder || self.MSBlobBuilder;
        if (!self.BlobBuilder) {
            postMessage("The browser does not support BlobBuilder interface");
        }
        var builder = new self.BlobBuilder(); 
        builder.append("Hello world!");
        var blob = builder.getBlob("text/plain");
        if (!blob) {
            postMessage("Fail to obtain a Blob object");
        }
        var arraybuffer = fileReaderSync.readAsArrayBuffer(blob);
        if (arraybuffer && arraybuffer.toString() == "[object ArrayBuffer]") {
            postMessage("PASS");
        } else {
            postMessage("Fail to read the blob");
        }
    } catch (ex) {
        postMessage("Occur an exception " + ex);
    }

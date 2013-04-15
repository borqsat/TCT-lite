Summary: TCT-Lite
Name: testkit-lite
Version: 2.3.4
Release: 1
License: GPLv2
Group: Applications/System


%description
Testkit-LIte is a test runner with command-line interface.It has the following functions 
1. Accepts .xml test case descriptor files as input. 
2. drives automatic test execution. 
3. provide multiple options to meet various test requirements. 

%prep

%build


%install
sudo cp ${RPM_BUILD_ROOT}/usr/bin/testkit-lite /usr/bin/
sudo mkdir -p /opt/testkit/lite
sudo cp  ${RPM_BUILD_ROOT}/opt/testkit/lite/VERSION /opt/testkit/lite
sudo mkdir -p /usr/lib/python2.7/dist-packages/commodule
sudo mkdir -p /usr/lib/python2.7/dist-packages/testkitlite
sudo cp -r ${RPM_BUILD_ROOT}/usr/lib/python2.7/dist-packages/testkitlite/* /usr/lib/python2.7/dist-packages/testkitlite
sudo cp -r ${RPM_BUILD_ROOT}/usr/lib/python2.7/dist-packages/commodule/* /usr/lib/python2.7/dist-packages/commodule

%post
if [ `echo $(uname) | grep -c "^Linux"` -eq 1 ];then
	sudo chmod a+w /opt/testkit/lite
fi

%clean

%files
/usr/lib/python2.7/dist-packages/testkitlite/*
/usr/lib/python2.7/dist-packages/commodule/*
/opt/testkit/lite/VERSION
/usr/bin/testkit-lite
%defattr(-,root,root)

%doc
/opt/testkit/lite/testkit_lite_user_guide.pdf




%changelog

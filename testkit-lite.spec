Summary: TCT-Lite
Name: testkit-lite
Version: 2.3.4
Release: 1
License: GPLv2
Group: Applications/System
Source: %name-%version.tar.gz
BuildRoot: %_tmppath/%name-%version-buildroot

Requires(pre): python >= 2.7
Requires(pre): python-requests


%description
Testkit-LIte is a test runner with command-line interface.It has the following functions 
1. Accepts .xml test case descriptor files as input. 
2. drives automatic test execution. 
3. provide multiple options to meet various test requirements. 

%prep
%setup -q

%build
./autogen
./configure
make

%install
[ "\$RPM_BUILD_ROOT" != "/" ] && rm -rf "\$RPM_BUILD_ROOT"
make install DESTDIR=$RPM_BUILD_ROOT

%clean
[ "\$RPM_BUILD_ROOT" != "/" ] && rm -rf "\$RPM_BUILD_ROOT"

%files
/opt/testkit/lite
/usr/lib/python2.7/dist-packages/testkitlite
/usr/lib/python2.7/dist-packages/commodule
/opt/testkit/web
%attr(755,root,root)
/usr/bin/testkit-lite

%pre
if [ `echo $(uname) | grep -c "^Linux"` -eq 1 ];then
	if [ -f "/etc/sudoers" ];then
		if [ -f "/etc/login.defs" ];then
			#get first user name 
			min_uid=$(cat /etc/login.defs|grep -v '#'|awk '/UID_MIN/ {print $2;}')
			cur_user=$(cat /etc/passwd|grep -v '#'|awk -F: -v userid="${min_uid:=500}" '{ if ($3 == userid) print $1; }' /etc/passwd)
			if [ ${cur_user:="root"} != "root" ];then
				echo "Update sudoers configuration, it will take some mins"
				sed -i "/$cur_user/d" /etc/sudoers
				#append line into sudoers to configure switch to root without password
				sed -i "\$a$cur_user\tALL=(ALL)\tNOPASSWD: ALL" /etc/sudoers
			fi
		fi
	fi
fi

%post
if [ `echo $(uname) | grep -c "^Linux"` -eq 1 ];then
	chmod a+wx /opt/testkit/lite
	if [ ! -x /usr/bin/testkit-lite ];then
		find /usr -name 'testkit-lite' -exec cp -af {} /usr/bin/ \; 
	fi
fi

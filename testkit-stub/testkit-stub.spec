Summary: Testkit Stub
Name: testkit-stub
Version: 1.0
Release: 1
License: GPLv2
Group: Applications/System
Source: testkit-stub-1.0.tar.gz
#BuildRoot: %{_builddir}/%{name}-root

Requires: rpmlib(CompressedFileNames) <= 3.0.4-1
Requires: rpmlib(PayloadFilesHavePrefix) <= 4.0-1
Requires: rtld(GNU_HASH)

%description
Binary stub run on device. mainly a httpserver

%prep

%setup -q
%build
#make
%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT
cp -r * $RPM_BUILD_ROOT/
#make DESTDIR=$RPM_BUILD_ROOT/ install


%clean
rm -rf $RPM_BUILD_ROOT
%files
/*
%defattr(-,root,root)

%doc
#/usr/bin/httpserver
#/usr/lib/libjson-glib-1.0.so.0.1503.0
%changelog

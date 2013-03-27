
Name:       testkit-stub
Summary:    test
Version:    1.0
Release:    1
Group:      Development/Debug
License:    GPL v2 only
URL:        http://www.moblin.org/
Source0:    %{name}-%{version}.tar.gz
BuildRoot:  %{_tmppath}/%{name}-%{version}-build

%description
test


%prep
%setup -q -n %{name}-%{version}
# >> setup
# << setup

%build
# >> build pre
# << build pre


# Call make instruction with smp support
make %{?jobs:-j%jobs}

# >> build post
# << build post
%install
rm -rf %{buildroot}
# >> install pre
# << install pre
%make_install

# >> install post
# << install post

%clean
rm -rf %{buildroot}






%files
%defattr(-,root,root,-)
# >> files
%{_bindir}/httpserver
# << files


%changelog
* Tue Mar  21 2013 Li Min <min.a.li@intel.com> 0.10
- create for SLP build

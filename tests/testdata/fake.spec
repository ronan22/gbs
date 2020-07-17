Name:       fake
Summary:    A fake tizen package for gbs test
Version:    1.0
Release:    1
Group:      Development/Tools
License:    GPLv2
Source0:    %{name}-%{version}.tbz2

%description
A fake tizen package for gbs test
* download and install gbs
* use this package to test gbs build, remotebuild, export, import and so on
%prep
%setup -q

%install
mkdir -p %{buildroot}/%{_docdir}

%files
%doc README

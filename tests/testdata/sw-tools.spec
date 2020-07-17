%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
Name:		sw-tools
Version:	0.1
Release:	1
Summary:	Generate binary update packs

Group:		Development/Tools
License:	GPL V2
URL:		http://www.tizen.org
Source0:	%{name}-%{version}.tar.bz2
BuildRoot:	%{_tmppath}/%{name}-%{version}-%{release}-root

BuildRequires:	python-devel
Requires:	yum
Requires:	deltarpm
Requires:   python-deltarpm

%description
This is a tool to help genearting binary update packs

%prep
%setup -q -n %{name}-%{version}

%install
mkdir -p %{buildroot}/%{_docdir}

%files
%{_docdir}/

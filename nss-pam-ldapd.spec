%if 0%{?fedora} > 15 || 0%{?rhel} > 6
%global systemd 1
%global sysvinit 0
%else
%global systemd 0
%global sysvinit 1
%endif

# Fedora had these in F18, but we didn't cut over to use them until after F18
# was frozen, so pretend it didn't happen until F19.
%if 0%{?fedora} > 18 || 0%{?rhel} > 6
%global systemd_macros 1
%else
%global systemd_macros 0
%endif

%if 0%{?fedora} > 14 || 0%{?rhel} > 6
%global tmpfiles 1
%else
%global tmpfiles 0
%endif

# Fedora had it in F17, but moving things around in already-released versions
# is a bad idea, so pretend it didn't happen until F19.
%if 0%{?fedora} > 18 || 0%{?rhel} > 6
%global separate_usr 0
%global nssdir %{_libdir}
%global pamdir %{_libdir}/security
%else
%global separate_usr 1
%global nssdir /%{_lib}
%global pamdir /%{_lib}/security
%endif

# For distributions that support it, build with RELRO
%if (0%{?fedora} > 15 || 0%{?rhel} >= 7)
%define _hardened_build 1
%endif

Name:		nss-pam-ldapd
Version:	0.8.13
Release:	8%{?dist}
Summary:	An nsswitch module which uses directory servers
Group:		System Environment/Base
License:	LGPLv2+
URL:		http://arthurdejong.org/nss-pam-ldapd/
Source0:	http://arthurdejong.org/nss-pam-ldapd/nss-pam-ldapd-%{version}.tar.gz
Source1:	http://arthurdejong.org/nss-pam-ldapd/nss-pam-ldapd-%{version}.tar.gz.sig
Source2:	nslcd.init
Source3:	nslcd.tmpfiles
Source4:	nslcd.service
Patch1:		nss-pam-ldapd-0.8.12-validname.patch
Patch2:         nss-pam-ldapd-0.8.12-In-nslcd-log-EPIPE-only-on-debug-level.patch
Patch3:		nss-pam-ldapd-0.8.12-uid-overflow.patch
Patch4:		nss-pam-ldapd-0.8.12-Use-a-timeout-when-skipping-remaining-result-data.patch
Patch5:		nss-pam-ldapd-0.8.12-fix-buffer-overflow-on-interrupted-read-thanks-John-.patch
Patch6:		nss-pam-ldapd-rh-msgs-in-tests.patch
Patch7:         nss-pam-ldapd-0.8.13-Fix-use-after-free-in-read_hostent-and-read_netent.patch
Patch8:         nss-pam-ldapd-0.8.13-Use-right-h_errnop-for-retrying-with-larger-buffer.patch

BuildRoot:	%{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildRequires:	openldap-devel, krb5-devel
BuildRequires:	autoconf, automake
BuildRequires:	pam-devel
Obsoletes:	nss-ldapd < 0.7
Provides:	nss-ldapd = %{version}-%{release}

# Obsolete PADL's nss_ldap
Provides:       nss_ldap = 265-12
Obsoletes:      nss_ldap < 265-11

%if 0%{?fedora} > 18 || 0%{?rhel} > 6
# Obsolete PADL's pam_ldap
Provides:       pam_ldap = 185-15
Obsoletes:      pam_ldap < 185-15
%global         build_pam_ldap 1
%else
# Pull in the pam_ldap module, which is its own package in F14 and later, to
# keep upgrades from removing the module.  We used to disable nss-pam-ldapd's
# own pam_ldap.so when it wasn't mature enough.
Requires:       pam_ldap%{?_isa}
%global         build_pam_ldap 0
%endif

# Pull in nscd, which is recommended.
Requires:	nscd
%if %{sysvinit}
Requires(post):		/sbin/ldconfig, chkconfig, grep, sed
Requires(preun):	chkconfig, initscripts
Requires(postun):	/sbin/ldconfig, initscripts
%endif
%if %{systemd}
BuildRequires:	systemd-units
Requires(post):	systemd-units
Requires(preun):	systemd-units
Requires(postun):	systemd-units
Requires(post):	systemd-sysv
%endif

%description
The nss-pam-ldapd daemon, nslcd, uses a directory server to look up name
service information (users, groups, etc.) on behalf of a lightweight
nsswitch module.

%prep
%setup -q
%patch1 -p0 -b .validname
%patch2 -p1 -b .epipe
%patch3 -p1 -b .overflow
%patch4 -p1 -b .skiptimeout
%patch5 -p1 -b .readall
%patch6 -p1 -b .test_msgs
%patch7 -p1 -b .use_after_free
%patch8 -p1 -b .errnop_val
autoreconf -f -i

%build
CFLAGS="$RPM_OPT_FLAGS -fPIC" ; export CFLAGS
%configure --libdir=%{nssdir} \
%if %{build_pam_ldap}
	--with-pam-seclib-dir=%{pamdir}
%else
	--disable-pam
%endif
make %{?_smp_mflags}

%check
make check

%install
rm -rf $RPM_BUILD_ROOT
make install DESTDIR=$RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/{%{_initddir},%{_libdir},%{_unitdir}}
%if %{sysvinit}
install -p -m755 %{SOURCE2} $RPM_BUILD_ROOT/%{_initddir}/nslcd
%endif
%if %{systemd}
install -p -m644 %{SOURCE4} $RPM_BUILD_ROOT/%{_unitdir}/
%endif

%if 0%{?fedora} > 13 || 0%{?rhel} > 5
%if %{separate_usr}
# Follow glibc's convention and provide a .so symlink so that people who know
# what to expect can link directly with the module.
if test %{_libdir} != /%{_lib} ; then
	touch $RPM_BUILD_ROOT/rootfile
	relroot=..
	while ! test -r $RPM_BUILD_ROOT/%{_libdir}/$relroot/rootfile ; do
		relroot=../$relroot
	done
	ln -s $relroot/%{_lib}/libnss_ldap.so.2 \
		$RPM_BUILD_ROOT/%{_libdir}/libnss_ldap.so
	rm $RPM_BUILD_ROOT/rootfile
fi
%else
ln -s libnss_ldap.so.2 $RPM_BUILD_ROOT/%{nssdir}/libnss_ldap.so
%endif
%endif

sed -i -e 's,^uid.*,uid nslcd,g' -e 's,^gid.*,gid ldap,g' \
$RPM_BUILD_ROOT/%{_sysconfdir}/nslcd.conf
touch -r nslcd.conf $RPM_BUILD_ROOT/%{_sysconfdir}/nslcd.conf
mkdir -p -m 0755 $RPM_BUILD_ROOT/var/run/nslcd
%if %{tmpfiles}
mkdir -p -m 0755 $RPM_BUILD_ROOT/etc/tmpfiles.d
install -p -m 0644 %{SOURCE3} $RPM_BUILD_ROOT/etc/tmpfiles.d/%{name}.conf
%endif

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
%doc AUTHORS ChangeLog COPYING HACKING NEWS README TODO
%{_sbindir}/*
%{nssdir}/*.so.*
%if %{build_pam_ldap}
%{pamdir}/pam_ldap.so
%endif
%{_mandir}/*/*
%attr(0600,root,root) %config(noreplace) %verify(not md5 size mtime) /etc/nslcd.conf
%if %{tmpfiles}
%attr(0644,root,root) %config(noreplace) /etc/tmpfiles.d/%{name}.conf
%endif
%if %{sysvinit}
%attr(0755,root,root) %{_initddir}/nslcd
%endif
%if %{systemd}
%config(noreplace) %{_unitdir}/*
%endif
%attr(0755,nslcd,root) /var/run/nslcd
%if 0%{?fedora} > 13 || 0%{?rhel} > 5
# This would be the only thing in the -devel subpackage, so we include it.  It
# will conflict with nss_ldap, so only include it for releases where pam_ldap is
# its own package.
/%{_libdir}/*.so
%endif

%pre
getent group  ldap  > /dev/null || \
/usr/sbin/groupadd -r -g 55 ldap
getent passwd nslcd > /dev/null || \
/usr/sbin/useradd -r -g ldap -c 'LDAP Client User' \
    -u 65 -d / -s /sbin/nologin nslcd 2> /dev/null || :

%post
# The usual stuff.
%if %{sysvinit}
/sbin/chkconfig --add nslcd
%endif
%if %{systemd}
%if %{systemd_macros}
%systemd_post nslcd.service
%else
/bin/systemctl daemon-reload >/dev/null 2>&1 || :
%endif
%endif
/sbin/ldconfig
# Import important non-default settings from nss_ldap or pam_ldap configuration
# files, but only the first time this package is installed.
comment="This comment prevents repeated auto-migration of settings."
if test -s /etc/nss-ldapd.conf ; then
	source=/etc/nss-ldapd.conf
elif test -s /etc/nss_ldap.conf ; then
	source=/etc/nss_ldap.conf
elif test -s /etc/pam_ldap.conf ; then
	source=/etc/pam_ldap.conf
else
	source=/etc/ldap.conf
fi
target=/etc/nslcd.conf
if test "$1" -eq "1" && ! grep -q -F "# $comment" $target 2> /dev/null ; then
	# Try to make sure we only do this the first time.
	echo "# $comment" >> $target
	if grep -E -q '^uri[[:blank:]]' $source 2> /dev/null ; then
		# Comment out the packaged default host/uri and replace it...
		sed -i -r -e 's,^((host|uri)[[:blank:]].*),# \1,g' $target
		# ... with the uri.
		grep -E '^uri[[:blank:]]' $source >> $target
	elif grep -E -q '^host[[:blank:]]' $source 2> /dev/null ; then
		# Comment out the packaged default host/uri and replace it...
		sed -i -r -e 's,^((host|uri)[[:blank:]].*),# \1,g' $target
		# ... with the "host" reformatted as a URI.
		scheme=ldap
		# check for 'ssl on', which means we want to use ldaps://
		if grep -E -q '^ssl[[:blank:]]+on$' $source 2> /dev/null ; then
			scheme=ldaps
		fi
		grep -E '^host[[:blank:]]' $source |\
		sed -r -e "s,^host[[:blank:]](.*),uri ${scheme}://\1/,g" >> $target
	fi
	# Base doesn't require any special logic.
	if grep -E -q '^base[[:blank:]]' $source 2> /dev/null ; then
		# Comment out the packaged default base and replace it.
		sed -i -r -e 's,^(base[[:blank:]].*),# \1,g' $target
		grep -E '^base[[:blank:]]' $source >> $target
	fi
	# Pull in these settings, if they're set, directly.
	grep -E '^(binddn|bindpw|port|scope|ssl|pagesize)[[:blank:]]' $source 2> /dev/null >> $target
	grep -E '^(tls_)' $source 2> /dev/null >> $target
	grep -E '^(timelimit|bind_timelimit|idle_timelimit)[[:blank:]]' $source 2> /dev/null >> $target
fi
# If this is the first time we're being installed, and the system is already
# configured to use LDAP as a naming service, enable the daemon, but don't
# start it since we can never know if that's a safe thing to do.  If this
# is an upgrade, leave the user's runlevel selections alone.
if [ "$1" -eq "1" ]; then
	if grep -E -q '^USELDAP=yes$' /etc/sysconfig/authconfig 2> /dev/null ; then
%if %{sysvinit}
		/sbin/chkconfig nslcd on
%endif
%if %{systemd}
		/bin/systemctl --no-reload enable nslcd.service >/dev/null 2>&1 ||:
%endif
	fi
fi
# Earlier versions of 0.7.6 of this package would have included both 'gid
# nslcd' (a group which doesn't exist) and 'gid ldap' (which we ensure exists).
# If we detect both, fix the configuration.
if grep -q '^gid nslcd' $target ; then
	if grep -q '^gid ldap' $target ; then
		sed -i -e 's,^gid nslcd$,# gid nslcd,g' $target
	fi
fi
# In 0.8.4, the name of the attribute which was expected to contain the DNs of
# a group's members changed from "uniqueMember" to "member".  Change any
# instances of "map group uniqueMember ..." to "map group member ...", unless
# "member" is already being mapped, in which case attempting this would
# probably just confuse things further.
if grep -E -q "^[[:blank:]]*map[[:blank:]]+group[[:blank:]]+uniqueMember[[:blank:]]" $target ; then
	if ! grep -E -q "^[[:blank:]]*map[[:blank:]]+group[[:blank:]]+member[[:blank:]]" $target ; then
		sed -i -r -e "s,^[[:blank:]]*map[[:blank:]]+group[[:blank:]]+uniqueMember[[:blank:]](.*),map group member \1,g" $target
	fi
fi
# Create the daemon's /var/run directory if it isn't there.
if ! test -d /var/run/nslcd ; then
	mkdir -p -m 0755 /var/run/nslcd
fi
exit 0

%preun
if [ "$1" -eq "0" ]; then
%if %{sysvinit}
	/sbin/service nslcd stop >/dev/null 2>&1
	/sbin/chkconfig --del nslcd
%endif
%if %{systemd}
%if %{systemd_macros}
%systemd_preun nslcd.service
%else
	/bin/systemctl --no-reload disable nslcd.service > /dev/null 2>&1 || :
	/bin/systemctl stop nslcd.service > /dev/null 2>&1 || :
%endif
%endif
fi
exit 0

%postun
/sbin/ldconfig
%if %{sysvinit}
if [ "$1" -ge "1" ]; then
	/etc/rc.d/init.d/nslcd condrestart >/dev/null 2>&1
fi
%endif
%if %{systemd}
%if %{systemd_macros}
%systemd_postun_with_restart nslcd.service
%else
/bin/systemctl daemon-reload >/dev/null 2>&1 || :
if [ "$1" -ge "1" ]; then
	/bin/systemctl try-restart nslcd.service >/dev/null 2>&1
fi
%endif
%endif
exit 0

%if %{systemd}
%triggerun -- nss-pam-ldapd < 0.7.13-6
# Save the current service runlevel info, in case the user wants to apply
# the enabled status manually later, by running
#   "systemd-sysv-convert --apply nslcd".
%{_bindir}/systemd-sysv-convert --save nslcd >/dev/null 2>&1 ||:
# Do this because the old package's %%postun doesn't know we need to do it.
/sbin/chkconfig --del nslcd >/dev/null 2>&1 || :
# Do this because the old package's %%postun wouldn't have tried.
/bin/systemctl try-restart nslcd.service >/dev/null 2>&1 || :
exit 0
%endif

%changelog
* Wed Jan 29 2014 Jakub Hrozek <jhrozek@redhat.com>  0.8.13-8
- Fix a potential use-after-free in nsswitch module
- Resolves: rhbz#1036030 - New defect found in nss-pam-ldapd-0.8.13-4.el7

* Fri Jan 24 2014 Daniel Mach <dmach@redhat.com> - 0.8.13-7
- Mass rebuild 2014-01-24

* Mon Jan 20 2014 Jakub Hrozek <jhrozek@redhat.com>  0.8.13-6
- Change the error messages the tests expect to those printed on RH based
  systems
- Resolves: rhbz#1044482

* Fri Dec 27 2013 Daniel Mach <dmach@redhat.com> - 0.8.13-5
- Mass rebuild 2013-12-27

* Fri Oct 18 2013 Nalin Dahyabhai <nalin@redhat.com>  0.8.13-4
- compile nslcd/log.c with -fPIC instead of the current hardened-build default
  of -fPIE, which doesn't seem to avoid relocations for its thread-local
  variables on s390x (#1002834)

* Sat Oct 05 2013 Jakub Hrozek <jhrozek@redhat.com>  0.8.13-3
- Suppress Broken Pipe messages when requesting a large groupo
- Resolves: rhbz#1002829

* Wed Jul 31 2013 Jakub Hrozek <jhrozek@redhat.com>  0.8.13-2
- Build with _hardened_build macro

* Mon May  6 2013 Nalin Dahyabhai <nalin@redhat.com> 0.8.13-1
- update to 0.8.13
- correct a syntax error in the fix that was added for #832706

* Tue Apr 30 2013 Nalin Dahyabhai <nalin@redhat.com> 0.8.12-4
- in %%post, attempt to rewrite any instances of "map group uniqueMember ..."
  to be "map group member ..." in nslcd.conf, as the attribute name changed
  in 0.8.4 (via freeipa ticket #3589)

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.8.12-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Fri Jan 18 2013 Nalin Dahyabhai <nalin@redhat.com> 0.8.12-2
- drop local patch to make the client flush some more read buffers

* Fri Jan 18 2013 Nalin Dahyabhai <nalin@redhat.com> 0.8.12-1
- update to 0.8.12 (#846793)
- make building pam_ldap conditional on the targeted release
- add "After=named.service dirsrv.target slapd.service" to nslcd.service,
  to make sure that nslcd is started after them if they're to be started
  on the local system (#832706)
- alter the versioned Obsoletes: on pam_ldap to include the F18 package
- use %%{_unitdir} when deciding where to put systemd configuration, based
  on patch from Václav Pavlín (#850232)
- use new systemd macros for scriptlet hooks, when available, based on
  patch from Václav Pavlín (#850232)

* Sun Sep 09 2012 Jakub Hrozek <jhrozek@redhat.com> 0.7.17-1
- new upstream release 0.7.17

* Sun Aug 05 2012 Jakub Hrozek <jhrozek@redhat.com> - 0.7.16-5
- Obsolete PADL's nss_ldap

* Sat Aug 04 2012 Jakub Hrozek <jhrozek@redhat.com> - 0.7.16-4
- Build the PAM module, obsoletes PADL's pam-ldap (#856006)

* Fri Jul 20 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.7.16-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Mon May 14 2012 Jakub Hrozek <jhrozek@redhat.com> 0.7.16-2
- backport upstream revision r1659 related to broken pipe when
  requesting a large group
- use grep -E instead of egrep to avoid rpmlint warnings

* Sat Apr 28 2012 Jakub Hrozek <jhrozek@redhat.com> 0.7.16-1
- new upstream release 0.7.16

* Thu Mar 15 2012 Jakub Hrozek <jhrozek@redhat.com> 0.7.15-2
- Do not print "Broken Pipe" error message when requesting a large group

* Fri Mar 9 2012 Jakub Hrozek <jhrozek@redhat.com> 0.7.15-1
- new upstream release 0.7.15

* Fri Jan 13 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.7.14-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Fri Dec 16 2011 Jakub Hrozek <jhrozek@redhat.com> 0.7.14-2
- Do not overflow large UID/GID values on 32bit architectures

* Mon Nov 28 2011 Nalin Dahyabhai <nalin@redhat.com>
- use the same conditional test for deciding when to create the .so symlink as
  we do later on for deciding when to include it in the package (#757004)

* Fri Sep 23 2011 Jakub Hrozek <jhrozek@redhat.com> 0.7.14-1
- new upstream release 0.7.14
- obsoletes nss-pam-ldapd-0.7.x-buffers.patch

* Wed Aug 24 2011 Nalin Dahyabhai <nalin@redhat.com> 0.7.13-8
- include backported enhancement to take URIs in the form "dns:DOMAIN" in
  addition to the already-implemented "dns" (#730309)

* Thu Jul 14 2011 Nalin Dahyabhai <nalin@redhat.com> 0.7.13-7
- switch to only munging the contents of /etc/nslcd.conf on the very first
  install (#706454)
- make sure that we have enough space to parse any valid GID value when
  parsing a user's primary GID (#716822)
- backport support for the "validnames" option from SVN and use it to allow
  parentheses characters by modifying the default setting (#690870), then
  modify the default again to also allow shorter and shorter names to pass
  muster (#706860)

* Wed Jul 13 2011 Nalin Dahyabhai <nalin@redhat.com> 0.7.13-6
- convert to systemd-native startup (#716997)

* Mon Jun 13 2011 Nalin Dahyabhai <nalin@redhat.com> 0.7.13-5
- change the file path Requires: we have for pam_ldap into a package name
  Requires: (#601931)

* Wed Mar 30 2011 Nalin Dahyabhai <nalin@redhat.com> 0.7.13-4
- tag nslcd.conf with %%verify(not md5 size mtime), since we always tweak
  it in %%post (#692225)

* Tue Mar  1 2011 Nalin Dahyabhai <nalin@redhat.com> 0.7.13-3
- add a tmpfiles configuration to ensure that /var/run/nslcd is created when
  /var/run is completely empty at boot (#656643)

* Tue Feb 08 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.7.13-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Mon Dec 13 2010 Nalin Dahyabhai <nalin@redhat.com> 0.7.13-1
- update to 0.7.13

* Fri Oct 29 2010 Nalin Dahyabhai <nalin@redhat.com> 0.7.12-1
- update to 0.7.12

* Fri Oct 15 2010 Nalin Dahyabhai <nalin@redhat.com> 0.7.11-1
- update to 0.7.11

* Wed Sep 29 2010 jkeating - 0.7.10-2
- Rebuilt for gcc bug 634757

* Fri Sep 24 2010 Nalin Dahyabhai <nalin@redhat.com> 0.7.10-1
- update to 0.7.10

* Thu Sep 23 2010 Nalin Dahyabhai <nalin@redhat.com> 0.7.9-2
- when creating /var/run/nslcd in the buildroot, specify that 0755 is a
  permissions value and not another directory name (#636880)

* Mon Aug 30 2010 Nalin Dahyabhai <nalin@redhat.com> 0.7.9-1
- update to 0.7.9

* Wed Aug 18 2010 Nalin Dahyabhai <nalin@redhat.com> 0.7.8-1
- update to 0.7.8

* Wed Jul  7 2010 Nalin Dahyabhai <nalin@redhat.com> 0.7.7-1
- update to 0.7.7

* Mon Jun 28 2010 Nalin Dahyabhai <nalin@redhat.com> 0.7.6-3
- don't accidentally set multiple 'gid' settings in nslcd.conf, and try to
  clean up after older versions of this package that did (#608314)

* Thu May 27 2010 Nalin Dahyabhai <nalin@redhat.com> 0.7.6-2
- make inclusion of the .so symlink conditional on being on a sufficiently-
  new Fedora where pam_ldap isn't part of the nss_ldap package, so having
  this package conflict with nss_ldap doesn't require that pam_ldap be
  removed (#596691)

* Thu May 27 2010 Nalin Dahyabhai <nalin@redhat.com> 0.7.6-1
- update to 0.7.6

* Mon May 17 2010 Nalin Dahyabhai <nalin@redhat.com> 0.7.5-3
- switch to the upstream patch for #592411

* Fri May 14 2010 Nalin Dahyabhai <nalin@redhat.com> 0.7.5-2
- don't return an uninitialized buffer as the value for an optional attribute
  that isn't present in the directory server entry (#592411)

* Fri May 14 2010 Nalin Dahyabhai <nalin@redhat.com> 0.7.5-1
- update to 0.7.5

* Fri May 14 2010 Nalin Dahyabhai <nalin@redhat.com> 0.7.4-1
- update to 0.7.4
- stop trying to migrate retry timeout parameters from old ldap.conf files
- add an explicit requires: on nscd to make sure it's at least available on
  systems that are using nss-pam-ldapd; otherwise it's usually optional

* Tue Mar 23 2010 Nalin Dahyabhai <nalin@redhat.com> 0.7.3-1
- update to 0.7.3

* Thu Feb 25 2010 Nalin Dahyabhai <nalin@redhat.com> 0.7.2-2
- bump release for post-review commit

* Thu Feb 25 2010 Nalin Dahyabhai <nalin@redhat.com> 0.7.2-1
- add comments about why we have a .so link at all, and not a -devel subpackage

* Wed Jan 13 2010 Nalin Dahyabhai <nalin@redhat.com>
- obsolete/provides nss-ldapd
- import configuration from nss-ldapd.conf, too

* Tue Jan 12 2010 Nalin Dahyabhai <nalin@redhat.com>
- rename to nss-pam-ldapd
- also check for import settings in /etc/nss_ldap.conf and /etc/pam_ldap.conf

* Thu Sep 24 2009 Nalin Dahyabhai <nalin@redhat.com> 0.6.11-2
- rebuild

* Wed Sep 16 2009 Nalin Dahyabhai <nalin@redhat.com> 
- apply Mitchell Berger's patch to clean up the init script, use %%{_initddir},
  and correct the %%post so that it only thinks about turning on nslcd when
  we're first being installed (#522947)
- tell status() where the pidfile is when the init script is called for that

* Tue Sep  8 2009 Nalin Dahyabhai <nalin@redhat.com>
- fix typo in a comment, capitalize the full name for "LDAP Client User" (more
  from #516049)

* Wed Sep  2 2009 Nalin Dahyabhai <nalin@redhat.com> 0.6.11-1
- update to 0.6.11

* Sat Jul 25 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.6.10-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Thu Jun 18 2009 Nalin Dahyabhai <nalin@redhat.com> 0.6.10-3
- update URL: and Source:

* Mon Jun 15 2009 Nalin Dahyabhai <nalin@redhat.com> 0.6.10-2
- add and own /var/run/nslcd
- convert hosts to uri during migration

* Thu Jun 11 2009 Nalin Dahyabhai <nalin@redhat.com> 0.6.10-1
- update to 0.6.10

* Fri Apr 17 2009 Nalin Dahyabhai <nalin@redhat.com> 0.6.8-1
- bump release number to 1 (part of #491767)
- fix which group we check for during %%pre (part of #491767)

* Tue Mar 24 2009 Nalin Dahyabhai <nalin@redhat.com>
- require chkconfig by package rather than path (Jussi Lehtola, part of #491767)

* Mon Mar 23 2009 Nalin Dahyabhai <nalin@redhat.com> 0.6.8-0.1
- update to 0.6.8

* Mon Mar 23 2009 Nalin Dahyabhai <nalin@redhat.com> 0.6.7-0.1
- start using a dedicated user

* Wed Mar 18 2009 Nalin Dahyabhai <nalin@redhat.com> 0.6.7-0.0
- initial package (#445965)

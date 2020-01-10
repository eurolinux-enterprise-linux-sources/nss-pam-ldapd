Name:		nss-pam-ldapd
Version:	0.7.5
Release:	20%{?dist}.3
Summary:	An nsswitch module which uses directory servers
Group:		System Environment/Base
License:	LGPLv2+
URL:		http://arthurdejong.org/nss-pam-ldapd/
Source0:	http://arthurdejong.org/nss-pam-ldapd/nss-pam-ldapd-%{version}.tar.gz
Source1:	http://arthurdejong.org/nss-pam-ldapd/nss-pam-ldapd-%{version}.tar.gz.sig
Source2:	nslcd.init
Patch0:		nss-pam-ldapd-default.patch
Patch1:		nss-pam-ldapd-0.7.5-man.patch
Patch2:		nss-pam-ldapd-0.7.5-validname.patch
Patch3:		nss-pam-ldapd-0.7.5-socktimeouts.patch
Patch4:		nss-pam-ldapd-0.7.5-disconnect.patch
Patch5:		nss-pam-ldapd-0.7.x-buffers.patch
Patch6:		nss-pam-ldapd-0.7.x-dnssrv.patch
Patch7:         nss-pam-ldapd-0.7.5-uid-overflow.patch
Patch8:         nss-pam-ldapd-0.7.x-session-check.patch
Patch9:         nss-pam-ldapd-0.7.x-logic-typo.patch
Patch10:        nss-pam-ldapd-0.7.x-epipe.patch
Patch11:        nss-pam-ldapd-0.7.x-skipall.patch
Patch12:        nss-pam-ldapd-0.7.5-fdsize.patch
Patch13:        nss-pam-ldapd-0.7.x-skipnull.patch
Patch14:        nss-pam-ldapd-ssl-timeout.patch
Patch15:        nss-pam-ldapd-config-crash.patch
Patch16:        nss-pam-ldapd-static-cb-buf.patch

BuildRoot:	%{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildRequires:	openldap-devel, krb5-devel
BuildRequires:	autoconf, automake
Obsoletes:	nss-ldapd < 0.7
Provides:	nss-ldapd = %{version}-%{release}

# Pull in the pam_ldap module, which is currently bundled with nss_ldap, to
# keep upgrades from removing the module.  We currently disable nss-pam-ldapd's
# own pam_ldap.so until it's more mature.
Requires:	/%{_lib}/security/pam_ldap.so
# Pull in nscd, which is recommended.
Requires:	nscd
Requires(post):		/sbin/ldconfig, chkconfig, grep, sed
Requires(preun):	chkconfig, initscripts
Requires(postun):	/sbin/ldconfig, initscripts

%description
The nss-pam-ldapd daemon, nslcd, uses a directory server to look up name
service information (users, groups, etc.) on behalf of a lightweight
nsswitch module.

%prep
%setup -q
%patch0 -p0 -b .default
%patch1 -p1 -b .man
%patch2 -p0 -b .validname
%patch3 -p1 -b .socktimeouts
%patch4 -p1 -b .disconnect
%patch5 -p1 -b .buffers
%patch6 -p1 -b .dnssrv
%patch7 -p1 -b .biguid
%patch8 -p1 -b .session
%patch9 -p1 -b .logic_typo
%patch10 -p1 -b .epipe
%patch11 -p1 -b .skipall
%patch12 -p1 -b .fdset
%patch13 -p1 -b .skipnull
%patch14 -p1 -b .ssl
%patch15 -p1 -b .configcrash
%patch16 -p1 -b .cbstatic
autoreconf -f -i

%build
%configure --libdir=/%{_lib} --disable-pam
make %{?_smp_mflags}

%check
make check

%install
rm -rf $RPM_BUILD_ROOT
make install DESTDIR=$RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/{%{_initddir},%{_libdir}}
install -p -m755 %{SOURCE2} $RPM_BUILD_ROOT/%{_initddir}/nslcd
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
cat >> $RPM_BUILD_ROOT/%{_sysconfdir}/nslcd.conf << EOF
uid nslcd
gid ldap
EOF
touch -r nslcd.conf $RPM_BUILD_ROOT/%{_sysconfdir}/nslcd.conf
mkdir -p 0755 $RPM_BUILD_ROOT/var/run/nslcd

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
%doc AUTHORS ChangeLog COPYING HACKING NEWS README TODO
%{_sbindir}/*
/%{_lib}/*.so.*
%{_mandir}/*/*
%attr(0600,root,root) %config(noreplace) %verify(not md5 size mtime) /etc/nslcd.conf
%attr(0755,root,root) %{_initddir}/nslcd
%attr(0755,nslcd,root) /var/run/nslcd
# This would be the only thing in the -devel subpackage, so we include it.
/%{_libdir}/*.so

%pre
getent group  ldap  > /dev/null || \
/usr/sbin/groupadd -r -g 55 ldap
getent passwd nslcd > /dev/null || \
/usr/sbin/useradd -r -g ldap -c 'LDAP Client User' \
    -u 65 -d / -s /sbin/nologin nslcd 2> /dev/null || :

%post
# The usual stuff.
/sbin/chkconfig --add nslcd
/sbin/ldconfig
# Import important non-default settings from nss_ldap or pam_ldap configuration
# files, but only the first time this package is installed.
comment="This comment prevents repeated auto-migration of settings."
target=/etc/nslcd.conf
if test "$1" -eq "1" && ! grep -q -F "# $comment" $target 2> /dev/null ; then
        touch /var/run/nss-pam-ldapd.migrate
fi
# If this is the first time we're being installed, and the system is already
# configured to use LDAP as a naming service, enable the daemon, but don't
# start it since we can never know if that's a safe thing to do.  If this
# is an upgrade, leave the user's runlevel selections alone.
if [ "$1" -eq "1" ]; then
	if egrep -q '^USELDAP=yes$' /etc/sysconfig/authconfig 2> /dev/null ; then
		/sbin/chkconfig nslcd on
	fi
fi
exit 0

%preun
if [ "$1" -eq "0" ]; then
	/sbin/service nslcd stop >/dev/null 2>&1
	/sbin/chkconfig --del nslcd
fi
exit 0

%postun
/sbin/ldconfig
if [ "$1" -ge "1" ]; then
	/etc/rc.d/init.d/nslcd condrestart >/dev/null 2>&1
fi
exit 0

%posttrans
target=/etc/nslcd.conf
comment="This comment prevents repeated auto-migration of settings."

if test -f /var/run/nss-pam-ldapd.migrate; then
    rm -f /var/run/nss-pam-ldapd.migrate

    if test -s /etc/nss-ldapd.conf ; then
            source=/etc/nss-ldapd.conf
    elif test -s /etc/nss_ldap.conf ; then
            source=/etc/nss_ldap.conf
    elif test -s /etc/pam_ldap.conf ; then
            source=/etc/pam_ldap.conf
    else
            source=/etc/ldap.conf
    fi

    # Try to make sure we only do this the first time.
    echo "# $comment" >> $target
    if egrep -q '^uri[[:blank:]]' $source 2> /dev/null ; then
            # Comment out the packaged default host/uri and replace it...
            sed -i -r -e 's,^((host|uri)[[:blank:]].*),# \1,g' $target
            # ... with the uri.
            egrep '^uri[[:blank:]]' $source >> $target
    elif egrep -q '^host[[:blank:]]' $source 2> /dev/null ; then
            # Comment out the packaged default host/uri and replace it...
            sed -i -r -e 's,^((host|uri)[[:blank:]].*),# \1,g' $target
            # ... with the "host" reformatted as a URI.
            scheme=ldap
            # check for 'ssl on', which means we want to use ldaps://
            if egrep -q '^ssl[[:blank:]]+on$' $source 2> /dev/null ; then
                    scheme=ldaps
            fi
            egrep '^host[[:blank:]]' $source |\
            sed -r -e "s,^host[[:blank:]](.*),uri ${scheme}://\1/,g" >> $target
    fi
    # Base doesn't require any special logic.
    if egrep -q '^base[[:blank:]]' $source 2> /dev/null ; then
            # Comment out the packaged default base and replace it.
            sed -i -r -e 's,^(base[[:blank:]].*),# \1,g' $target
            egrep '^base[[:blank:]]' $source >> $target
    fi
    # Pull in these settings, if they're set, directly.
    egrep '^(binddn|bindpw|port|scope|ssl|pagesize)[[:blank:]]' $source 2> /dev/null >> $target || :
    egrep '^(tls_)' $source 2> /dev/null >> $target || :
    egrep '^(timelimit|bind_timelimit|idle_timelimit)[[:blank:]]' $source 2> /dev/null >> $target || :
fi

%changelog
* Wed Jan 28 2015 Jakub Hrozek <jhrozek@redhat.com> 0.7.5-20.3
- Use a static buffer for OpenLDAP callback structure
- Resolves: rhbz#999472 - nslcd does not reconnect to alternate ldap server
                          when using SSL

* Wed Jan 28 2015 Jakub Hrozek <jhrozek@redhat.com> 0.7.5-20.2
- Do not crash when parsing the tls_ciphers option
- Resolves: rhbz#1184361 - segfault occurs when nslcd starts 

* Wed Jan 28 2015 Jakub Hrozek <jhrozek@redhat.com> 0.7.5-20.1
- Resolves: rhbz#1192451 - nslcd does not reconnect to alternate ldap server
                           when using SSL

* Mon Jul 22 2013  Jakub Hrozek <jhrozek@redhat.com> 0.7.5-20
- Apply a patch by Martin Poole to fix skipping a zero-length attribute
- Resolves: #958364

* Tue Feb 19 2013  Jakub Hrozek <jhrozek@redhat.com> 0.7.5-19
- Apply upstream r1926 to resolve FD_SET array index error
- Resolves: rhbz#915362

* Mon Nov 26 2012  Jakub Hrozek <jhrozek@redhat.com> 0.7.5-18
- Correct the patch to silent a warning after retrieving a large group
- Resolves: #791042

* Tue Oct  9 2012  Jakub Hrozek <jhrozek@redhat.com> 0.7.5-17
- include LDAP_ADMINLIMIT_EXCEEDED in the disconnection logic patch
- Related: rhbz#747281

* Tue Oct  9 2012  Jakub Hrozek <jhrozek@redhat.com> 0.7.5-16
- Do not print a "Broken Pipe" error message after requesting a large group
  (#791042)
- Fix a typo in the disconnection logic (#747281), patch by Martin Poole

* Tue Dec  20 2011 Jakub Hrozek <jhrozek@redhat.com> 0.7.5-15
- Do not check connection before adding a new search (#769289)

* Tue Oct  18 2011 Jakub Hrozek <jhrozek@redhat.com> 0.7.5-14
- run the config file upgrade in %posttrans to avoid problems on multilib
  (#706454)
- convert UID to long long on all arches to catch negative values (#741362)

* Tue Oct  18 2011 Jakub Hrozek <jhrozek@redhat.com> 0.7.5-13
- punt on negative UID/GID (#741362)

* Tue Oct  4 2011 Jakub Hrozek <jhrozek@redhat.com> 0.7.5-12
- patch the nslcd.conf manual page with the "dns:DOMAIN" syntax info (#730309)

* Tue Oct  4 2011 Jakub Hrozek <jhrozek@redhat.com> 0.7.5-11
- do not overflow big UID values, use explicit base when converting UIDs
  and GIDs to integer types (#741362)

* Mon Sep 12 2011 Nalin Dahyabhai <nalin@redhat.com> 0.7.5-10
- update the validnames changes to the self-tests so that their expectations
  match the modified defaults (#737496)

* Wed Aug 24 2011 Nalin Dahyabhai <nalin@redhat.com> 0.7.5-9
- include backported enhancement to take URIs in the form "dns:DOMAIN" in
  addition to the already-implemented "dns" (#730309)

* Thu Jul 14 2011 Nalin Dahyabhai <nalin@redhat.com> 0.7.5-8
- switch to only munging the contents of /etc/nslcd.conf on the very first
  install (#706454)
- make sure that we have enough space to parse any valid GID value when
  parsing a user's primary GID (#716822,#720230)
- tweak the default "validnames" setting to also allow shorter and shorter
  names to pass muster (#706860)

* Tue Apr  5 2011 Nalin Dahyabhai <nalin@redhat.com> 0.7.5-7
- tag nslcd.conf with %%verify(not md5 size mtime), since we always tweak
  it in %%post (#692225)

* Fri Apr  1 2011 Nalin Dahyabhai <nalin@redhat.com> 0.7.5-6
- backport patches from 0.7.10 to interpret more types of errors as indicators
  that we need to ask a different server (#692817) and from 0.7.12 to not
  get stuck while cleaning up SSL/TLS encrypted connections

* Tue Mar 29 2011 Nalin Dahyabhai <nalin@redhat.com> 0.7.5-5
- backport support for the "validnames" option from SVN and use it to allow
  parentheses characters by modifying the default setting (#690870)

* Fri Mar 18 2011 Nalin Dahyabhai <nalin@redhat.com> 0.7.5-4
- tweak the pre-generated man pages to avoid a syntax error warning with older
  versions of groff (#676483)

* Mon May 17 2010 Nalin Dahyabhai <nalin@redhat.com> 0.7.5-3
- switch to the upstream patch for #592965

* Fri May 14 2010 Nalin Dahyabhai <nalin@redhat.com> 0.7.5-2
- don't return an uninitialized buffer as the value for an optional attribute
  that isn't present in the directory server entry (#592965)

* Fri May 14 2010 Nalin Dahyabhai <nalin@redhat.com> 0.7.5-1
- update to 0.7.5

* Fri May 14 2010 Nalin Dahyabhai <nalin@redhat.com> 0.7.4-1
- update to 0.7.4 (#592385)
- stop trying to migrate retry timeout parameters from old ldap.conf files
- add an explicit requires: on nscd to make sure it's at least available
  on systems that are using nss-pam-ldapd; otherwise it's usually optional
  (#587306)

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

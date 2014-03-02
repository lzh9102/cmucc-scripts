#!/usr/bin/perl

# bucy 20030315
# more small fixes
# usage: ./NewAcct.pl
# (user file on stdin)
# format : username:passwd:full name:mail addr

# bucy 20030222
# cleaned out completely obselete junk (archive copy NewAcct.pl.archive)

# updated bucy 20021122
# now takes user list on stdin (more convenient for debugging)
# defaults expiration date to 2 years from today
# (if you want to change it, do it by hand with kadmin later;
#  kadmin uses a non-obvious date format)
# Usage: ./NewAcct.pl   (with userlist file on stdin)
# userlist file:  user:passwd:realname:mailaddr
# mail addr not currently used.  should probably start sending mail again.


# NewAcct.pl
# Create new computer-club accounts
# This creates new computer-club accounts for a bunch of users.
# The user information is read from a file specified on the command line.
# Usage: NewAcct.pl <expire-date> <user-file>
# last updated: rbraun 8/3/2002


# AFS-related constants
$cell="club.cc.cmu.edu";
$usrvol="club.usr";
$ctr = 0;
# for cheezy load balancing
# really want a club-wide place to get this info
@sites = ( # "copper.club.cc.cmu.edu vicepa",
	  "zinc.club.cc.cmu.edu vicepa");

$mountpt = "/afs/.club.cc.cmu.edu/usr";
$homedir = "/afs/club.cc.cmu.edu/usr";
#$admin = $ARGV[0];
#$expire = $ARGV[0];
$usergroup = 20;

#default quota
$quota = 300000;
$mquota = 100000;
$PasswdDotUser = "/afs/club.cc.cmu.edu/service/etc/passwd.user";

$mailtabsdir = "/afs/club.cc.cmu.edu/service/mail/mailtabs";

# Other constants
$mydir="/afs/club.cc.cmu.edu/system/scripts/perl";
$mailer = "/usr/sbin/sendmail -iU";
$subj = "Computer Club account created";

# Open files...
open(LETTER, "/afs/club/admin/accounts/Letters/NewAccount.new");

$|=1;



# lots of sanity checking per aarons permissions-clobbering incident
# validate a username .. returns 0 if username bad, 1 if ok
sub usernameOK {

    if(length($_[0]) > 8) {
	print "*** error: username too long: $_\n";
	return 0;
    }

    if(! ($_[0] =~ /[A-Za-z0-9_]+/)) {
	print "*** error: bad chars in username: $_[0]\n";
	return 0;
    } 
    
    # could be more aggressive -- check passwd and krb as well
    # heimdal-- again .. kadmin exits 0 for get whether or not
    # the user exists...
    system("pts ex $_[0]");
    if(($? >> 8) == 0) {
	print "*** error: user already exists\n";
	return 0;
    }

    return 1;
}


# use STDIN (bucy)
# open(USERS,$ARGV[0]) || die("couldn't open $ARGV[0]\n");

print "Getting you kadmin-specific tickets...\n";
if (system("kinit -S kadmin/admin"))
{
	die "spell your password right!\n";
}

print "Checking PATH and permissions:\n";

print "fs in PATH: ";
unless (system("which fs >/dev/null"))
{
	print "OK\n";
}
else
{
	die "not found.\n";
}

print "vos in PATH: ";
unless (system("which vos >/dev/null"))
{
	print "OK\n";
}
else
{
	die "not found.\n";
}

print "pts in PATH: ";
unless (system("which pts >/dev/null"))
{
	print "OK\n";
}
else
{
	die "not found.\n";
}

print "kadmin in PATH: ";
unless (system("which kadmin >/dev/null"))
{
	print "OK\n";
}
else
{
	die "not found.\n";
}

print "kadmin has perms: ";
unless (system('(setsid kadmin get admin@CLUB.CC.CMU.EDU < /dev/null) > /dev/null 2>&1'))
{
	print "OK\n";
}
else
{
	die "no.\n";
}

print "AFS admin permissions 1: ";
unless (system("touch $PasswdDotUser >/dev/null 2>/dev/null"))
{
	print "OK\n";
}
else
{
	die "no.\n";
}

print "AFS admin permissions 2 (may take a moment): ";
unless (system("vos release root.cell >/dev/null 2>/dev/null"))
{
	print "OK\n";
}
else
{
	die "no.\n";
}

# Process users
while(<STDIN>)
{
    # switch to the next volume site
    $site = $sites[$ctr]; $ctr++; $ctr = $ctr % (@sites);

    # Read the user entry and print a useful message
    chomp;

    # user:passwd:realname:mailaddr
    @U=split(":");  
    print "*** Processing user ", $U[0], "($U[2]) ...\n";

    if(@U != 4) {
	print "*** error: bogus input line $_\n";
	next;
    }

    if(usernameOK($U[0])) {
	print "alright ... user ok\n";
	# debug
    }
    else { next; }
    
    # debug
#    next;
    
    # Create the user's Kerberos principal
    print "Creating kerberos user...\n";

    @daysm = ( 0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 );

    ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime(time);
    $year += 1900; 
    $year += 2; # expire after 2 years by default
    $mday++;    # (counts from 0)
    $mon++;	# also counts from 0
    if ($mday > $daysm[$mon]) { # end of month when aarons creates accts
    	$mday = 1;
	if ($mon == 12) { $mon = 1; $year++; } else { $mon++ }
    }
    $expiration = join("-", ($year,$mon,$mday));
    
    (! system "kadmin add -r --expiration-time=\"$expiration\" --max-ticket-life=\"25 hours\" --max-renewable-life=unlimited --pw-expiration-time=never --attributes='' $U[0]") || die("kadmin add failed!");
    system "kadmin passwd -p $U[1] $U[0]";
    system "kadmin get $U[0]";

    (! system "kadmin add -r --expiration-time=\"$expiration\" --max-ticket-life='10 minutes' --max-renewable-life='10 minutes' --pw-expiration-time=never --attributes='' $U[0]/mail") || die("kadmin add failed! (mail)");
    system "kadmin get $U[0]/mail";

    # Create the user's PTS id
    print "Creating PTS id...\n";
    (!system "pts createuser $U[0] -c club.cc.cmu.edu")
	|| die("pts createu failed!");
    open(PTSCMD, "pts examine $U[0] 2>&1 |")
	|| die("pts examine failed!");

    while(<PTSCMD>) {
	print "$_";
	if(/.*id:\s+([0-9]+).*/) {
	    $ptsid = $1;
	    print ("*** PTSID is $ptsid\n");
	    last;
	}
    }
    close(PTSCMD);

    (!system "pts createuser $U[0].mail -c club.cc.cmu.edu")
      || die("pts createu failed! (mail)");
    system "pts examine $U[0].mail ";

    # Create the AFS volume and the mount points
    print "Creating AFS volume...\n";
    $uname = $U[0];
    system("vos create $site user.$uname -cell $cell -v")
	&& die("vos create failed!");

    (!system "fs mkm $mountpt\/$uname user.$uname -cell $cell")
	|| die("fs mkm failed!");
    (!system "fs mkm $mountpt\/$uname\/OldFiles user.$uname.backup -cell $cell")
	|| die("fs mkm OldFiles failed!");

    (!system "vos release $usrvol -cell $cell -verbose")
      || print("vos release $usrvol failed!");

    # Create the mail volume and the mount points
    print "Creating AFS mail volume...\n";
    $uname = $U[0];
    system("vos create $site mail.$uname -cell $cell -v")
      && die("vos create failed! (maildir)");

    (!system "fs mkm $mountpt\/$uname\/Maildir mail.$uname -cell $cell")
      || die ("fs mkm failed! (maildir)");
    (!system "fs mkm $mountpt\/$uname\/Maildir\/OldFiles mail.$uname.backup -cell $cell")
      || die("fs mkm OldFiles failed! (maildir)");

    system "fs checkv";

    # Set up the maildir (maildirmake won't do this for an existing 
    # mountpoint...)
    mkdir("$homedir\/$uname\/Maildir/cur");
    mkdir("$homedir\/$uname\/Maildir/new");
    mkdir("$homedir\/$uname\/Maildir/tmp");

    # We explicitly chown and chmod these because qmail is paranoid
    system("chown", "$ptsid:$usergroup", "$homedir/$uname");
    system("chmod", "0755", "$homedir/$uname");
    system("chown", "$ptsid:$usergroup", "$homedir/$uname/Maildir");
    system("chmod", "0755", "$homedir/$uname/Maildir");
    system("chown", "$ptsid:$usergroup", "$homedir/$uname/Maildir/cur");
    system("chmod", "0755", "$homedir/$uname/Maildir/cur");
    system("chown", "$ptsid:$usergroup", "$homedir/$uname/Maildir/new");
    system("chmod", "0755", "$homedir/$uname/Maildir/new");
    system("chown", "$ptsid:$usergroup", "$homedir/$uname/Maildir/tmp");
    system("chmod", "0755", "$homedir/$uname/Maildir/tmp");

    # Update permissions
    print "Updating permissions...\n";
    open(FOUND, "find $homedir/$uname -type d -print |tac |");
    while(<FOUND>) {
        chomp;
        system "fs sa $_ $uname all -clear";
    }
    close(FOUND);

    # used to do a default .qmail file here

    # We explicitly chown and chmod these because qmail is paranoid 
    system("chown", "$ptsid:$usergroup", "$homedir/$uname");
    system("chmod", "0755", "$homedir/$uname");

    (!system("fs sa $homedir\/$uname $uname all system:anyuser l -clear"))
	|| die("fs sa failed!");

    (!system("fs setquota $homedir\/$uname $quota"))
	|| die("fs sq failed!");

    # mail principal needs r on homedir to read .qmail*
    # bucy 200303
    (!system("fs sa $homedir\/$uname ${uname}.mail rl"))
      || die("fs sa failed! (maildir)");

    (!system("fs sa $homedir\/$uname\/Maildir ${uname}.mail rlidwk"))
      || die("fs sa failed! (maildir)");

    foreach $i ("cur", "new", "tmp") {
	(!system("fs sa $homedir\/$uname\/Maildir/$i $uname all ${uname}.mail rlidwk -clear"))
	    || die("fs sa failed! (maildir)");
    }
    
    (!system("fs sq $homedir\/$uname\/Maildir $mquota"))
      || die("fs sq failed!");

    # Create the AFS backup volumes
    print "Creating backup...\n";
    (!system("vos backup user.$uname -cell $cell"))
	|| die("vos backup failed!");

    (!system("vos backup mail.$uname -cell $cell"))
	|| die("vos backup failed! (maildir)");

    # add the entry to passwd.user
    open(PASSWDUSER, ">>$PasswdDotUser")
	|| die("couldn't open $PasswdDotUser");
    print PASSWDUSER "$uname:K:$ptsid:$usergroup:$U[2]:$homedir/$uname:/bin/bash\n";
    close(PASSWDUSER);

	# extract mail keytab
	(!system("kadmin ext -k $mailtabsdir/$uname $uname/mail")) || die("kadmin ext for mailtab failed!");
	(!system("chown $ptsid $mailtabsdir/$uname")) || die("chown for mailtab failed!");
	(!system("chmod u-w $mailtabsdir/$uname")) || die("chmod for mailtab failed!");


    # Send out mail
#    print "Sending mail to $U[3]\n";
#    seek(LETTER,0,0);
#    open(SEND,"|$mailer $U[3]");
#    print SEND "From: CMUCC Accounts <gripe\@club.cc.cmu.edu>\n";
#    print SEND "Reply-To: gripe\@club.cc.cmu.edu\n";
#    print SEND "Subject: $subj\n\n";
#    while(<LETTER>)
#    {
#	s/%EXPR%/$expire/;
#	s/%USER%/$uname/;
#	s/%PASS%/$U[1]/;
#	print SEND;
#    }
#    print SEND "\n";
#    close(SEND);
}

close(USERS);
close(LETTER);


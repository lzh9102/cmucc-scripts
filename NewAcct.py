#!/usr/bin/env python

# chehuail 20130302
# translated into python script

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

import sys
import re
import os
import subprocess
from datetime import datetime

# AFS-related constants
cell = "club.cc.cmu.edu"
usrvol = "club.usr"
ctr = 0
# for cheezy load balancing
# really want a club-wide place to get this info
sites = [
    # "copper.club.cc.cmu.edu vicepa",
    "zinc.club.cc.cmu.edu vicepa",
]

mountpt = "/afs/.club.cc.cmu.edu/usr"
homedir = "/afs/club.cc.cmu.edu/usr"
# argv[0] is python is the script name
#admin = sys.argv[1]
#expire = sys.argv[1]
usergroup = 20

#default quota
quota = 300000
mquota = 100000
PasswdDotUser = "/afs/club.cc.cmu.edu/service/etc/passwd.user"

mailtabsdir = "/afs/club.cc.cmu.edu/service/mail/mailtabs"

# Other constants
mydir="/afs/club.cc.cmu.edu/system/scripts/perl"
mailer = "/usr/sbin/sendmail -iU"
subj = "Computer Club account created"

# Open files...
letterFile = open("/afs/club/admin/accounts/Letters/NewAccount.new", "r")

# TODO: unbuffered output

def die(message):
    print message
    sys.exit(1)

# lots of sanity checking per aarons permissions-clobbering incident
# validate a username .. returns 0 if username bad, 1 if ok
def usernameOK(username):

    if len(username) > 8:
        print "*** error: username too long: %s" % (username)
        return 0

    # username should only contain letters, numbers and underscore
    if not re.match(r"^[A-Za-z0-9_]+$", username):
        print "*** error: bad chars in username: %s" % (username)
        return 0

    # could be more aggressive -- check passwd and krb as well
    # heimdal-- again .. kadmin exits 0 for get whether or not
    # the user exists...
    status = os.system("pts ex %s" % (username))
    if (status >> 8) == 0:
        print "*** error: user already exists"
        return 0

    return 1

# TODO: translate the following two lines
# use STDIN (bucy)
# open(usersFile,$ARGV[0]) || die("couldn't open $ARGV[0]\n");

print "Getting you kadmin-specific tickets..."
if os.system("kinit -S kadmin/admin") != 0:
    die("spell your password right!")

print "Checking PATH and permissions:"

sys.stdout.write("fs in PATH: ")
if os.system("which fs > /dev/null 2>&1") == 0:
    print "OK"
else:
    die("not found")

sys.stdout.write("vos in PATH: ")
if os.system("which vos > /dev/null 2>&1") == 0:
    print "OK"
else:
    die("not found.")

sys.stdout.write("pts in PATH: ")
if os.system("which pts > /dev/null 2>&1") == 0:
    print "OK";
else:
    die("not found.")

sys.stdout.write("kadmin in PATH: ")
if os.system("which kadmin > dev/null 2>&1") == 0:
    print "OK"
else:
    die("not found.")

sys.stdout.write("kadmin has perms: ")
if os.system("setsid kadmin get admin@CLUB.CC.CMU.EDU > /dev/null 2>&1") == 0:
    print "OK"
else:
    die("no.")

sys.stdout.write("AFS admin permissions 1: ")
if os.system("touch %s >/dev/null 2>/dev/null" % (PasswdDotUser)) == 0:
    print "OK"
else:
    die("no.")

sys.stdout.write("AFS admin permissions 2 (may take a moment): ")
if os.system("vos release root.cell >/dev/null 2>/dev/null") == 0:
    print "OK"
else:
    die("no.")

# Process users
for line in sys.stdin:
    line = line.strip("\n") # remove trailing newline

    # switch to the next volume site
    site = sites[ctr]
    ctr = (ctr + 1) % (len(sites))

    # Read the user entry and print a useful message

    # user:passwd:realname:mailaddr
    fields = line.split(":")
    print "*** Processing user %s(%s) ..." % (fields[0], fields[1])

    if len(fields) != 4:
        print "*** error: bogus input line $s" % line
        continue

    if usernameOK(fields[0]):
        print "alright ... user ok"
        # debug
    else:
        continue

    # debug
    #continue

    # Create the user's Kerberos principal
    print "Creating kerberos user..."

    daysm = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    tm = datetime.now()
    (year, mon, mday) = (tm.year, tm.month, tm.day)
    (hour, min, sec) = (tm.hour, tm.minute, tm.second)
    # ignore (wday, yday, isdst) because they are not used
    year += 2; # expire after 2 years by default
    if mday > daysm[mon]: # end of month when aarons creates accts
        mday = 1
        if mon == 12:
            mon = 1
            year += 1
        else:
            mon += 1
            expiration = "%d-%d-%d" % (year, mon, mday);

    os.system("kadmin add -r --expiration-time=\"" + expiration + "\" " +
              "--max-ticket-life=\"25 hours\" " +
              "--max-renewable-life=unlimited --pw-expiration-time=never " +
              "--attributes='' " + fields[0]) == 0 or die("kadmin add failed!")
    os.system("kadmin passwd -p %(pw)s %(user)s" %
              {"user": fields[0], "pw": fields[1]})
    os.system("kadmin get %1s" % (fields[0]))

    if os.system("kadmin add -r --expiration-time=\"" + expiration + "\" " +
                 "--max-ticket-life='10 minutes' " +
                 "--max-renewable-life='10 minutes' --pw-expiration-time=never " +
                 "--attributes='' " + fields[0] + "/mail") != 0:
        die("kadmin add failed! (mail)")
    os.system("kadmin get %1s/mail" % (fields[0]))

    # Create the user's PTS id
    print "Creating PTS id..."
    if os.system("pts createuser %1s -c club.cc.cmu.edu" % (fields[0])) != 0:
        die("pts createu failed!")

    # run "pts examine id"
    # TODO: catch exceptions
    ptsproc = subprocess.Popen(['pts', 'examine', fields[0]],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    (stdoutdata, stderrdata) = ptsproc.communicate()
    for line in (stdoutdata + stderrdata).split("\n"):
        match = re.match(r".*id:[ ]*([0-9]+).*", line)
        if match: # found an id field
            ptsid = match.group(1)
            print "*** PTSID is %s" % (ptsid)
            break

    os.system("pts createuser %(user)s.mail -c club.cc.cmu.edu" %
              {"user": fields[0]}) == 0 or die("pts createu failed! (mail)")

    os.system("pts examine %(user)s.mail " % {"user": fields[0]})

    # Create the AFS volume and the mount points

    print "Creating AFS volume..."
    uname = fields[0]
    if os.system("vos create %(site)s user.%(uname)s -cell %(cell)s -v" %
                 {"uname": uname, "site": site, "cell": cell}) != 0:
        die("vos create failed!")

    if os.system("fs mkm %(mountpt)s\/%(uname)s user.%(uname)s " +
                 "-cell %(cell)s" % {"uname": uname, "mountpt": mountpt}) != 0:
        die("fs mkm failed!")

    if os.system("fs mkm %(mountpt)s\/%(uname)s\/OldFiles " +
                 "user.%(uname)s.backup -cell %(cell)s" % {"uname": uname,
                                                           "mountpt": mountpt,
                                                           "cell": cell}) != 0:
        die("fs mkm OldFiles failed!")

    if os.system("vos release %(usrvol)s -cell %(cell)s -verbose" %
                 {"usrvol": usrvol, "cell": cell}) != 0:
        print "vos release %(usrvol)s failed!" % {"uservol": uservol}

    # Create the mail volume and the mount points
    print "Creating AFS mail volume..."
    uname = fields[0]
    if os.system("vos create $site mail.$uname -cell $cell -v" %
                 {"site": site, "uname": uname, "cell": cell}) != 0:
        die("vos create failed! (maildir)")

    if os.system("fs mkm %(mountpt)s\/%(uname)s\/Maildir mail.%(uname)s " +
                 "-cell %(cell)s" % {"mountpt": mountpt, "uname": uname,
                                     "cell": cell}) != 0:
        die("fs mkm failed! (maildir)")
    if os.system("fs mkm %(mountpt)s\/%(uname)s\/Maildir\/OldFiles " +
                 "mail.%(uname)s.backup -cell %(cell)s" %
                 {"mountpt": mountpt, "uname": uname, "cell": cell}) != 0:
        die("fs mkm OldFiles failed! (maildir)")

    os.system("fs checkv")

    # Set up the maildir (maildirmake won't do this for an existing
    # mountpoint...)
    maildir = os.path.join(homedir, uname, "Maildir")
    os.mkdir(maildir + "/cur");
    os.mkdir(maildir + "/new");
    os.mkdir(maildir + "/tmp");

    # We explicitly chown and chmod these because qmail is paranoid
    ownership = "%s:%s" % (ptsid, usergroup)
    userhome = os.path.join(homedir, uname)
    permission = "0755"
    os.system("chown %s %s" % (ownership, userhome))
    os.system("chmod %s %s" % (permission, userhome))
    os.system("chown %s %s" % (ownership, maildir))
    os.system("chmod %s %s" % (permission, maildir))
    os.system("chown %s %s" % (ownership, maildir + "/cur"))
    os.system("chmod %s %s" % (permission, maildir + "/cur"))
    os.system("chown %s %s" % (ownership, maildir + "/new"))
    os.system("chmod %s %s" % (permission, maildir + "/new"))
    os.system("chown %s %s" % (ownership, maildir + "/tmp"))
    os.system("chmod %s %s" % (permission, maildir + "/tmp"))

    # Update permissions
    print "Updating permissions..."
    # Run "fs sa <dir> <username> all -clear" on every directory
    # in the user's home directory (in reverse order) <-- is this necessary?
    findproc = subprocess.Popen(["find", userhome, "-type", "d", "-print"],
                                stdout=subprocess.PIPE)
    directories = findproc.communicate()
    for directory in reversed(directories.split("\n")):
        if len(directory) != 0:
            os.system("fs sa $s $s all -clear" % (directory, uname))

    # used to do a default .qmail file here

    # We explicitly chown and chmod these because qmail is paranoid
    os.system("chown %s %s" % (ownership, userhome))
    os.system("chmod %s %s" % (permission, userhome))

    if os.system("fs sa %(home)s %(uname)s all system:anyuser l -clear" %
                 {userhome, uname}) != 0:
        die("fs sa failed!")

    if os.system("fs setquota %(home)s %(quota)s" %
                 {"home": userhome, "quota": quota}) != 0:
        die("fs sq failed!")

    # mail principal needs r on homedir to read .qmail*
    # bucy 200303
    if os.system("fs sa %(home)s %(uname)s.mail rl" %
                 {"home": userhome, "uname": uname}) != 0:
        die("fs sa failed! (maildir)")

    if os.system("fs sa %(maildir)s %(uname)s.mail rlidwk" %
                 {"maildir": maildir, "uname": uname}) != 0:
        die("fs sa failed! (maildir)")

    for subdir in ["cur", "new", "tmp"]:
        if os.system("fs sa %(maildir)s/%(subdir)s %(uname)s all " +
                     "%(uname)s.mail rlidwk -clear" % {"maildir": maildir,
                                                       "subdir": subdir,
                                                       "uname": uname}) != 0:
            die("fs sa failed! (maildir)")

    if os.system("fs sq %s %s" % (maildir, mquota)) != 0:
        die("fs sq failed!")

    # Create the AFS backup volumes
    print "Creating backup..."
    if os.system("vos backup user.%s -cell %s" % (uname, cell)) != 0:
        die("vos backup failed!")

    if os.system("vos backup mail.%s -cell %s" % (uname, cell)) != 0:
        die("vos backup failed! (maildir)")

    # add the entry to passwd.user
    # TODO: handle file not found
    with open(PasswdDotUser, "a+") as passwdUserFile:
        entry = "%(uname)s:K:%(ptsid)s:%(usergroup)s:%(realname)s:" + \
                "%(homedir)s/%(uname)s:/bin/bash\n" % \
                {"uname": uname, "ptsid": ptsid, "usergroup": usergroup,
                 "realname": fields[2], "homedir": homedir}
        passwdUserFile.write(entry)

    # extract mail keytab
    if os.system("kadmin ext -k %(mailtabsdir)s/%(uname)s %(uname)s/mail" %
                 {"uname": uname, "mailtabsdir": mailtabsdir}) != 0:
        die("kadmin ext for mailtab failed!")
    if os.system("chown %(ptsid)s %(mailtabsdir)s/%(uname)s" %
                 {"uname": uname, "mailtabsdir": mailtabsdir,
                  "ptsid": ptsid}) != 0:
        die("chown for mailtab failed!")
    if os.system("chmod u-w %(mailtabsdir)s/%(uname)s" %
                 {"uname": uname, "mailtabsdir": mailtabsdir}) != 0:
        die("chmod for mailtab failed!")

    # Send out mail
    #    print "Sending mail to $U[3]\n";
    #    seek(letterFile,0,0);
    #    open(sendFile,"|$mailer $U[3]");
    #    print sendFile "From: CMUCC Accounts <gripe\@club.cc.cmu.edu>\n";
    #    print sendFile "Reply-To: gripe\@club.cc.cmu.edu\n";
    #    print sendFile "Subject: $subj\n\n";
    #    while(<letterFile>)
    #    {
    #    s/%EXPR%/$expire/;
    #    s/%USER%/$uname/;
    #    s/%PASS%/$U[1]/;
    #    print sendFile;
    #    }
    #    print sendFile "\n";
    #    close(sendFile);

#close(usersFile);
close(letterFile);


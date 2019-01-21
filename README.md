**gpgmda-client - Client tools for gpgmda.**

https://github.com/jakeogh/gpgmda-client


# DESCRIPTION:
-------------------------
**This is a set of scripts to accept, distribute and optionally interact with email. At it's core is a Mail Delivery Agent ([MDA](https://en.wikipedia.org/wiki/Mail_delivery_agent)) [gpgmda](https://github.com/jakeogh/gpgmda) which saves incoming and outgoing messages on the mail server encrypted with your public key.**

- Incoming and outgoing mail is written to disk encrypted with your public key on the mail server (postfix so far).

- Mail is distributed to any number of mail clients (and converted to std maildir format) via ssh/rsync.

- Mail is optionally read, tagged, and replied to with gpgmda-client which uses [alot](https://github.com/pazz/alot). Standard end-to-end public key encryption and decryption are supported. Any maildir compatible client can be used.


# DEPENDENCIES:
-------------------------

- gpgmda: https://github.com/jakeogh/gpgmda (server side)
- python3: http://python.org
- bash: https://www.gnu.org/software/bash/
- gnupg: http://gnupg.org
- ssh: http://openssh.org
- rsync: http://rsync.samba.org
- tar: http://www.gnu.org/software/tar
- coreutils: http://www.gnu.org/software/coreutils
- xapian: http://xapian.org
- notmuchmail: http://notmuchmail.org
- alot: https://github.com/pazz/alot
- getmail: http://pyropus.ca/software/getmail (optional, used if you have POP/IMAP accounts you want to pull/migrate from)


# COMPONENTS:
-------------------------

**gpgmda-client**

- Download new mail, decrypt, add to notmuch, and read with alot (or your client of choice).

**gpgmda-client-send**

- Called by alot to send message via ssh through the mail server hosting gpgmda. Note this determines the user that postfix uses to send mail.

**gpgmda-client-getmail-gmail**

- Download gmail account (needs fixing).

**gpgmda-client-make-alot-theme**

- Generate alot theme configuration file (edit this to customize the alot theme).

**gpgmda-client-make-alot-config**

- Generate alot configuration file (edit this to customize alot).

**LICENSE**

- Public Domain

**nottoomuch-addresses.sh**

- Script for managing the notmuch address book and address autocomplete in alot.
- See: https://github.com/domo141/nottoomuch/blob/master/nottoomuch-addresses.rst

**gpgmda-client-generate-example-configs**

- Create example config files under ~/.gpgmda (run this and then read the examples in ~/.gpgmda/).

**gpgmda-client-check-postfix-config**

- Setup script for postfix. (needs work)


# INSTALLATION:
-------------------------
1. Install the dependencies.

3. Execute gpgmda-client-generate-gpgmda-example-configs, edit and rename the example files.

4. Run "gpgmda-client --download --decrypt --update_notmuch --read user@domain.net" to rsync, decrypt, index and read your mail.

5. Run "gpgmda-client --read user@domain.net" to just read your mail.

6. Add aliases in ~/.bashrc for steps 4 and 5.

7. Fix bugs, send patches.


# FEATURES:
-------------------------
This system protects the headers, body and attachments of mail "at rest" on the server. Similar MDA's apply public key encryption to the body and attachments, but this leaves the metadata (like FROM, TO and SUBJECT) in plaintext.

If you use this, your email is backed up; by default these scripts leave your mail (sent or received) encrypted on the server and your local machine syncs to it. If it's deleted it off the server, your local copy remains, and vice versa.

[alot](https://github.com/pazz/alot) has all of the features expected from a modern email client:

* Tagging. Like gmail, you can add tags and group messages by tags.
* Threading.
* Searching. Notmuch (the email index) has extensive search capabilities via [xapian](http://xapian.org/).
* HTML view. You can configure alot to pipe a message to any app, so it's easy to view an HTML message by automatically (if desired) sending it to a web browser. In theory you could even render it in the terminal with "links2 -g".
* Themes.
* Multiple accounts.
* Full support for PGP/MIME encryption and signing.

alot Docs:

- Overview: https://github.com/pazz/alot
- Manual: http://alot.readthedocs.org/en/latest/


**Similar software:**

https://github.com/SkullTech/drymail

gpgit:
 
- https://grepular.com/Automatically_Encrypting_all_Incoming_Email
- https://github.com/mikecardwell/gpgit

S/MIME 3.1: (?)

- https://tools.ietf.org/html/rfc3851#page-14
- https://news.ycombinator.com/item?id=10006655
	

# CONTRIBUTE:
-------------------------
Feedback and patches are greatly appreciated.

Support for MUA's other than alot exists but needs testing, gpgmda-client creates a normal local Maildir from the encrypted Maildir on the server. Any maildir compatible email client can use it. More documentation is needed.


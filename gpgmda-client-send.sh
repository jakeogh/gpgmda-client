#!/bin/bash

#
# 1. take stdin and tee it to /dev/shm/lastmail
# 2. pipe stdin to ssh user@domain.com
# 3. pee on the server side to the sentusers maildir and send the message via sendmail

# note the send from address $1 (fed to sendmail) needs to match the ssh login and therefore the local user on the mailserver

# $1 sets the user@email_server.com that this mail is submitted to via ssh for sending via sendmail
# $2 sets the Sender: (not the From:, that is set when you compose the message)

user="${1}"
shift
domain=`echo "${user}" | cut -d '@' -f 2`
sentuser="sentuser@${domain}"

tee /dev/shm/lastmail | \
    /usr/bin/ssh "${user}" "pee \"sudo -u sentuser -g sentuser -i /bin/bash -c '/bin/cat - | /bin/gpgmda'\" \"/usr/sbin/sendmail -N delay,failure,success -t -i -f reply_to_the_from_address@${domain}\""

#old working:
#tee /dev/shm/lastmail | ssh "${sentuser}" "cat - | /bin/gpgmda" || exit 1
#cat /dev/shm/lastmail | ssh "${user}" "cat - | /usr/sbin/sendmail -N delay,failure,success -t -i -f reply_to_the_from_address@${domain}" || exit 1

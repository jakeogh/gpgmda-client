#!/bin/bash

#
# 1. pipe stdin to sendmail on the mailserver over ssh (this delivers the message to all recipiente)
# 2. pipe the same message directly to the remote mda using the "sentuser" (this puts a exact message copy in the sentuser gpgmda/.sent on the server, keeping the BCC fields)
#   * the order is actually reversed, so if something goes wrong, you have the message you were trying to send

# note the send from address $1 (fed to sendmail) needs to match the ssh login and therefore the local user on the mailserver


# $1 sets the user@email_server.com that this mail is submitted to via ssh for sending via sendmail
# $2 sets the Sender: (not the From:, that is set when you compose the message)

#echo "$1" " " "$2" > /home/user/delthissss 2>&1

user="${1}"
shift
domain=`echo "${user}" | cut -d '@' -f 2`
sentuser="sentuser@${domain}"

#cat - |  ssh "${1}" "cat - | /usr/sbin/sendmail -t -i -f ${2}" || exit 1
#cat - | tee /dev/shm/lastmail | ssh "${1}" "cat - | /usr/sbin/sendmail -N delay,failure,success -t -i -f reply_to_the_from_address@${domain}" || exit 1

#bug potential race
#bug uploading the message twice (cant write it to the remote disk, need to pee |)

# user@mail0:~$ sudo -u sentuser -g sentuser -i /bin/bash -c "/bin/cat /home/user/testmail | /bin/gpgmda"

tee /dev/shm/lastmail | \
    ssh "${user}" 'sudo -u sentuser -g sentuser -i /bin/bash -c "/bin/cat - | /bin/gpgmda"'

#working:
#tee /dev/shm/lastmail | ssh "${sentuser}" "cat - | /bin/gpgmda" || exit 1
#cat /dev/shm/lastmail | ssh "${user}" "cat - | /usr/sbin/sendmail -N delay,failure,success -t -i -f reply_to_the_from_address@${domain}" || exit 1

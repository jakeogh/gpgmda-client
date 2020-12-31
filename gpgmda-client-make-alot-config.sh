#!/bin/bash

#todo: moved address_replacement and addresses_to_names to ~/.gpgmda/ so this is almost not needed, the only reason it's still here is because $DIR is still used in the alot config file.
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ] ; do SOURCE="$(readlink "$SOURCE")"; done
#DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"        # http://stackoverflow.com/questions/59895/can-a-bash-script-tell-what-directory-its-stored-in

config_dir="$HOME/.gpgmda"

email_address="${1}"

if [[ -s "${config_dir}/addresses_to_names" ]]
then
    #echo "grepping ${config_dir}/addresses_to_names for a name"
    name=$(grep -i "${email_address}" "${config_dir}"/addresses_to_names | cut -d '=' -f 2 | head -n 1) || name="${email_address}"
    #echo "$name"
else
    name="${email_address}"
fi


if [[ -s "${config_dir}/address_replacement" ]]
then
    #echo "grepping ${config_dir}/address_replacement"
    alias_address=$(grep -i "${email_address}" "${config_dir}"/address_replacement | cut -d '=' -f 2 | head -n 1) || alias_address="${email_address}"
    #echo "$alias_address"
else
    alias_address="${email_address}"
fi



make_alot_config()
{
cat <<EOF

# config section for sending mail

#themes_dir = /dev/shm
#theme = __alot_theme_${email_address}
editor_cmd = /home/cfg/appwrappers/vi
notify_timeout = 3
timestamp_format = "%Y-%m-%d %I:%m%p %Z [%c]"
auto_remove_unread = True
# remove_unread_on_summary_touch = True
print_cmd = /home/cfg/print/to/text_file
hooksfile = ~/.config/alot/hooks.py

[accounts]
	[[default]]
		realname = ${name}
		address = ${alias_address}
		sendmail_command = gpgmda-client-send.sh ${email_address} ${alias_address}
		[[[abook]]]
			type = shellcommand
			command = gpgmda-client address-query ${email_address}
			regexp = \"(?P<name>.+)\"\s*<(?P<email>.*.+?@.+?)>

# to send a mail in alot enter the compose command http://alot.readthedocs.org/en/latest/usage/index.html#commands
# type
# :compose [ENTER]

[bindings]
    Z = search NOT tag:inbox
    A = search NOT tag:killed
    L = taglist
    n = compose
    esc = exit


#    [[bufferlist]]
#        select = openfocussed

#    [[search]]
#        a = toggletags unread
#        S = toggletags spam; untag unread
#        s = ""

#    [[envelope]]
#        H = toggleheaders

#    [[taglist]]

#    [[thread]]
#       h = togglesource
#       A = save --all --autopath
#       F = forward --attach
#       s = save --autopath

EOF
}


#    [[search]]
#        a = toggletags inbox


make_alot_config


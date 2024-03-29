#!/bin/bash

config_dir="~/.gpgmda"

mkdir "${config_dir}" > /dev/null 2>&1 || :

#TODO note this example functions are only here for reference, this script can not produce output other than the make_alot_config() function below or it will break.
make_addresses_to_names_example()
{
cat <<EOF
# you must rename this file to ~/.gpgmda/addresses_to_names for make_alot_config to parse it. List as many email to name mappings as you like. Most likely you only need one.
# Note this is not the address book, alot handles that. This sets your realname in the make_alot_config() function. See the source of make_alot_config for more information.
email@domain.com=Your Name
other.email@domain.com=Maybe Also Your Name

EOF
}


make_address_replacement_example()
{
cat <<EOF
# you must rename this file to ~/.gpgmda/address_replacement for make_alot_config to parse it. List as many email to email mappings as you like. Most likely you only need one.
# the right hand side will become the address the left side user appears to send from. They could be the same. See the source of make_alot_config for more information.
user@domain.com=some.alias@domain.com
other.user@domain.com=some.alias@domain.com
another.user@domain.com=some.other.alias@domain.com

EOF
}

make_getmail_tags_example()
{
cat <<EOF
# you must remove the .example from the end of this file and rename it to the correct gmail address
Inbox
Personal
Travel
Receipts
Work
the tags above are the default gmail tags
you likely want them
these are other tags
like
a_example_tag
gmail tags can have spaces
you gotta enter them manually here
or
here
and
right here
one tag
per line
no duplicates
althouth a duplicate wont hurt anything
i had a over a hundred tags
so I grepped them out of a
saved copy of my inbox page

EOF
}


make_addresses_to_names_example > ~/.gpgmda/addresses_to_names.example

make_address_replacement_example > ~/.gpgmda/address_replacement.example

make_getmail_tags_example > ~/.gpgmda/getmail_tags.example




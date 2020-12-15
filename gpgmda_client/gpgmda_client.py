#!/usr/bin/env python3
# -*- coding: utf8 -*-

# pylint: disable=C0111  # docstrings are always outdated and wrong
# pylint: disable=W0511  # todo is encouraged
# pylint: disable=C0301  # line too long
# pylint: disable=R0902  # too many instance attributes
# pylint: disable=C0302  # too many lines in module
# pylint: disable=C0103  # single letter var names, func name too descriptive
# pylint: disable=R0911  # too many return statements
# pylint: disable=R0912  # too many branches
# pylint: disable=R0915  # too many statements
# pylint: disable=R0913  # too many arguments
# pylint: disable=R1702  # too many nested blocks
# pylint: disable=R0914  # too many local variables
# pylint: disable=R0903  # too few public methods
# pylint: disable=E1101  # no member for base
# pylint: disable=W0201  # attribute defined outside __init__
# pylint: disable=R0916  # Too many boolean expressions in if statement


# todo: locking to prevent multiple instances of mail_update

import glob
import os
import shutil
import subprocess
import sys
import time
#from multiprocessing import Process     #https://docs.python.org/3/library/multiprocessing.html
#from multiprocessing import Pool, cpu_count
from pathlib import Path

import click
from getdents import files
from icecream import ic
from kcl.dirops import check_or_create_dir, path_is_dir
from kcl.fileops import empty_file
from kcl.pathops import path_exists
from kcl.printops import ceprint, eprint

global debug
debug = False

#global NOTMUCH_QUERY_HELP
#NOTMUCH_QUERY_HELP = "notmuch search --output=files 'thread:000000000003c194'"


def check_for_notmuch_database(email_archive_folder):
    notmuch_database_folder = email_archive_folder + "/_Maildirs/.notmuch/xapian"
    if not os.path.isdir(notmuch_database_folder):
        eprint('''Error: notmuch has not created the xapian database yet. Run \"mail_update user@domain.com --update\" first. Exiting.''')
        sys.exit(1)


def rsync_mail(*,
               email_address,
               gpgMaildir_archive_folder,):
    ic()
    load_ssh_key(email_address=email_address)
    ic('running rsync')
    rsync_p = \
        subprocess.Popen(['rsync',
                          '--ignore-existing',
                          '--size-only',
                          '-t',
                          '--whole-file',
                          '--copy-links',
                          '--stats',
                          '-i',
                          '-r',
                          '-vv',
                          email_address + ':gpgMaildir',
                          gpgMaildir_archive_folder + '/'], stdout=subprocess.PIPE)
    rsync_p_output = rsync_p.communicate()

    for line in rsync_p_output[0].split(b'\n'):
        if b'exists' not in line:
            eprint(line)

    ic(rsync_p.returncode)
    if rsync_p.returncode != 0:
        ic('rsync did not return 0, exiting')
        sys.exit(1)

    rsync_logfile = "/dev/shm/.gpgmda_rsync_last_new_mail_" + email_address
    with open(rsync_logfile, 'wb') as rsync_logfile_handle:
        rsync_logfile_handle.write(rsync_p_output[0])
        ic('wrote rsync_logfile:', rsync_logfile)


def run_notmuch(*,
                mode,
                email_address,
                email_archive_folder,
                gpgmaildir,
                query,
                notmuch_config_file,
                notmuch_config_folder,):

    ic()
    yesall = False

    if mode == "update_notmuch_db":
        current_env = os.environ.copy()
        current_env["NOTMUCH_CONFIG"] = notmuch_config_file

        notmuch_new_command = ["notmuch", "--config=" + notmuch_config_file, "new"]
        ceprint("notmuch_new_command:", notmuch_new_command)
        notmuch_p = subprocess.Popen(notmuch_new_command,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     shell=False,
                                     env=current_env)
        ic(notmuch_p.args)
        notmuch_p_output = notmuch_p.communicate()

        ic('notmuch_p_output:')
        ic(notmuch_p_output)

        ic('len(notmuch_p_output[0]):', len(notmuch_p_output[0]))

        ic('notmuch_p_output[0]:')
        for line in notmuch_p_output[0].split(b'\n'):
            ic(line.decode('utf-8'))

        ic('notmuch_p_output[1]:')
        for line in notmuch_p_output[1].split(b'\n'):
            line = line.decode('utf-8')
            ic(line)
            if "Note: Ignoring non-mail file:" in line:
                non_mail_file = line.split(" ")[-1]
                ic('found file that gmime does not like:', non_mail_file)
                random_id = non_mail_file[-40:]
                ic(random_id)
                maildir_subfolder = non_mail_file.split('/')[-2]
                ic(maildir_subfolder)
                encrypted_file = gpgmaildir + '/' + maildir_subfolder + '/' + random_id
                ic(encrypted_file)
                ic('head -c 500:')
                command = "head -c 500 " + non_mail_file
                os.system(command)
                if not yesall:
                    ic('running vi')
                    command = "vi " + non_mail_file
                    os.system(command)

                    delete_message_answer = \
                        input("Would you like to move this message locally to the ~/.gpgmda/non-mail folder and delete it on the server? (yes/no/skipall/yesall): ")

                    if delete_message_answer.lower() == "yesall":
                        yesall = True
                    if delete_message_answer.lower() == "skipall":
                        break
                else:
                    delete_message_answer = 'yes'

                if delete_message_answer.lower() == "yes":
                    non_mail_path = '~/.gpgmda/non-mail'

                    os.path.sep = '/'      #py3: paths _are_ bytes. glob.glob(b'/home') does it right
                    os.path.altsep = '/'

                    os.makedirs(os.path.expanduser(non_mail_path), exist_ok=True)

                    ic('Processing files for local move and delete:')

                    eprint(non_mail_file)
                    shutil.move(non_mail_file, os.path.expanduser(non_mail_path))

                    eprint(encrypted_file)
                    shutil.move(encrypted_file, os.path.expanduser(non_mail_path))

                    if maildir_subfolder == ".sent":
                        target_file = "/home/sentuser/gpgMaildir/new/" + random_id
                        command = "ssh root@v6y.net rm -v " + target_file
                        eprint(command)
                        os.system(command)

                    elif maildir_subfolder == "new":
                        target_file = "/home/user/gpgMaildir/new/" + random_id
                        command = "ssh root@v6y.net rm -v " + target_file    #todo use ~/.gpgmda/config
                        eprint(command)
                        os.system(command)
                    else:
                        eprint("unknown maildir_subfolder:", maildir_subfolder, "exiting")
                        sys.exit(1)

        eprint("notmuch_p.returncode:", notmuch_p.returncode)
        if notmuch_p.returncode != 0:
            eprint("notmuch new did not return 0, exiting")
            sys.exit(1)

    elif mode == "query_notmuch":
        check_for_notmuch_database(email_archive_folder=email_archive_folder)
        command = "NOTMUCH_CONFIG=" + notmuch_config_file + " notmuch " + query
        eprint("command:", command)
        return_code = os.system(command)
        if return_code != 0:
            eprint("\"notmuch " + query + "\" returned nonzero, exiting")
            sys.exit(1)

    elif mode == "query_afew":
        check_for_notmuch_database(email_archive_folder=email_archive_folder)
        command = "afew" + " --notmuch-config=" + notmuch_config_file + " " + query
        eprint("command:", command)
        return_code = os.system(command)
        if return_code != 0:
            eprint("\"notmuch " + query + "\" returned nonzero, exiting")
            sys.exit(1)

    elif mode == "query_address_db":
        check_for_notmuch_database(email_archive_folder=email_archive_folder)
        command = "XDG_CONFIG_HOME=" + \
                  notmuch_config_folder + \
                  " NOTMUCH_CONFIG=" + \
                  notmuch_config_file + " " + \
                  "nottoomuch-addresses.sh " + \
                  query
        return_code = os.system(command)
        if return_code != 0:
            eprint("\"nottoomuch-addresses.sh\" returned nonzero, exiting")
            sys.exit(1)

    elif mode == "build_address_db":
        check_for_notmuch_database(email_archive_folder=email_archive_folder)
        command = "XDG_CONFIG_HOME=" + \
                  notmuch_config_folder + \
                  " NOTMUCH_CONFIG=" + \
                  notmuch_config_file + \
                  " " + \
                  "nottoomuch-addresses.sh --update --rebuild"
        return_code = os.system(command)
        if return_code != 0:
            eprint("\"nottoomuch-addresses.sh\" returned nonzero, exiting")
            sys.exit(1)

    elif mode == "update_address_db":
        check_for_notmuch_database(email_archive_folder=email_archive_folder)
        command = "XDG_CONFIG_HOME=" + \
                  notmuch_config_folder + \
                  " NOTMUCH_CONFIG=" + \
                  notmuch_config_file + " " + \
                  "nottoomuch-addresses.sh --update"
        return_code = os.system(command)
        if return_code != 0:
            eprint("\"nottoomuch-addresses.sh\" returned nonzero, exiting")
            sys.exit(1)

    else:
        ic('invalid', mode, 'exiting.')
        sys.exit(1)


def make_notmuch_config(*,
                        email_address,
                        email_archive_folder,):

    ic()
    username = email_address.split("@")[0]

    notmuch_config = """
[database]
path = """ + email_archive_folder + """/_Maildirs

[user]
name = """ + username + """
primary_email=""" + email_address + """

[new]
tags = unread;inbox;

[maildir]
synchronize_flags = False

[global]
quit_on_last_bclose = True
"""
    notmuch_config_folder = '/'.join([email_archive_folder, "_notmuch_config"])
    check_or_create_dir(notmuch_config_folder)
    notmuch_config_file_location = '/'.join([notmuch_config_folder, ".notmuch_config"])
    if debug:
        ic('writing notmuch config to:', notmuch_config_file_location)
    notmuch_config_file_handle = open(notmuch_config_file_location, "w")
    notmuch_config_file_handle.write(notmuch_config)
    notmuch_config_file_handle.close()


def move_terminal_text_up_one_page():
    ic('moving terminal text up one page')
    tput_p = subprocess.Popen(['tput', 'lines'], stdout=subprocess.PIPE)
    tput_p_output = tput_p.communicate()
    tput_p_output = tput_p_output[0].decode('utf8').strip()

    for line in range(int(tput_p_output)):
        print('', file=sys.stderr)


def start_alot(*,
               email_address,
               email_archive_folder,):

    ic()
    check_for_notmuch_database(email_archive_folder=email_archive_folder)
    alot_config = subprocess.Popen(["gpgmda-client-make-alot-config.sh", email_address], stdout=subprocess.PIPE).communicate()
    alot_theme = subprocess.Popen(["gpgmda-client-make-alot-theme.sh"], stdout=subprocess.PIPE).communicate()

    alot_config_f = open('/dev/shm/__alot_config_' + email_address, 'w')
    alot_theme_f = open('/dev/shm/__alot_theme_' + email_address, 'w')

    alot_config_f.write(alot_config[0].decode('UTF8'))
    alot_theme_f.write(alot_theme[0].decode('UTF8'))

    alot_config_f.close()
    alot_theme_f.close()

    notmuch_config_folder = email_archive_folder + '/_notmuch_config'
    ic('starting alot')
    os.system(' '.join(['alot', '--version']))
    move_terminal_text_up_one_page()        # so alot does not overwrite the last messages on the terminal
    alot_p = os.system(' '.join(['/usr/bin/alot',
                                 '-C',
                                 '256',
                                 '--debug-level=debug',
                                 '--logfile=/dev/shm/__alot_log',
                                 '--notmuch-config',
                                 notmuch_config_folder + '/.notmuch_config',
                                 '--mailindex-path',
                                 email_archive_folder + '/_Maildirs',
                                 '-c',
                                 '/dev/shm/__alot_config_' + email_address]))


def load_ssh_key(email_address):
    ic('load_ssh_key(%s)' % email_address)
    if 'gmail' in email_address:
        return

    ssh_key = '/home/user/.ssh/id_rsa__' + email_address   # todo use ~/.gpgmda/config

    loaded_ssh_keys_p = subprocess.Popen(['ssh-add', '-l'], stdout=subprocess.PIPE)
    loaded_ssh_keys_p_output = loaded_ssh_keys_p.communicate()[0].strip().decode('UTF8')
    loaded_ssh_key_list = loaded_ssh_keys_p_output.split('\n')

    ic('ssh-add -l output:')
    for line in loaded_ssh_key_list:
        eprint(line)

    ic('looking for key:', ssh_key)
    found_key = 0
    for key in loaded_ssh_key_list:
        if ssh_key in key:
            found_key = 1
            break

    if found_key != 1:
        ssh_add_p = subprocess.Popen(['ssh-add', ssh_key])
        ssh_add_p_output = ssh_add_p.communicate()
        if ssh_add_p.returncode != 0:
            ic('something went wrong adding the ssh_key, exiting')
            sys.exit(1)


def short_random_string():
    command = ["gpg2", "--gen-random", "--armor", "1", "100"]
    cmd_proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=False)
    cmd_output = cmd_proc.stdout.read().strip() #get rid of newline
    return cmd_output


def get_maildir_file_counts(*,
                            gpgmaildir,
                            maildir,):
    ic()
    files_in_gpgmaildir = len(list(files(gpgmaildir)))
    files_in_maildir = len(list(files(maildir)))
    return {'files_in_gpgmaildir': files_in_gpgmaildir,
            "files_in_maildir": files_in_maildir}


def parse_rsync_log_to_list(*,
                            email_address,
                            gpgMaildir_archive_folder,):
    ic()
    rsync_log = '/dev/shm/.gpgmda_rsync_last_new_mail_' + email_address
    with open(rsync_log, 'r') as fh:
        rsync_log = fh.readlines()

    full_path_list = []
    for line in rsync_log:
        line = line.strip()  # remove newlines
        if 'exists' not in line:
            if 'gpgMaildir' in line:
                if line.startswith('>f'):
                    new_gpgmda_file_path = gpgMaildir_archive_folder + '/' + line.split(' ')[1]
                    ic(new_gpgmda_file_path)
                    full_path_list.append(new_gpgmda_file_path)

    message_list = []
    for line in full_path_list:
        assert len(line) > 0
        message_list.append(Path(line))

    return message_list


def decrypt_list_of_messages(*,
                             message_list,
                             email_address,
                             maildir,
                             delete_badmail,
                             skip_badmail,
                             move_badmail,):

    ic()
    ic(message_list)
    #process_count = min(cpu_count(), len(message_list))
    #message_list_filter = filter(None, message_list)   #remove empty items
    #ic(process_count)
    #p = Pool(process_count)
    index = 0
    for index, gpgfile in enumerate(message_list):    #useful for debugging
        decrypt_message(email_address=email_address,
                        gpgfile=gpgfile,
                        maildir=maildir,
                        delete_badmail=delete_badmail,
                        skip_badmail=skip_badmail,
                        move_badmail=move_badmail,)

    ic('done:', index)


def move_to_badmail(gpgfile):
    ic()
    badmail_path = os.path.expanduser(b'~/.gpgmda/badmail')
    #print("type(badmail_path):", type(badmail_path))
    os.makedirs(os.path.expanduser(badmail_path), exist_ok=True)
    ic('Processing files for local move and delete gpgfile:', gpgfile)

    os.path.sep = b'/'      #py3: paths _are_ bytes. glob.glob(b'/home') does it right
    os.path.altsep = b'/'
    shutil.move(gpgfile.as_posix(), badmail_path)


def decrypt_message(*,
                    email_address,
                    gpgfile,
                    delete_badmail,
                    skip_badmail,
                    move_badmail,
                    maildir,
                    stdout=False,):

    assert isinstance(gpgfile, Path)

    ic('decrypt_msg():', gpgfile)
    if '@' not in email_address:
        ic('Invalid email address:', email_address, ', exiting.')
        sys.exit(1)

    if not path_exists(gpgfile):
        ic(gpgfile, 'No such file or directory. Exiting.')
        sys.exit(1)

    if empty_file(gpgfile):
        ic('FOUND ZERO LENGTH FILE, EXITING. CHECK THE MAILSERVER LOGS (and manually delete it):', gpgfile)
        sys.exit(1)

    gpgfile_name = os.path.basename(gpgfile)
    ic(gpgfile_name)

    gpgfile_folder_path = os.path.dirname(gpgfile)
    ic(gpgfile_folder_path)

    maildir_subfolder = os.path.basename(gpgfile_folder_path)
    ic(maildir_subfolder)
    if not path_is_dir(maildir):
        ic(maildir, 'does not exist. Exiting.')
        sys.exit(1)

    #file_previously_decrypted = 0
    glob_pattern = maildir + '/' + maildir_subfolder + '/*.' + gpgfile_name
    ic(glob_pattern)
    result = glob.glob(glob_pattern)

    if len(result) > 1:
        ic('ERROR: This shouldnt happen. More than one result was returned for:', glob_pattern, ': ', result)
        sys.exit(1)

    if stdout is False:
        if len(result) == 1:
            result = result[0]
            ic('skipping existing file:', result)
            return True

    ic('decrypting:', gpgfile)
    if stdout:
        #command = "gpg2 -o - --decrypt " + gpgfile + " | tar --transform=s/$/." + gpgfile_name + "/ -xvf -" # hides the tar header
        command = "gpg2 -o - --decrypt " + gpgfile
        ic('decrypt_msg():', command)
        return_code = os.system(command)
        ic(return_code)

    else:
        gpg_command = ["gpg2", "-o", "-", "--decrypt", gpgfile]
        tar_command = ["tar", "--transform=s/$/." + gpgfile_name + "/", "-C", maildir + '/' + maildir_subfolder, "-xvf", "-"]
        gpg_cmd_proc = subprocess.Popen(gpg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        ic(gpg_command)
        gpg_cmd_proc_output_stdout, gpg_cmd_proc_output_stderr = gpg_cmd_proc.communicate()

        if debug:
            ic('gpg_cmd_proc_output_stdout:')
            gpg_cmd_proc_output_stdout_decoded = gpg_cmd_proc_output_stdout.decode('utf-8')
            for line in gpg_cmd_proc_output_stdout_decoded.split('\n'):
                ic('STDOUT:', line)

        ic('gpg_cmd_proc_output_stderr:')
        gpg_cmd_proc_output_stderr_decoded = gpg_cmd_proc_output_stderr.decode('utf-8')
        for line in gpg_cmd_proc_output_stderr_decoded.split('\n'):
            ic('STDERR:', line)

        ic(gpg_cmd_proc.returncode)
        if gpg_cmd_proc.returncode != 0:
            ic('gpg2 did not return 0')
            return False

        if len(gpg_cmd_proc_output_stdout) > 0:
            tar_cmd_proc = subprocess.Popen(tar_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
            ic('executing:', tar_command)
            tar_cmd_proc_output_stdout, tar_cmd_proc_output_stderr = tar_cmd_proc.communicate(gpg_cmd_proc_output_stdout)
            ic('tar_cmd_proc_output_stdout:')
            tar_cmd_proc_output_stdout_decoded = tar_cmd_proc_output_stdout.decode('utf-8')
            for line in tar_cmd_proc_output_stdout_decoded.split('\n'):
                ic('STDOUT:', line)

            ic('tar_cmd_proc_output_stderr:')
            tar_cmd_proc_output_stderr_decoded = tar_cmd_proc_output_stderr.decode('utf-8')
            for line in tar_cmd_proc_output_stderr_decoded.split('\n'):
                ic('STDERR:', line)

            ic(tar_cmd_proc.returncode)

            if tar_cmd_proc.returncode != 0:
                ic('tar did not return 0')
                return False
        else:
            ic('gpg did not produce any stdout, tar skipped file:', gpgfile)
            ic('looking into:', gpgfile, 'further...')
            os.system('/bin/ls -al ' + gpgfile.as_posix())
            stats = os.stat(gpgfile)
            if stats.st_size <= 1141:
                ic('this is likely an empty gpg encrypted file')

            if move_badmail:
                move_to_badmail(gpgfile)

            elif not skip_badmail:
                if delete_badmail is False:
                    delete_message_answer = \
                        input("Would you like to move this message locally to the ~/.gpgmda/badmail folder and delete it off the server? (yes/no/yesall/skipall/moveall): ")
                    if delete_message_answer.lower() == "yesall":
                        delete_badmail = True
                    if delete_message_answer.lower() == "skipall":
                        skip_badmail = True
                    if delete_message_answer.lower() == "moveall":
                        move_badmail = True
                if delete_badmail:
                    delete_message_answer = "yes"

                if delete_message_answer.lower() == "yes":
                    move_to_badmail(gpgfile)
                    random_id = gpgfile.split('/')[-1]

                    if maildir_subfolder == ".sent":
                        target_file = "/home/sentuser/gpgMaildir/new/" + random_id
                        command = "ssh root@v6y.net rm -v " + target_file
                        eprint(command)
                        os.system(command)
                    elif maildir_subfolder == "new":
                        target_file = "/home/user/gpgMaildir/new/" + random_id
                        command = "ssh root@v6y.net rm -v " + target_file    #todo use ~/.gpgmda/config
                        eprint(command)
                        os.system(command)
                    else:
                        ic('unknown exception, exiting')
                        sys.exit(1)
            return False
    return True


def gpgmaildir_to_maildir(*,
                          email_address,
                          delete_badmail,
                          skip_badmail,
                          move_badmail,
                          gpgMaildir_archive_folder,
                          gpgmaildir,
                          maildir,):

    # todo add locking
    ic()
    ic('gpgmda_to_maildir using:', gpgMaildir_archive_folder)
    ic('Checking for default-recipient in ~/.gnupg/gpg.conf')
    command = "grep \"^default-recipient\" ~/.gnupg/gpg.conf"
    grep_exit_code = os.system(command)
    if grep_exit_code != 0:
        eprint("error: default-recipient is not defined in ~/.gnupg/gpg.conf. Exiting.")
        sys.exit(1)

    rsync_last_new_mail_file = '/dev/shm/.gpgmda_rsync_last_new_mail_' + email_address
    ic('checking to see if', rsync_last_new_mail_file, 'exists and is greater than 0 bytes')
    rsync_files_transferred = 0
    if path_exists(rsync_last_new_mail_file):
        with open(rsync_last_new_mail_file, 'r') as fh:
            for line in fh.readlines():
                if 'Number of regular files transferred:' in line:
                    eprint(line)
                    rsync_files_transferred = int(line.split(':')[1].strip())
                    ic(rsync_files_transferred)
                    break
        if rsync_files_transferred == 0:
            ic('rsync transferred 0 files, skipping decrypt')

        else:
            rsync_list = parse_rsync_log_to_list(email_address=email_address,
                                                 gpgMaildir_archive_folder=gpgMaildir_archive_folder)
            ic(rsync_list)
            decrypt_list_of_messages(message_list=rsync_list,
                                     email_address=email_address,
                                     maildir=maildir,
                                     delete_badmail=delete_badmail,
                                     skip_badmail=skip_badmail,
                                     move_badmail=move_badmail,)

    else:
        ic(rsync_last_new_mail_file, 'does not exist or is 0 bytes')

    ic('checking if the message counts in the maildir and the gpgmaildir match')
    maildir_counts_dict = get_maildir_file_counts(gpgmaildir=gpgmaildir, maildir=maildir)
    ic(maildir_counts_dict)
    maildir_file_count = maildir_counts_dict['files_in_maildir']
    gpgmaildir_file_count = maildir_counts_dict['files_in_gpgmaildir']
    if gpgmaildir_file_count > maildir_file_count:
        ic('files_in_gpgmaildir > files_in_maildir:', gpgmaildir_file_count, '>', maildir_file_count)
        ic('locating un-decrypted files')
        files_in_gpgmaildir = [dent.pathlib for dent in files(gpgmaildir)]
        files_in_maildir = [dent.pathlib for dent in files(maildir)]
        ic('len(files_in_gpgmaildir):', len(files_in_gpgmaildir))
        ic('len(files_in_maildir):', len(files_in_maildir))
        hashes_in_gpgmaildir = [path.name for path in files_in_gpgmaildir]
        hashes_in_maildir = [path.name for path in files_in_maildir]
        #full_maildir_string = "\n".join(files_in_maildir)

        for gpgfile in files_in_gpgmaildir:
            #gpghash = gpgfile.split(b'/')[-1]
            gpghash = gpgfile.name
            if gpghash not in hashes_in_maildir:
                ic('found gpgfile that has not been decrypted yet:', gpgfile)
                decrypt_message(email_address=email_address,
                                gpgfile=gpgfile,
                                delete_badmail=delete_badmail,
                                skip_badmail=skip_badmail,
                                move_badmail=move_badmail,
                                maildir=maildir,
                                stdout=False)
    else:
        ic('files_in_gpgmaildir <= files_in_maildir, looks good')


def search_list_of_strings_for_substring(*,
                                         list_to_search,
                                         substring,):
    item_found = ''
    for item in list_to_search:
        try:
            if substring in item:
                item_found = item
                break
        except TypeError:
            pass
    return item_found


def update_notmuch_db(email_address, email_archive_folder, gpgmaildir, notmuch_config_file, notmuch_config_folder):
    run_notmuch(mode="update_notmuch_db",
                email_address=email_address,
                email_archive_folder=email_archive_folder,
                gpgmaildir=gpgmaildir,
                query=False,
                notmuch_config_file=notmuch_config_file,
                notmuch_config_folder=notmuch_config_folder)


def update_notmuch_address_db(email_address, email_archive_folder, gpgmaildir, notmuch_config_file, notmuch_config_folder):
    run_notmuch(mode="update_address_db",
                email_address=email_address,
                email_archive_folder=email_archive_folder,
                gpgmaildir=gpgmaildir,
                query=False,
                notmuch_config_file=notmuch_config_file,
                notmuch_config_folder=notmuch_config_folder)


def update_notmuch_address_db_build(email_address, email_archive_folder, gpgmaildir, notmuch_config_file, notmuch_config_folder):
    run_notmuch(mode="build_address_db",
                email_address=email_address,
                email_archive_folder=email_archive_folder,
                gpgmaildir=gpgmaildir,
                query=False,
                notmuch_config_file=notmuch_config_file,
                notmuch_config_folder=notmuch_config_folder)


def check_noupdate_list(email_address):
    noupdate_list = open(gpgmda_config_folder + "/.noupdate", 'r').readlines()  # todo move config to ~/.gpgmda
    for item in noupdate_list:
        if email_address in item:
            eprint(email_address + " is listed in .noupdate, exiting")
            sys.exit(1)


@click.group()
@click.option("--verbose", is_flag=True)
@click.pass_context
def client(ctx, verbose):
    start_time = time.time()
    if verbose:
        eprint(time.asctime())

    global gpgmda_config_folder
    gpgmda_config_folder = os.path.expanduser('~/.gpgmda/')

    if verbose:
        ic(time.asctime())
        ic('TOTAL TIME IN MINUTES:')
        ic((time.time() - start_time) / 60.0)


@client.command()
@click.argument("email_address", nargs=1, required=True, type=str)
#@click.option("--email-archive-type", help="", type=click.Choice(['gpgMaildir']), default="gpgMaildir")
@click.pass_context
def build_paths(ctx, email_address):
    assert '@' in email_address
    ctx.email_archive_type = 'gpgMaildir'

    ctx.email_archive_folder = "/home/user/__email_folders"
    check_or_create_dir(ctx.email_archive_folder)

    ctx.gpgMaildir_archive_folder_base_path = '/'.join([ctx.email_archive_folder, "_gpgMaildirs"])
    check_or_create_dir(ctx.gpgMaildir_archive_folder_base_path)

    ctx.gpgMaildir_archive_folder = '/'.join([ctx.gpgMaildir_archive_folder_base_path, email_address])
    check_or_create_dir(ctx.gpgMaildir_archive_folder)

    ctx.gpgmaildir = '/'.join([ctx.gpgMaildir_archive_folder, "gpgMaildir"])
    check_or_create_dir(ctx.gpgmaildir)

    stdMaildir_archive_folder = '/'.join([ctx.email_archive_folder, "_Maildirs", email_address])
    check_or_create_dir(stdMaildir_archive_folder)

    ctx.maildir = '/'.join([stdMaildir_archive_folder, "Maildir"])
    check_or_create_dir(ctx.maildir + "/new/")
    check_or_create_dir(ctx.maildir + "/cur/")
    check_or_create_dir(ctx.maildir + "/.sent/")

    ctx.notmuch_config_folder = '/'.join([ctx.email_archive_folder, "_notmuch_config"])
    check_or_create_dir(ctx.notmuch_config_folder)

    ctx.notmuch_config_file = '/'.join([ctx.notmuch_config_folder, ".notmuch_config"])
    make_notmuch_config(email_address=email_address, email_archive_folder=ctx.email_archive_folder)
    return ctx


@client.command()
@click.argument("email_address", nargs=1)
@click.argument("query", type=str)
@click.pass_context
def address_query(ctx, email_address, query):
    '''search for address string'''
    ctx = ctx.invoke(build_paths, email_address=email_address)
    run_notmuch(mode="query_address_db",
                email_address=email_address,
                query=query,
                email_archive_folder=ctx.email_archive_folder,
                gpgmaildir=ctx.gpgmaildir,
                notmuch_config_file=ctx.notmuch_config_file,
                notmuch_config_folder=ctx.notmuch_config_folder)


@client.command()
@click.argument("email_address", nargs=1)
@click.pass_context
def read(ctx, email_address):
    '''read mail without checking for new mail'''
    ctx = ctx.invoke(build_paths, email_address=email_address)
    load_ssh_key(email_address=email_address)     # so mail can be sent without having to unlock the key
    make_notmuch_config(email_address=email_address, email_archive_folder=ctx.email_archive_folder)
    start_alot(email_address=email_address, email_archive_folder=ctx.email_archive_folder)


@client.command()
@click.argument("email_address", nargs=1)
@click.option("--delete-badmail", help="", is_flag=True)
@click.option("--skip-badmail", help="", is_flag=True)
@click.option("--move-badmail", help="", is_flag=True)
@click.pass_context
def decrypt(ctx, email_address, delete_badmail, move_badmail, skip_badmail):
    '''decrypt new mail in encrypted maildir to unencrypted maildir'''
    ic()
    ctx = ctx.invoke(build_paths, email_address=email_address)
    check_noupdate_list(email_address=email_address)

    if ctx.email_archive_type == "gpgMaildir":
        ctx.invoke(warm_up_gpg)
        gpgmaildir_to_maildir(email_address=email_address,
                              gpgMaildir_archive_folder=ctx.gpgMaildir_archive_folder,
                              gpgmaildir=ctx.gpgmaildir,
                              maildir=ctx.maildir,
                              delete_badmail=delete_badmail,
                              skip_badmail=skip_badmail,
                              move_badmail=move_badmail,)

        ic('done with gpgmaildir_to_maildir()')
    else:
        ic('Unsupported:', ctx.email_archive_type, 'Exiting.')
        sys.exit(1)


@client.command()
@click.argument("email_address", nargs=1)
@click.pass_context
def update_notmuch(ctx, email_address):
    '''update notmuch with new mail from (normal, unencrypted) maildir'''
    ic()
    ctx = ctx.invoke(build_paths, email_address=email_address)
    check_noupdate_list(email_address=email_address)

    if ctx.email_archive_type == "gpgMaildir":
        ctx.invoke(warm_up_gpg)

    elif ctx.email_archive_type == "getmail":
        ic('gpgmda_program_folder/getmail_gmail "${email_address}" || exit 1')
        ic("todo, call /getmail_gmail ${email_address}")

    else:
        ic('unknown folder type', ctx.email_archive_type, 'exiting')

    update_notmuch_db(email_address=email_address,
                      email_archive_folder=ctx.email_archive_folder,
                      gpgmaildir=ctx.gpgmaildir,
                      notmuch_config_file=ctx.notmuch_config_file,
                      notmuch_config_folder=ctx.notmuch_config_folder)

    update_notmuch_address_db(email_address=email_address,
                              email_archive_folder=ctx.email_archive_folder,
                              gpgmaildir=ctx.gpgmaildir,
                              notmuch_config_file=ctx.notmuch_config_file,
                              notmuch_config_folder=ctx.notmuch_config_folder)


@client.command()
@click.argument("email_address", nargs=1)
@click.pass_context
def download(ctx, email_address):
    '''rsync new mail to encrypted maildir'''
    ic()
    ctx = ctx.invoke(build_paths, email_address=email_address)
    check_noupdate_list(email_address=email_address)

    if ctx.email_archive_type == "gpgMaildir":
        ctx.invoke(warm_up_gpg)
        rsync_mail(email_address=email_address,
                   gpgMaildir_archive_folder=ctx.gpgMaildir_archive_folder)

    else:
        ic('Unsupported:', ctx.email_archive_type, 'Exiting.')
        sys.exit(1)


@client.command()
@click.argument("email_address", nargs=1)
@click.pass_context
def address_db_build(ctx, email_address):
    '''build address database for use with address_query'''
    ic()
    ctx = ctx.invoke(build_paths, email_address=email_address)
    update_notmuch_address_db_build(email_address=email_address,
                                    email_archive_folder=ctx.email_archive_folder,
                                    gpgmaildir=ctx.gpgmaildir,
                                    notmuch_config_file=ctx.notmuch_config_file,
                                    notmuch_config_folder=ctx.notmuch_config_folder)


@client.command()
@click.argument("email_address", nargs=1)
@click.argument("query", type=str)
@click.pass_context
def afew_query(ctx, email_address, query):
    '''execute arbitrary afew query'''
    ic()
    ctx = ctx.invoke(build_paths, email_address=email_address)
    eprint(query)
    run_notmuch(mode="query_afew",
                email_address=email_address,
                query=query,
                email_archive_folder=ctx.email_archive_folder,
                gpgmaildir=ctx.gpgmaildir,
                notmuch_config_file=ctx.notmuch_config_file,
                notmuch_config_folder=ctx.notmuch_config_folder)


@client.command()
@click.argument("email_address", nargs=1)
@click.argument("query", type=str)
@click.pass_context
def notmuch_query(ctx, email_address, query):
    '''execute arbitrary notmuch query notmuch search --output=files "thread:000000000003c194"'''
    ic()
    ctx = ctx.invoke(build_paths, email_address=email_address)
    eprint(query)
    run_notmuch(mode="query_notmuch",
                email_address=email_address,
                query=query,
                email_archive_folder=ctx.email_archive_folder,
                gpgmaildir=ctx.gpgmaildir,
                notmuch_config_file=ctx.notmuch_config_file,
                notmuch_config_folder=ctx.notmuch_config_folder)


@client.command()
@click.argument("email_address", nargs=1)
@click.pass_context
def show_message_counts(ctx, email_address):
    ctx = ctx.invoke(build_paths, email_address=email_address)
    print(get_maildir_file_counts(gpgmaildir=ctx.gpgmaildir, maildir=ctx.maildir))


@client.command()
def warm_up_gpg():
    '''make sure gpg is working'''
    ic()
    # due to https://bugs.g10code.com/gnupg/issue1190 first get gpg-agent warmed up by decrypting a test message.
    decrypt_test = 0

    while decrypt_test != 1:
        ic('generating gpg test string')
        test_string = short_random_string()
        ic('warm_up_gpg test_string:', test_string)

        command = "gpg --yes --trust-model always --throw-keyids --encrypt -o - | gpg --decrypt"
        gpg_cmd_proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        ic('writing test_string to gpg_cmd_proc and reading output')
        gpg_cmd_proc_output_stdout, gpg_cmd_proc_output_stderr = gpg_cmd_proc.communicate(test_string)
        #ic(gpg_cmd_proc_output_stdout)
        gpg_cmd_proc_output_stdout_decoded = gpg_cmd_proc_output_stdout.decode('utf-8')
        for line in gpg_cmd_proc_output_stdout_decoded.split('\n'):
            ic('STDOUT:', line)

        ic('gpg_cmd_proc_output_stderr:')
        gpg_cmd_proc_output_stderr_decoded = gpg_cmd_proc_output_stderr.decode('utf-8')
        for line in gpg_cmd_proc_output_stderr_decoded.split('\n'):
            ic('STDERR:', line)

        ic(gpg_cmd_proc.returncode)

        if gpg_cmd_proc.returncode != 0:
            ic('warm_up_gpg did not return 0, exiting')
            sys.exit(1)

        if test_string not in gpg_cmd_proc_output_stdout:
            ic('test_string:', test_string, 'is not in', gpg_cmd_proc_output_stdout, 'Exiting.')
            sys.exit(1)
        else:
            ic('found test string in gpg_cmd_proc_output_stdout, gpg is working')
            decrypt_test = 1


if __name__ == '__main__':
    client()

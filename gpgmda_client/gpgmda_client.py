#!/usr/bin/env python3
# -*- coding: utf8 -*-

# todo: locking to prevent multiple instances of mail_update

import click
import sys
import os
import time
import subprocess
import shutil
import glob

from multiprocessing import Process     #https://docs.python.org/3/library/multiprocessing.html
from multiprocessing import Pool
from multiprocessing import cpu_count
from kcl.fileops import empty_file
from kcl.fileops import file_exists
from kcl.dirops import path_is_dir
from kcl.dirops import check_or_create_dir
from kcl.dirops import count_files
from kcl.dirops import list_files
from kcl.printops import eprint
from kcl.printops import ceprint

global debug
debug = False


def check_for_notmuch_database(email_archive_folder):
    notmuch_database_folder = email_archive_folder + "/_Maildirs/.notmuch/xapian"
    if not os.path.isdir(notmuch_database_folder):
        eprint('''Error: notmuch has not created the xapian database yet. Run \"mail_update user@domain.com --update\" first. Exiting.''')
        os._exit(1)


def rsync_mail(email_address, gpgMaildir_archive_folder):
    load_ssh_key(email_address=email_address)
    eprint("running rsync")
    #rsync_p = \
        #subprocess.Popen([b'rsync', b'--ignore-existing', b'--size-only', b'-t', b'--whole-file', b'--copy-links', b'--checksum', b'--stats', b'-i', b'-r', b'-vv', email_address + b':gpgMaildir', gpgMaildir_archive_folder + b'/'], stdout=subprocess.PIPE)
    rsync_p = \
        subprocess.Popen(['rsync', '--ignore-existing', '--size-only', '-t', '--whole-file', '--copy-links', '--stats', '-i', '-r', '-vv', email_address + ':gpgMaildir', gpgMaildir_archive_folder + '/'], stdout=subprocess.PIPE)
    rsync_p_output = rsync_p.communicate()
    for line in rsync_p_output[0].split(b'\n'):
#       eprint(line.decode('utf-8'))
        if b'exists' not in line:
            eprint(line)

    eprint("rsync_p.returncode:", rsync_p.returncode)
    if rsync_p.returncode != 0:
        eprint("rsync did not return 0, exiting")
#        os._exit(1)

    rsync_logfile = "/dev/shm/.gpgmda_rsync_last_new_mail_" + email_address
    with open(rsync_logfile, 'wb') as rsync_logfile_handle:
        rsync_logfile_handle.write(rsync_p_output[0])
        ceprint("wrote rsync_logfile:", rsync_logfile)


def run_notmuch(mode, email_address, email_archive_folder, gpgmaildir, query, debug=False):
    yesall = False

    notmuch_config_folder = email_archive_folder + "/_notmuch_config"
    check_or_create_dir(notmuch_config_folder)

    notmuch_config_file = notmuch_config_folder + "/.notmuch_config"
    make_notmuch_config(email_address=email_address, email_archive_folder=email_archive_folder)

    if mode == "update_notmuch_db":
        current_env = os.environ.copy()
        current_env["NOTMUCH_CONFIG"] = notmuch_config_file
        notmuch_p = subprocess.Popen([b'notmuch', b'new'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, env=current_env)
        eprint(notmuch_p.args)
        notmuch_p_output = notmuch_p.communicate()

        eprint("notmuch_p_output:")
        eprint(notmuch_p_output)

        eprint("notmuch_p_output[0]:")
        for line in notmuch_p_output[0].split(b'\n'):
            eprint(line.decode('utf-8'))

        eprint("notmuch_p_output[1]:")
        for line in notmuch_p_output[1].split(b'\n'):
            eprint(line.decode('utf-8'))
            if b"Note: Ignoring non-mail file:" in line:
                non_mail_file = line.split(b" ")[-1]
                eprint("found file that gmime does not like:", non_mail_file)
                random_id = non_mail_file[-40:]
                eprint("random_id:", random_id)
                maildir_subfolder = non_mail_file.split(b'/')[-2]
                eprint("maildir_subfolder:", maildir_subfolder)
                encrypted_file = gpgmaildir + b'/' + maildir_subfolder + b'/' + random_id
                eprint("encrypted_file:", encrypted_file)
                eprint("head -c 500:")
                command = b"head -c 500 " + non_mail_file
                os.system(command)
                if not yesall:
                    eprint("running nano")
                    command = b"nano " + non_mail_file
                    os.system(command)

                    delete_message_answer = input("Would you like to move this message locally to the ~/.gpgmda/non-mail folder and delete it on the server? (yes/no/skipall/yesall): ")

                    if delete_message_answer.lower() == "yesall":
                        yesall = True
                    if delete_message_answer.lower() == "skipall":
                        break
                else:
                    delete_message_answer = 'yes'

                if delete_message_answer.lower() == "yes":
                    non_mail_path = b'~/.gpgmda/non-mail'

                    os.path.sep = b'/'      #py3: paths _are_ bytes. glob.glob(b'/home') does it right
                    os.path.altsep = b'/'

                    os.makedirs(os.path.expanduser(non_mail_path), exist_ok=True)

                    eprint("Processing files for local move and delete:")

                    eprint(non_mail_file)
                    shutil.move(non_mail_file, os.path.expanduser(non_mail_path))

                    eprint(encrypted_file)
                    shutil.move(encrypted_file, os.path.expanduser(non_mail_path))

                    if maildir_subfolder == b".sent":
                        target_file = b"/home/sentuser/gpgMaildir/new/" + random_id
                        command = b"ssh root@v6y.net rm -v " + target_file
                        eprint(command)
                        os.system(command)

                    elif maildir_subfolder == b"new":
                        target_file = b"/home/user/gpgMaildir/new/" + random_id
                        command = b"ssh root@v6y.net rm -v " + target_file    #todo use ~/.gpgmda/config
                        eprint(command)
                        os.system(command)

                    else:
                        eprint("unknown exception, exiting")
                        os._exit(1)

        eprint("notmuch_p.returncode:", notmuch_p.returncode)
        if notmuch_p.returncode != 0:
            eprint("notmuch new did not return 0, exiting")
            os._exit(1)

    elif mode == "query_notmuch":
        check_for_notmuch_database(email_archive_folder=email_archive_folder)
        command = "NOTMUCH_CONFIG=" + notmuch_config_file + " notmuch " + query
        eprint("command:", command)
        return_code = os.system(command)
        if return_code != 0:
            eprint("\"notmuch " + query + "\" returned nonzero, exiting")
            os._exit(1)

    elif mode == "query_afew":
        check_for_notmuch_database(email_archive_folder=email_archive_folder)
        command = "afew" + " --notmuch-config=" + notmuch_config_file + " " + query
        eprint("command:", command)
        return_code = os.system(command)
        if return_code != 0:
            eprint("\"notmuch " + query + "\" returned nonzero, exiting")
            os._exit(1)

    elif mode == "query_address_db":
        check_for_notmuch_database(email_archive_folder=email_archive_folder)
        command = "XDG_CONFIG_HOME=" + notmuch_config_folder + " NOTMUCH_CONFIG=" + notmuch_config_file + " " + "nottoomuch-addresses.sh " + query
        return_code = os.system(command)
        if return_code != 0:
            eprint("\"nottoomuch-addresses.sh\" returned nonzero, exiting")
            os._exit(1)

    elif mode == "build_address_db":
        check_for_notmuch_database(email_archive_folder=email_archive_folder)
        command = "XDG_CONFIG_HOME=" + notmuch_config_folder + " NOTMUCH_CONFIG=" + notmuch_config_file + " " + "nottoomuch-addresses.sh --update --rebuild"
        return_code = os.system(command)
        if return_code != 0:
            eprint("\"nottoomuch-addresses.sh\" returned nonzero, exiting")
            os._exit(1)

    elif mode == "update_address_db":
        check_for_notmuch_database(email_archive_folder=email_archive_folder)
        command = "XDG_CONFIG_HOME=" + notmuch_config_folder + " NOTMUCH_CONFIG=" + notmuch_config_file + " " + "nottoomuch-addresses.sh --update"
        return_code = os.system(command)
        if return_code != 0:
            eprint("\"nottoomuch-addresses.sh\" returned nonzero, exiting")
            os._exit(1)

    else:
        eprint("invalid mode", mode, "exiting.")
        os._exit(1)


def make_notmuch_config(email_address, email_archive_folder):
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
synchronize_flags = false
"""
    notmuch_config_folder = '/'.join([email_archive_folder, "_notmuch_config"])
    check_or_create_dir(notmuch_config_folder)
    notmuch_config_file_location = '/'.join([notmuch_config_folder, ".notmuch_config"])
    if debug:
        eprint("writing notmuch config to:", notmuch_config_file_location)
    notmuch_config_file_handle = open(notmuch_config_file_location, "w")
    notmuch_config_file_handle.write(notmuch_config)
    notmuch_config_file_handle.close()


def move_terminal_text_up_one_page():
    eprint("moving terminal text up one page")
    tput_p = subprocess.Popen(['tput', 'lines'], stdout=subprocess.PIPE)
    tput_p_output = tput_p.communicate()
    tput_p_output = tput_p_output[0].decode('utf8').strip()

    for line in range(int(tput_p_output)):
        print('', file=sys.stderr)


def start_alot(email_address, email_archive_folder):
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
    eprint("starting alot",)
    os.system(' '.join(['alot', '--version']))
    move_terminal_text_up_one_page()        # so alot does not overwrite the last messages on the terminal
    #alot_p = os.system(b' '.join([b'/home/cfg/python/debugging/pudb2.7', b'/usr/bin/alot', b'-C', b'256', b'--debug-level=debug', b'--logfile=/dev/shm/__alot_log', b'--notmuch-config', notmuch_config_folder + b'/.notmuch_config', b'--mailindex-path', email_archive_folder + b'/_Maildirs', b'-c', b'/dev/shm/__alot_config_' + email_address]))
    alot_p = os.system(' '.join(['/usr/bin/alot', '-C', '256', '--debug-level=debug', '--logfile=/dev/shm/__alot_log', '--notmuch-config', notmuch_config_folder + '/.notmuch_config', '--mailindex-path', email_archive_folder + '/_Maildirs', '-c', '/dev/shm/__alot_config_' + email_address]))


def load_ssh_key(email_address):
    eprint("load_ssh_key(%s)" % email_address)
    if 'gmail' in email_address:
        return

    ssh_key = '/home/user/.ssh/id_rsa__' + email_address   #todo use ~/.gpgmda/config

    loaded_ssh_keys_p = subprocess.Popen(['ssh-add', '-l'], stdout=subprocess.PIPE)
    loaded_ssh_keys_p_output = loaded_ssh_keys_p.communicate()[0].strip().decode('UTF8')
    loaded_ssh_key_list = loaded_ssh_keys_p_output.split('\n')

    eprint("ssh-add -l output:")
    for line in loaded_ssh_key_list:
        eprint(line)

    eprint("looking for key:", ssh_key)
    found_key = 0
    for key in loaded_ssh_key_list:
        if ssh_key in key:
            found_key = 1
            break

    if found_key != 1:
        ssh_add_p = subprocess.Popen(['ssh-add', ssh_key])
        ssh_add_p_output = ssh_add_p.communicate()
        if ssh_add_p.returncode != 0:
            eprint("something went wrong adding the ssh_key, exiting")
            os._exit(1)


def short_random_string():
    command = ["gpg2", "--gen-random", "--armor", "1", "100"]
    cmd_proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=False)
    cmd_output = cmd_proc.stdout.read().strip() #get rid of newline
    return cmd_output


def get_maildir_file_counts(gpgmaildir, maildir):
    files_in_gpgmaildir = count_files(gpgmaildir)
    files_in_maildir = count_files(maildir)
    return {'files_in_gpgmaildir': files_in_gpgmaildir, "files_in_maildir": files_in_maildir}


def parse_rsync_log_to_list(email_address, gpgMaildir_archive_folder):
    rsync_log = b'/dev/shm/.gpgmda_rsync_last_new_mail_' + email_address
    with open(rsync_log, 'rb') as fh:
        rsync_log = fh.readlines()

    full_path_list = []
    for line in rsync_log:
        line = line.strip() #remove newlines
        if b'exists' not in line:
            if b'gpgMaildir' in line:
                if line.startswith(b'>f'):
                    new_gpgmda_file_path = gpgMaildir_archive_folder + b'/' + line.split(b' ')[1]
                    print("new_gpgmda_file_path:", new_gpgmda_file_path)
                    full_path_list.append(new_gpgmda_file_path)

    return full_path_list


def decrypt_list_of_messages(message_list, email_address, delete_badmail, skip_badmail, move_badmail):
    message_list = filter(None, message_list)   #remove empty items
    process_count = cpu_count()
    p = Pool(process_count)
    eprint("message_list:", message_list)
    for gpgfile in message_list:    #useful for debugging
       decrypt_message(email_address=email_address, gpgfile=gpgfile, delete_badmail=delete_badmail, skip_badmail=skip_badmail, move_badmail=move_badmail)


def move_to_badmail(gpgfile):
    badmail_path = os.path.expanduser(b'~/.gpgmda/badmail')
    #print("type(badmail_path):", type(badmail_path))
    os.makedirs(os.path.expanduser(badmail_path), exist_ok=True)
    eprint("Processing files for local move and delete gpgfile:", gpgfile)

    os.path.sep = b'/'      #py3: paths _are_ bytes. glob.glob(b'/home') does it right
    os.path.altsep = b'/'
    shutil.move(gpgfile, badmail_path)


def decrypt_message(email_address, gpgfile, delete_badmail, skip_badmail, move_badmail, maildir, stdout=False):
    if not isinstance(gpgfile, bytes):
        eprint("decrypt_message() takes the gpgfile as bytes")
        os._exit(1)
    eprint("\ndecrypt_msg() gpgfile:", gpgfile)
    if b'@' not in email_address:
        eprint("Invalid email address:", email_address, ", exiting.")
        os._exit(1)

    if not file_exists(gpgfile):
        eprint(gpgfile, "No such file or directory. Exiting.")
        os._exit(1)

    if empty_file(gpgfile):
        eprint("FOUND ZERO LENGTH FILE, EXITING. CHECK THE MAILSERVER LOGS (and manually delete it):", gpgfile)
        os._exit(1)

    gpgfile_name = os.path.basename(gpgfile)
    eprint("\ngpgfile_name:", gpgfile_name)

    gpgfile_folder_path = os.path.dirname(gpgfile)
    eprint("gpgfile_folder_path:", gpgfile_folder_path)

    maildir_subfolder = os.path.basename(gpgfile_folder_path)
    eprint("maildir_subfolder:", maildir_subfolder)
    if not path_is_dir(maildir):
        eprint("maildir:", maildir, "does not exist. Exiting.")
        os._exit(1)

    #file_previously_decrypted = 0
    glob_pattern = maildir + b'/' + maildir_subfolder + b'/*.' + gpgfile_name
    eprint("glob_pattern:", glob_pattern)
    result = glob.glob(glob_pattern)

    if len(result) > 1:
        eprint("ERROR: This shouldnt happen. More than one result was returned for glob_pattern:", glob_pattern, ": ", result)
        os._exit(1)

    if stdout is False:
        if len(result) == 1:
            result = result[0]
            eprint("skipping existing file:", result)
            return True

    eprint("decrypting:", gpgfile)
    if stdout:
#       command = "gpg2 -o - --decrypt " + gpgfile + " | tar --transform=s/$/." + gpgfile_name + "/ -xvf -" # hides the tar header
        command = "gpg2 -o - --decrypt " + gpgfile
        eprint("decrypt_msg() command:", command)
        return_code = os.system(command)
        eprint("return_code:", return_code)

    else:
        gpg_command = ["gpg2", "-o", "-", "--decrypt", gpgfile]
        tar_command = ["tar", "--transform=s/$/." + gpgfile_name + "/", "-C", maildir + '/' + maildir_subfolder, "-xvf", "-"]
        gpg_cmd_proc = subprocess.Popen(gpg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        eprint("executing gpg_command:", gpg_command)
        gpg_cmd_proc_output_stdout, gpg_cmd_proc_output_stderr = gpg_cmd_proc.communicate()

        if debug:
            eprint("gpg_cmd_proc_output_stdout:")
            gpg_cmd_proc_output_stdout_decoded = gpg_cmd_proc_output_stdout.decode('utf-8')
            for line in gpg_cmd_proc_output_stdout_decoded.split('\n'):
                eprint("STDOUT:", line)

        eprint("gpg_cmd_proc_output_stderr:")
        gpg_cmd_proc_output_stderr_decoded = gpg_cmd_proc_output_stderr.decode('utf-8')
        for line in gpg_cmd_proc_output_stderr_decoded.split('\n'):
            eprint("STDERR:", line)

        eprint("gpg_cmd_proc.returncode:", gpg_cmd_proc.returncode)
        if gpg_cmd_proc.returncode != 0:
            eprint("gpg2 did not return 0")
            return False

        if len(gpg_cmd_proc_output_stdout) > 0:
            tar_cmd_proc = subprocess.Popen(tar_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
            eprint("executing tar_command:", tar_command)
            tar_cmd_proc_output_stdout, tar_cmd_proc_output_stderr = tar_cmd_proc.communicate(gpg_cmd_proc_output_stdout)
            eprint("tar_cmd_proc_output_stdout:")
            tar_cmd_proc_output_stdout_decoded = tar_cmd_proc_output_stdout.decode('utf-8')
            for line in tar_cmd_proc_output_stdout_decoded.split('\n'):
                eprint("STDOUT:", line)

            eprint("tar_cmd_proc_output_stderr:")
            tar_cmd_proc_output_stderr_decoded = tar_cmd_proc_output_stderr.decode('utf-8')
            for line in tar_cmd_proc_output_stderr_decoded.split('\n'):
                eprint("STDERR:", line)

            eprint("tar_cmd_proc.returncode:", tar_cmd_proc.returncode)

            if tar_cmd_proc.returncode != 0:
                eprint("tar did not return 0")
                return False
        else:
            eprint("gpg did not produce any stdout, tar skipped file:", gpgfile)
            eprint("looking into:", gpgfile, "further...")
            os.system(b'/bin/ls -al ' + gpgfile)
            stats = os.stat(gpgfile)
            if stats.st_size <= 1141:
                eprint("this is likely an empty gpg encrypted file")

            if move_badmail:
                move_to_badmail(gpgfile)

            elif not skip_badmail:
                if delete_badmail is False:
                    delete_message_answer = input("Would you like to move this message locally to the ~/.gpgmda/badmail folder and delete it off the server? (yes/no/yesall/skipall/moveall): ")
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
                    random_id = gpgfile.split(b'/')[-1]

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
                        eprint("unknown exception, exiting")
                        os._exit(1)
            return False
    return True


def gpgmaildir_to_maildir(email_address, delete_badmail, skip_badmail, move_badmail, gpgMaildir_archive_folder, gpgmaildir, maildir):
    # todo add locking
    eprint("gpgmda_to_maildir using gpgMaildir_archive_folder:", gpgMaildir_archive_folder)
    eprint("Checking for default-recipient in ~/.gnupg/gpg.conf")
    command = "grep \"^default-recipient\" ~/.gnupg/gpg.conf"
    grep_exit_code = os.system(command)
    if grep_exit_code != 0:
        eprint("error: default-recipient is not defined in ~/.gnupg/gpg.conf. Exiting.")
        os._exit(1)

    rsync_last_new_mail_file = b'/dev/shm/.gpgmda_rsync_last_new_mail_' + email_address
    eprint("checking to see if", rsync_last_new_mail_file, "exists and is greater than 0 bytes")
    rsync_files_transferred = 0
    if file_exists(rsync_last_new_mail_file):
        with open(rsync_last_new_mail_file, 'r') as fh:
            for line in fh.readlines():
                if 'Number of regular files transferred:' in line:
                    eprint(line)
                    rsync_files_transferred = line.split(':')[1].strip()
                    eprint("rsync_files_transferred:", rsync_files_transferred)
                    break
        if rsync_files_transferred == 0:
            eprint("rsync transferred 0 files, skipping decrypt")

        else:
            rsync_list = parse_rsync_log_to_list(email_address=email_address)
            eprint("rsync_list:", rsync_list)
            decrypt_list_of_messages(message_list=rsync_list, email_address=email_address, delete_badmail=delete_badmail, skip_badmail=skip_badmail, move_badmail=move_badmail)

    else:
        eprint(rsync_last_new_mail_file, "does not exist or is 0 bytes")

    eprint("\nchecking if the message counts in the maildir and the gpgmaildir match")
    maildir_counts_dict = get_maildir_file_counts(gpgmaildir=gpgmaildir, maildir=maildir)
    eprint("maildir_counts_dict:", maildir_counts_dict)
    maildir_file_count = maildir_counts_dict['files_in_maildir']
    gpgmaildir_file_count = maildir_counts_dict['files_in_gpgmaildir']
    if gpgmaildir_file_count > maildir_file_count:
        eprint("files_in_gpgmaildir > files_in_maildir:", gpgmaildir_file_count, '>', maildir_file_count)
        eprint("locating un-decrypted files")
        files_in_gpgmaildir = list_files(gpgmaildir=gpgmaildir)
        files_in_maildir = list_files(maildir=maildir)
        eprint("len(files_in_gpgmaildir):", len(files_in_gpgmaildir))
        eprint("len(files_in_maildir):", len(files_in_maildir))
        full_maildir_string = "\n".join(files_in_maildir)

        for gpgfile in files_in_gpgmaildir:
            #subfolder = file.split(b'/')[-2]
            gpghash = gpgfile.split(b'/')[-1]
            if gpghash not in full_maildir_string:
                eprint("\n\nfound gpgfile that has not been decrypted yet:", gpgfile)
                decrypt_message(email_address=email_address, gpgfile=gpgfile, delete_badmail=delete_badmail, skip_badmail=skip_badmail, move_badmail=move_badmail, maildir=maildir, stdout=False)
    return


def search_list_of_strings_for_substring(list, substring):
    item_found = ''
    for item in list:
        try:
            if substring in item:
                item_found = item
                break
        except TypeError:
            pass
    return item_found


def update_notmuch_db(email_address, email_archive_folder, gpgmaildir):
    run_notmuch("update_notmuch_db", email_address=email_address, email_archive_folder=email_archive_folder, gpgmaildir=gpgmaildir, query=False)


def update_notmuch_address_db(email_address, email_archive_folder, gpgmaildir):
    run_notmuch("update_address_db", email_address=email_address, email_archive_folder=email_archive_folder, gpgmaildir=gpgmaildir, query=False)


def update_notmuch_address_db_build(email_address, email_archive_folder, gpgmaildir):
    run_notmuch("build_address_db", email_address=email_address, email_archive_folder=email_archive_folder, gpgmaildir=gpgmaildir, query=False)


def query_afew(email_address, query, email_archive_folder, gpgmaildir):
    run_notmuch("query_afew", email_address=email_address, query=query, email_archive_folder=email_archive_folder, gpgmaildir=gpgmaildir)


def query_notmuch_address_db(email_address, query, email_archive_folder, gpgmaildir):
    run_notmuch("query_address_db", email_address=email_address, query=query, email_archive_folder=email_archive_folder, gpgmaildir=gpgmaildir)


def check_noupdate_list(email_address):
    noupdate_list = open(gpgmda_config_folder + "/.noupdate", 'r').readlines() #todo move config to ~/.gpgmda
    for item in noupdate_list:
        if email_address in item:
            eprint(email_address + " is listed in .noupdate, exiting")
            os._exit(1)


@click.group()
@click.option("--verbose", is_flag=True)
@click.option("--delete-badmail", help="", is_flag=True)
@click.option("--skip-badmail", help="", is_flag=True)
@click.option("--move-badmail", help="", is_flag=True)
@click.pass_context
def client(ctx, verbose, delete_badmail, move_badmail, skip_badmail):
    start_time = time.time()
    if verbose:
        eprint(time.asctime())

    global gpgmda_config_folder
    gpgmda_config_folder = os.path.expanduser('~/.gpgmda/')

    if verbose:
        eprint(time.asctime())
        eprint('TOTAL TIME IN MINUTES:',)
        eprint((time.time() - start_time) / 60.0)


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
    return ctx


@client.command()
@click.argument("email_address", nargs=1)
@click.argument("query", type=str)
@click.pass_context
def address_query(ctx, email_address, query):
    '''search for address string'''
    ctx = ctx.invoke(build_paths, email_address=email_address)
    query_notmuch_address_db(email_address=email_address, query=query, gpgmaildir=ctx.gpgmaildir, email_archive_folder=ctx.email_archive_folder)


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
@click.pass_context
def decrypt(ctx, email_address):
    '''decrypt new mail in encrypted maildir to unencrypted maildir'''
    ctx = ctx.invoke(build_paths, email_address=email_address)
    check_noupdate_list(email_address=email_address)

    if ctx.email_archive_type == "gpgMaildir":
        ctx.invoke(warm_up_gpg)
        gpgmaildir_to_maildir(email_address=email_address, gpgMaildir_archive_folde=ctx.gpgMaildir_archive_folder, gpgmaildir=ctx.gpgmaildir, maildir=ctx.maildir)

    else:
        eprint("Unsupported email_archive_type:", ctx.email_archive_type, "Exiting.")
        os._exit(1)


@client.command()
@click.argument("email_address", nargs=1)
@click.pass_context
def update_notmuch(ctx, email_address):
    '''update notmuch with new mail from (normal, unencrypted) maildir'''
    ctx = ctx.invoke(build_paths, email_address=email_address)
    check_noupdate_list(email_address=email_address)

    if ctx.email_archive_type == "gpgMaildir":
        ctx.invoke(warm_up_gpg)

    elif ctx.email_archive_type == "getmail":
        eprint('gpgmda_program_folder/getmail_gmail "${email_address}" || exit 1')
        eprint("todo, call /getmail_gmail ${email_address}")

    else:
        eprint("unknown folder type", ctx.email_archive_type, ", exiting")


    update_notmuch_db(email_address=email_address, email_archive_folder=ctx.email_archive_folder, gpgmaildir=ctx.gpgmaildir)
    update_notmuch_address_db(email_address=email_address, email_archive_folder=ctx.email_archive_folder, gpgmaildir=ctx.gpgmaildir)


@client.command()
@click.argument("email_address", nargs=1)
@click.pass_context
def download(ctx, email_address):
    '''rsync new mail to encrypted maildir'''
    ctx = ctx.invoke(build_paths, email_address=email_address)
    check_noupdate_list(email_address=email_address)

    if ctx.email_archive_type == "gpgMaildir":
        ctx.invoke(warm_up_gpg)
        rsync_mail(email_address=email_address, gpgMaildir_archive_folder=ctx.gpgMaildir_archive_folder)

    else:
        eprint("Unsupported email_archive_type:", ctx.email_archive_type, "Exiting.")
        os._exit(1)


@client.command()
@click.argument("email_address", nargs=1)
@click.pass_context
def address_db_build(ctx, email_address):
    '''build address database for use with address_query'''
    ctx = ctx.invoke(build_paths, email_address=email_address)
    update_notmuch_address_db_build(email_address=email_address, email_archive_folder=ctx.email_archive_folder, gpgmaildir=ctx.gpgmaildir)


@client.command()
@click.argument("email_address", nargs=1)
@click.argument("query", type=str)
@click.pass_context
def afew_query(ctx, email_address, query):
    '''execute arbitrary afew query'''
    ctx = ctx.invoke(build_paths, email_address=email_address)
    eprint(query)
    query_afew(email_address=email_address, query=query, gpgmaildir=ctx.gpgmaildir)


@client.command()
@click.argument("email_address", nargs=1)
@click.argument("query", type=str)
@click.pass_context
def notmuch_query(ctx, email_address, query):
    '''execute arbitrary notmuch query'''
    ctx = ctx.invoke(build_paths, email_address=email_address)
    eprint(query)
    run_notmuch("query_notmuch", email_address=email_address, query=query, email_archive_folder=ctx.email_archive_folder, gpgmaildir=ctx.gpgmaildir)


@client.command()
@click.argument("email_address", nargs=1)
@click.pass_context
def show_message_counts(ctx, email_address):
    ctx = ctx.invoke(build_paths, email_address=email_address)
    print(get_maildir_file_counts(gpgmaildir=ctx.gpgmaildir, maildir=ctx.maildir))


@client.command()
def warm_up_gpg():
    '''make sure gpg is working'''
    # due to https://bugs.g10code.com/gnupg/issue1190 first get gpg-agent warmed up by decrypting a test message.
    decrypt_test = 0

    while decrypt_test != 1:
        eprint("generating gpg test string")
        test_string = short_random_string()
        eprint("warm_up_gpg test_string:", test_string)

        command = "gpg --yes --trust-model always --throw-keyids --encrypt -o - | gpg --decrypt"
        gpg_cmd_proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        eprint("writing test_string to gpg_cmd_proc and reading output")
        gpg_cmd_proc_output_stdout, gpg_cmd_proc_output_stderr = gpg_cmd_proc.communicate(test_string)
        eprint("gpg_cmd_proct_output_stdout:", gpg_cmd_proc_output_stdout)
        eprint("gpg_cmd_proct_output_stdout:")
        gpg_cmd_proc_output_stdout_decoded = gpg_cmd_proc_output_stdout.decode('utf-8')
        for line in gpg_cmd_proc_output_stdout_decoded.split('\n'):
            eprint("STDOUT:", line)

        eprint("gpg_cmd_proc_output_stderr:")
        gpg_cmd_proc_output_stderr_decoded = gpg_cmd_proc_output_stderr.decode('utf-8')
        for line in gpg_cmd_proc_output_stderr_decoded.split('\n'):
            eprint("STDERR:", line)

        eprint("gpg_cmd_proc.returncode:", gpg_cmd_proc.returncode)

        if gpg_cmd_proc.returncode != 0:
            eprint("warm_up_gpg did not return 0, exiting")
            os._exit(1)

        if test_string not in gpg_cmd_proc_output_stdout:
            eprint("test_string:", test_string, "is not in gpg_cmd_proc_output_stdout:", gpg_cmd_proc_output_stdout, "Exiting.")
            os._exit(1)
        else:
            eprint("found test string in gpg_cmd_proc_output_stdout, gpg is working")
            decrypt_test = 1


if __name__ == '__main__':
    client()

#!/usr/bin/env python3
# -*- coding: utf8 -*-

# pylint: disable=missing-docstring               # [C0111] docstrings are always outdated and wrong
# pylint: disable=fixme                           # [W0511] todo is encouraged
# pylint: disable=line-too-long                   # [C0301]
# pylint: disable=too-many-instance-attributes    # [R0902]
# pylint: disable=too-many-lines                  # [C0302] too many lines in module
# pylint: disable=invalid-name                    # [C0103] single letter var names, name too descriptive
# pylint: disable=too-many-return-statements      # [R0911]
# pylint: disable=too-many-branches               # [R0912]
# pylint: disable=too-many-statements             # [R0915]
# pylint: disable=too-many-arguments              # [R0913]
# pylint: disable=too-many-nested-blocks          # [R1702]
# pylint: disable=too-many-locals                 # [R0914]
# pylint: disable=too-few-public-methods          # [R0903]
# pylint: disable=no-member                       # [E1101] no member for base
# pylint: disable=attribute-defined-outside-init  # [W0201]
# pylint: disable=too-many-boolean-expressions    # [R0916] in if statement
from __future__ import annotations

import glob
import logging
import os
import subprocess
import sys
import time
from math import inf
from pathlib import Path

import click
import sh
from asserttool import ic
from click_auto_help import AHGroup
from clicktool import click_add_options
from clicktool import click_global_options
from clicktool import tv
from eprint import eprint
from getdents import files
from pathtool import check_or_create_dir
from pathtool import empty_file
from pathtool import path_exists
from pathtool import path_is_dir

logging.basicConfig(level=logging.INFO)
# from multiprocessing import Process     #https://docs.python.org/3/library/multiprocessing.html
# from multiprocessing import Pool, cpu_count
# todo: locking to prevent multiple instances of mail_update


sh.mv = None  # use busybox
# global NOTMUCH_QUERY_HELP
# NOTMUCH_QUERY_HELP = "notmuch search --output=files 'thread:000000000003c194'"


class EmptyGPGMailFile(ValueError):
    pass


def check_for_notmuch_database(email_archive_folder: Path):
    notmuch_database_folder = email_archive_folder / Path("_Maildirs/.notmuch/xapian")
    if not os.path.isdir(notmuch_database_folder):
        eprint(
            """Error: notmuch has not created the xapian database yet. Run \"mail_update user@domain.com --update\" first. Exiting."""
        )
        sys.exit(1)


def rsync_mail(
    *,
    email_address: str,
    gpgMaildir_archive_folder: Path,
    verbose: bool | int | float,
):
    ic()
    load_ssh_key(
        email_address=email_address,
        verbose=verbose,
    )
    ic("running rsync")
    rsync_p = subprocess.Popen(
        [
            "rsync",
            "--ignore-existing",
            "--size-only",
            "-t",
            "--whole-file",
            "--copy-links",
            "--stats",
            "-i",
            "-r",
            "-vv",
            email_address + ":gpgMaildir",
            gpgMaildir_archive_folder.as_posix() + "/",
        ],
        stdout=subprocess.PIPE,
    )

    rsync_p_output = rsync_p.communicate()

    for line in rsync_p_output[0].split(b"\n"):
        if b"exists" not in line:
            ic(line)

    ic(rsync_p.returncode)
    if rsync_p.returncode != 0:
        ic("rsync did not return 0, exiting")
        sys.exit(1)

    rsync_logfile = "/dev/shm/.gpgmda_rsync_last_new_mail_" + email_address
    with open(rsync_logfile, "wb") as rsync_logfile_handle:
        rsync_logfile_handle.write(rsync_p_output[0])
        ic("wrote rsync_logfile:", rsync_logfile)


def run_notmuch(
    *,
    mode: str,
    email_address: str,
    email_archive_folder: Path,
    gpgmaildir: Path,
    query: None | str,
    notmuch_config_file: Path,
    notmuch_config_folder: Path,
    verbose: bool | int | float,
):

    ic()
    yesall = False

    if mode == "update_notmuch_db":
        current_env = os.environ.copy()
        current_env["NOTMUCH_CONFIG"] = notmuch_config_file.as_posix()

        notmuch_new_command = [
            "notmuch",
            "--config=" + notmuch_config_file.as_posix(),
            "new",
        ]
        ic(notmuch_new_command)
        notmuch_p = subprocess.Popen(
            notmuch_new_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            env=current_env,
        )
        ic(notmuch_p.args)
        notmuch_p_output = notmuch_p.communicate()

        ic("notmuch_p_output:")
        ic(notmuch_p_output)

        ic("len(notmuch_p_output[0]):", len(notmuch_p_output[0]))

        ic("notmuch_p_output[0]:")
        for line in notmuch_p_output[0].split(b"\n"):
            ic(line.decode("utf-8"))

        ic("notmuch_p_output[1]:")
        for line in notmuch_p_output[1].decode("utf8").split("\n"):
            # line = line.decode('utf-8')
            ic(line)
            if "Note: Ignoring non-mail file:" in line:
                non_mail_file = Path(line.split(" ")[-1])
                ic("found file that gmime does not like:", non_mail_file)
                random_id = Path(non_mail_file.as_posix()[-40:])
                ic(random_id)
                # maildir_subfolder = Path(non_mail_file.parent.parent)
                maildir_subfolder_name = Path(non_mail_file.parent).name
                ic(maildir_subfolder_name)
                assert maildir_subfolder_name in ["new", ".sent"]
                encrypted_file = (
                    Path(gpgmaildir) / Path(maildir_subfolder_name) / Path(random_id)
                )
                ic(encrypted_file)
                ic("head -c 500:")
                command = "head -c 500 " + non_mail_file.as_posix()
                os.system(command)
                with open(non_mail_file, "rb") as fh:
                    data = fh.read()
                if data == b"metastable":
                    ic("metastable test message... fixme")

                if not yesall:
                    # ic('running vi')
                    # command = "vi " + non_mail_file
                    # os.system(command)

                    delete_message_answer = input(
                        "Would you like to move this message locally to the ~/.gpgmda/non-mail folder and delete it on the server? (yes/no/skipall/yesall): "
                    )

                    if delete_message_answer.lower() == "yesall":
                        yesall = True
                    if delete_message_answer.lower() == "skipall":
                        break
                else:
                    delete_message_answer = "yes"

                if delete_message_answer.lower() == "yes":
                    non_mail_path = Path("~/.gpgmda/non-mail").expanduser()

                    os.makedirs(non_mail_path, exist_ok=True)

                    ic("Processing files for local move and delete:")

                    ic(non_mail_file)
                    sh.busybox.mv("-vi", non_mail_file, non_mail_path)

                    ic(encrypted_file)
                    sh.busybox.mv("-vi", encrypted_file, non_mail_path)

                    if maildir_subfolder_name == ".sent":
                        target_file = Path("/home/sentuser/gpgMaildir/new/") / random_id
                        command = "ssh root@v6y.net rm -v " + target_file.as_posix()
                        ic(command)
                        os.system(command)

                    elif maildir_subfolder_name == "new":
                        target_file = Path("/home/user/gpgMaildir/new/") / random_id
                        command = (
                            "ssh root@v6y.net rm -v " + target_file.as_posix()
                        )  # todo use ~/.gpgmda/config
                        ic(command)
                        os.system(command)
                    else:
                        eprint(
                            "unknown maildir_subfolder:",
                            maildir_subfolder_name,
                            "exiting",
                        )
                        sys.exit(1)

        ic(notmuch_p.returncode)
        if notmuch_p.returncode != 0:
            eprint("notmuch new did not return 0, exiting")
            sys.exit(1)

    elif mode == "query_notmuch":
        check_for_notmuch_database(email_archive_folder=email_archive_folder)
        assert query
        if query:
            command = (
                "NOTMUCH_CONFIG=" + notmuch_config_file.as_posix() + " notmuch " + query
            )
            ic(command)
            return_code = os.system(command)
            if return_code != 0:
                eprint('"notmuch ' + query + '" returned nonzero, exiting')
                sys.exit(1)

    elif mode == "query_afew":
        assert query
        check_for_notmuch_database(email_archive_folder=email_archive_folder)
        if query:
            command = (
                "afew"
                + " --notmuch-config="
                + notmuch_config_file.as_posix()
                + " "
                + query
            )
            ic(command)
            return_code = os.system(command)
            if return_code != 0:
                eprint('"notmuch ' + query + '" returned nonzero, exiting')
                sys.exit(1)

    elif mode == "query_address_db":
        assert query
        if query:
            check_for_notmuch_database(email_archive_folder=email_archive_folder)
            command = (
                "XDG_CONFIG_HOME="
                + notmuch_config_folder.as_posix()
                + " NOTMUCH_CONFIG="
                + notmuch_config_file.as_posix()
                + " "
                + "nottoomuch-addresses.sh "
                + query
            )
            return_code = os.system(command)
            if return_code != 0:
                eprint('"nottoomuch-addresses.sh" returned nonzero, exiting')
                sys.exit(1)

    elif mode == "build_address_db":
        check_for_notmuch_database(email_archive_folder=email_archive_folder)
        command = (
            "XDG_CONFIG_HOME="
            + notmuch_config_folder.as_posix()
            + " NOTMUCH_CONFIG="
            + notmuch_config_file.as_posix()
            + " "
            + "nottoomuch-addresses.sh --update --rebuild"
        )
        return_code = os.system(command)
        if return_code != 0:
            eprint('"nottoomuch-addresses.sh" returned nonzero, exiting')
            sys.exit(1)

    elif mode == "update_address_db":
        check_for_notmuch_database(email_archive_folder=email_archive_folder)
        command = (
            "XDG_CONFIG_HOME="
            + notmuch_config_folder.as_posix()
            + " NOTMUCH_CONFIG="
            + notmuch_config_file.as_posix()
            + " "
            + "nottoomuch-addresses.sh --update"
        )
        return_code = os.system(command)
        if return_code != 0:
            eprint('"nottoomuch-addresses.sh" returned nonzero, exiting')
            sys.exit(1)

    else:
        ic("invalid", mode, "exiting.")
        sys.exit(1)


def make_notmuch_config(
    *,
    email_address: str,
    email_archive_folder: Path,
    verbose: bool | int | float,
):

    ic()
    username = email_address.split("@")[0]

    notmuch_config = (
        """
[database]
path = """
        + email_archive_folder.as_posix()
        + """/_Maildirs

[user]
name = """
        + username
        + """
primary_email="""
        + email_address
        + """

[new]
tags = unread;inbox;

[maildir]
synchronize_flags = False

[global]
quit_on_last_bclose = True
"""
    )
    notmuch_config_folder = email_archive_folder / Path("_notmuch_config")
    check_or_create_dir(notmuch_config_folder)
    notmuch_config_file_location = notmuch_config_folder / Path(".notmuch_config")
    if verbose:
        ic("writing notmuch config to:", notmuch_config_file_location)
    notmuch_config_file_handle = open(notmuch_config_file_location, "w")
    notmuch_config_file_handle.write(notmuch_config)
    notmuch_config_file_handle.close()


def move_terminal_text_up_one_page():
    ic("moving terminal text up one page")
    tput_p = subprocess.Popen(["tput", "lines"], stdout=subprocess.PIPE)
    tput_p_output = tput_p.communicate()
    tput_p_output = tput_p_output[0].decode("utf8").strip()

    for line in range(int(tput_p_output)):
        print("", file=sys.stderr)


def start_alot(
    *,
    email_address: str,
    email_archive_folder: Path,
    verbose: bool | int | float,
):

    ic()
    check_for_notmuch_database(email_archive_folder=email_archive_folder)
    alot_config = subprocess.Popen(
        ["gpgmda-client-make-alot-config.sh", email_address], stdout=subprocess.PIPE
    ).communicate()
    alot_theme = subprocess.Popen(
        ["gpgmda-client-make-alot-theme.sh"], stdout=subprocess.PIPE
    ).communicate()

    alot_config_f = open("/dev/shm/__alot_config_" + email_address, "w")
    alot_theme_f = open("/dev/shm/__alot_theme_" + email_address, "w")

    alot_config_f.write(alot_config[0].decode("UTF8"))
    alot_theme_f.write(alot_theme[0].decode("UTF8"))

    alot_config_f.close()
    alot_theme_f.close()
    ic(alot_config_f, alot_theme_f)

    notmuch_config_folder = email_archive_folder / Path("_notmuch_config")
    notmuch_config_file = notmuch_config_folder / Path(".notmuch_config")
    maildirs_folder = email_archive_folder / Path("_Maildirs")
    ic("starting alot")
    os.system(" ".join(["alot", "--version"]))
    move_terminal_text_up_one_page()  # so alot does not overwrite the last messages on the terminal
    alot_config_file = Path("/dev/shm/__alot_config_" + email_address)
    ic(alot_config_file, notmuch_config_file)

    alot_command_list = [
        "/usr/bin/alot",
        "-C",
        "256",
        "--logfile=/dev/shm/__alot_log",
        "--notmuch-config",
        notmuch_config_file.as_posix(),
        "--mailindex-path",
        maildirs_folder.as_posix(),
        "-c",
        alot_config_file.as_posix(),
    ]

    if verbose == inf:
        alot_command_list.append("--debug-level=debug")

    # alot_command = ' '.join(['/usr/bin/alot',
    #                         '-C',
    #                         '256',
    #                         '--debug-level=debug',
    #                         '--logfile=/dev/shm/__alot_log',
    #                         '--notmuch-config',
    #                         notmuch_config_file.as_posix(),
    #                         '--mailindex-path',
    #                         maildirs_folder.as_posix(),
    #                         '-c',
    #                         alot_config_file.as_posix()])
    alot_command = " ".join(alot_command_list)

    if verbose:
        ic(alot_command)
    alot_p = os.system(alot_command)

    if verbose:
        ic(alot_p)


def load_ssh_key(email_address: str, verbose):
    ic(f"load_ssh_key({email_address})")
    if "gmail" in email_address:
        return

    ssh_key = "/home/user/.ssh/id_rsa__" + email_address  # todo use ~/.gpgmda/config

    loaded_ssh_keys_p = subprocess.Popen(["ssh-add", "-l"], stdout=subprocess.PIPE)
    loaded_ssh_keys_p_output = loaded_ssh_keys_p.communicate()[0].strip().decode("UTF8")
    loaded_ssh_key_list = loaded_ssh_keys_p_output.split("\n")

    ic("ssh-add -l output:")
    for line in loaded_ssh_key_list:
        ic(line)

    ic("looking for key:", ssh_key)
    found_key = 0
    for key in loaded_ssh_key_list:
        if ssh_key in key:
            found_key = 1
            break

    if found_key != 1:
        ssh_add_p = subprocess.Popen(["ssh-add", ssh_key])
        ssh_add_p_output = ssh_add_p.communicate()
        if ssh_add_p.returncode != 0:
            ic("something went wrong adding the ssh_key, exiting")
            ic(ssh_add_p_output)
            sys.exit(1)


def short_random_string() -> bytes:
    command = ["gpg2", "--gen-random", "--armor", "1", "100"]
    cmd_proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=False)
    cmd_output = cmd_proc.stdout.read().strip()  # get rid of newline
    ic(type(cmd_output), cmd_output)
    return cmd_output


def get_maildir_file_counts(
    *,
    gpgmaildir: Path,
    maildir: Path,
    verbose: bool | int | float,
):
    ic()
    files_in_gpgmaildir = len(
        list(
            files(
                gpgmaildir,
                verbose=verbose,
            )
        )
    )
    files_in_maildir = len(
        list(
            files(
                maildir,
                verbose=verbose,
            )
        )
    )
    return {
        "files_in_gpgmaildir": files_in_gpgmaildir,
        "files_in_maildir": files_in_maildir,
    }


def parse_rsync_log_to_list(
    *,
    email_address: str,
    gpgMaildir_archive_folder: Path,
    verbose: bool | int | float,
):
    ic()
    rsync_log = Path("/dev/shm/.gpgmda_rsync_last_new_mail_" + email_address)
    with open(rsync_log, "r") as fh:
        rsync_log_lines = fh.readlines()

    full_path_list = []
    line = None
    for line in rsync_log_lines:
        line = line.strip()  # remove newlines
        if "exists" not in line:
            if "gpgMaildir" in line:
                if line.startswith(">f"):
                    new_gpgmda_file_path = gpgMaildir_archive_folder / Path(
                        line.split(" ")[1]
                    )
                    ic(new_gpgmda_file_path)
                    full_path_list.append(new_gpgmda_file_path)

    # message_list = []
    # if line:
    #    for path in full_path_list:
    #        assert len(path.as_posix()) > 0
    #        message_list.append(line)

    return full_path_list


def decrypt_list_of_messages(
    *,
    message_list: list,
    email_address: str,
    maildir: Path,
    skip_hashes: list,
    verbose: bool | int | float,
):

    ic()
    assert isinstance(maildir, Path)
    yesall = False
    # ic(message_list)
    ic(len(skip_hashes))
    index = 0
    for index, gpgfile in enumerate(message_list):
        gpghash = gpgfile.name
        if gpghash in skip_hashes:
            if verbose:
                ic(index, "skipping:", gpgfile)
            continue

        print("", file=sys.stderr)
        ic(index, "found gpgfile that has not been decrypted yet:", gpgfile)
        try:
            decrypt_message(
                email_address=email_address,
                gpgfile=gpgfile,
                maildir=maildir,
                verbose=verbose,
            )
        except EmptyGPGMailFile as e:
            ic(e)
            answer = deal_with_badmail(
                gpgfile=gpgfile,
                yesall=yesall,
                verbose=verbose,
            )
            if answer == "yesall":
                yesall = True

    ic("done:", index)


def move_to_badmail(
    *,
    gpgfile: Path,
    verbose: bool | int | float,
):
    ic()
    badmail_path = Path("~/.gpgmda/badmail").expanduser()
    ic(badmail_path)
    os.makedirs(badmail_path, exist_ok=True)
    ic("Processing files for local move and delete gpgfile:", gpgfile)
    sh.busybox.mv("-vi", gpgfile, badmail_path)


def move_badmail_and_delete_off_server(
    *,
    gpgfile: Path,
    verbose: bool | int | float,
):
    if verbose:
        ic(gpgfile)

    assert isinstance(gpgfile, Path)
    maildir_subfolder = gpgfile.parent.name
    ic(maildir_subfolder)
    move_to_badmail(
        gpgfile=gpgfile,
        verbose=verbose,
    )
    random_id = gpgfile.name
    ic(random_id)

    ic(maildir_subfolder)
    if maildir_subfolder == ".sent":
        target_file = "/home/sentuser/gpgMaildir/new/" + random_id
        command = "ssh root@v6y.net rm -v " + target_file
        ic(command)
        os.system(command)
    elif maildir_subfolder == "new":
        target_file = "/home/user/gpgMaildir/new/" + random_id
        command = "ssh root@v6y.net rm -v " + target_file  # todo use ~/.gpgmda/config
        ic(command)
        os.system(command)
    else:
        ic("unknown exception, exiting")
        sys.exit(1)


def deal_with_badmail(
    *,
    gpgfile: Path,
    yesall: bool,
    verbose: bool | int | float,
):
    if yesall:
        move_badmail_and_delete_off_server(
            gpgfile=gpgfile,
            verbose=verbose,
        )
        return "yesall"

    delete_message_answer = input(
        "Would you like to move this message locally to the ~/.gpgmda/badmail folder and delete it off the server? (yes/no/yesall): "
    )
    delete_message_answer = delete_message_answer.lower()

    if delete_message_answer.startswith("yes"):
        move_badmail_and_delete_off_server(
            gpgfile=gpgfile,
            verbose=verbose,
        )
        if delete_message_answer == "yesall":
            return "yesall"
    return "no"


def decrypt_message(
    *,
    email_address: str,
    gpgfile: Path,
    maildir: Path,
    verbose: bool | int | float,
    stdout: bool = False,
):

    assert isinstance(gpgfile, Path)
    assert isinstance(maildir, Path)

    ic("decrypt_msg():", gpgfile)
    if "@" not in email_address:
        ic("Invalid email address:", email_address, ", exiting.")
        sys.exit(1)

    if not path_exists(gpgfile):
        ic(gpgfile, "No such file or directory. Exiting.")
        sys.exit(1)

    if empty_file(gpgfile):
        ic(
            "FOUND ZERO LENGTH FILE, EXITING. CHECK THE MAILSERVER LOGS (and manually delete it):",
            gpgfile,
        )
        sys.exit(1)

    gpgfile_folder_path = gpgfile.parent
    ic(gpgfile_folder_path)

    maildir_subfolder = gpgfile_folder_path.name
    ic(maildir_subfolder)
    assert maildir_subfolder in ["new", ".sent"]

    if not path_is_dir(maildir):
        ic(maildir, "does not exist. Exiting.")
        sys.exit(1)

    # file_previously_decrypted = 0
    glob_pattern = maildir.as_posix() + "/" + maildir_subfolder + "/*." + gpgfile.name
    ic(glob_pattern)
    result = glob.glob(glob_pattern)

    if len(result) > 1:
        ic(
            "ERROR: This shouldnt happen. More than one result was returned for:",
            glob_pattern,
            ": ",
            result,
        )
        sys.exit(1)

    if stdout is False:
        if len(result) == 1:
            _result = result[0]
            ic("skipping existing file:", _result)
            return True

    ic("decrypting:", gpgfile)
    if stdout:
        # command = "gpg2 -o - --decrypt " + gpgfile + " | tar --transform=s/$/." + gpgfile.name + "/ -xvf -" # hides the tar header
        command = "gpg2 -o - --decrypt " + gpgfile.as_posix()
        ic("decrypt_msg():", command)
        return_code = os.system(command)
        ic(return_code)

    else:
        gpg_command = ["gpg2", "-o", "-", "--decrypt", gpgfile.as_posix()]
        tar_command = [
            "tar",
            "--transform=s/$/." + gpgfile.name + "/",
            "-C",
            maildir.as_posix() + "/" + maildir_subfolder,
            "-xvf",
            "-",
        ]
        gpg_cmd_proc = subprocess.Popen(
            gpg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False
        )
        ic(gpg_command)
        (
            gpg_cmd_proc_output_stdout,
            gpg_cmd_proc_output_stderr,
        ) = gpg_cmd_proc.communicate()

        if verbose:
            ic("gpg_cmd_proc_output_stdout:")
            gpg_cmd_proc_output_stdout_decoded = gpg_cmd_proc_output_stdout.decode(
                "utf-8"
            )
            for line in gpg_cmd_proc_output_stdout_decoded.split("\n"):
                ic("STDOUT:", line)

        ic("gpg_cmd_proc_output_stderr:")
        gpg_cmd_proc_output_stderr_decoded = gpg_cmd_proc_output_stderr.decode("utf-8")
        for line in gpg_cmd_proc_output_stderr_decoded.split("\n"):
            ic("STDERR:", line)

        ic(gpg_cmd_proc.returncode)
        if gpg_cmd_proc.returncode != 0:
            ic("gpg2 did not return 0")
            return False

        if len(gpg_cmd_proc_output_stdout) > 0:
            tar_cmd_proc = subprocess.Popen(
                tar_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
            )
            ic("executing:", tar_command)
            (
                tar_cmd_proc_output_stdout,
                tar_cmd_proc_output_stderr,
            ) = tar_cmd_proc.communicate(gpg_cmd_proc_output_stdout)
            ic("tar_cmd_proc_output_stdout:")
            tar_cmd_proc_output_stdout_decoded = tar_cmd_proc_output_stdout.decode(
                "utf-8"
            )
            for line in tar_cmd_proc_output_stdout_decoded.split("\n"):
                ic("STDOUT:", line)

            ic("tar_cmd_proc_output_stderr:")
            tar_cmd_proc_output_stderr_decoded = tar_cmd_proc_output_stderr.decode(
                "utf-8"
            )
            for line in tar_cmd_proc_output_stderr_decoded.split("\n"):
                ic("STDERR:", line)

            ic(tar_cmd_proc.returncode)

            if tar_cmd_proc.returncode != 0:
                ic("tar did not return 0")
                return False
        else:
            ic("gpg did not produce any stdout, tar skipped file:", gpgfile)
            ic("looking into:", gpgfile, "further...")
            os.system("/bin/ls -al " + gpgfile.as_posix())
            stats = os.stat(gpgfile)
            if stats.st_size <= 1668:
                ic("this is likely an empty gpg encrypted file")
                # search_server_logs_command = ['ssh', 'root@v6y.net', '"', 'zgrep', gpgfile.name, '/var/log/*', '"']
                # search_server_logs_command = ' '.join(search_server_logs_command)
                search_server_logs_command = " ".join(
                    ["echo", '"' + "zgrep", "--", gpgfile.name, "/var/log/*" + '"']
                )
                search_server_logs_command += " | ssh root@v6y.net bash"
                ic(search_server_logs_command)
                # sys.exit(1)
                os.system(search_server_logs_command)
                raise EmptyGPGMailFile

            ic(stats.st_size, gpgfile)
            assert False

    return True


def gpgmaildir_to_maildir(
    *,
    email_address: str,
    gpgMaildir_archive_folder: Path,
    gpgmaildir: Path,
    maildir: Path,
    verbose: bool | int | float,
):

    # todo add locking
    ic()
    assert isinstance(maildir, Path)
    assert isinstance(gpgmaildir, Path)
    assert isinstance(gpgMaildir_archive_folder, Path)
    ic("gpgmda_to_maildir using:", gpgMaildir_archive_folder)
    ic("Checking for default-recipient in ~/.gnupg/gpg.conf")
    command = 'grep "^default-recipient" ~/.gnupg/gpg.conf'
    grep_exit_code = os.system(command)
    if grep_exit_code != 0:
        eprint("error: default-recipient is not defined in ~/.gnupg/gpg.conf. Exiting.")
        sys.exit(1)

    rsync_last_new_mail_file = "/dev/shm/.gpgmda_rsync_last_new_mail_" + email_address
    ic(
        "checking to see if",
        rsync_last_new_mail_file,
        "exists and is greater than 0 bytes",
    )
    rsync_files_transferred = 0
    if path_exists(rsync_last_new_mail_file):
        with open(rsync_last_new_mail_file, "r", encoding="utf8") as fh:
            for line in fh.readlines():
                if "Number of regular files transferred:" in line:
                    ic(line)
                    rsync_files_transferred = int(line.split(":")[1].strip())
                    ic(rsync_files_transferred)
                    break
        if rsync_files_transferred == 0:
            ic("rsync transferred 0 files, skipping decrypt")

        else:
            rsync_list = parse_rsync_log_to_list(
                email_address=email_address,
                gpgMaildir_archive_folder=gpgMaildir_archive_folder,
                verbose=verbose,
            )
            ic(rsync_list)
            skip_hashes = []
            decrypt_list_of_messages(
                message_list=rsync_list,
                skip_hashes=skip_hashes,
                email_address=email_address,
                maildir=maildir,
                verbose=verbose,
            )

    else:
        ic(rsync_last_new_mail_file, "does not exist or is 0 bytes")

    ic("checking if the message counts in the maildir and the gpgmaildir match")
    maildir_counts_dict = get_maildir_file_counts(
        gpgmaildir=gpgmaildir,
        maildir=maildir,
        verbose=verbose,
    )
    ic(maildir_counts_dict)
    maildir_file_count = maildir_counts_dict["files_in_maildir"]
    gpgmaildir_file_count = maildir_counts_dict["files_in_gpgmaildir"]

    ##if gpgmaildir_file_count > maildir_file_count:  # not a good check.
    # if gpgmaildir_file_count != maildir_file_count:  # not a good check.
    #    ic(
    #        "files_in_gpgmaildir != files_in_maildir:",
    #        gpgmaildir_file_count,
    #        "!=",
    #        maildir_file_count,
    #    )
    #    ic("locating un-decrypted files")
    #    files_in_gpgmaildir = [
    #        path
    #        for path in files_pathlib(
    #            gpgmaildir,
    #            verbose=verbose,
    #        )
    #    ]
    #    # assert isinstance(files_in_gpgmaildir[0], Path)
    #    files_in_maildir = [
    #        path
    #        for path in files_pathlib(
    #            maildir,
    #            verbose=verbose,
    #        )
    #    ]
    #    ic(len(files_in_gpgmaildir))
    #    ic(len(files_in_maildir))
    #    ic(len(files_in_gpgmaildir) - len(files_in_maildir))
    #    ic("building hash lists")
    #    # hashes_in_gpgmaildir = [path.name.split('.')[-1] for path in files_in_gpgmaildir]
    #    hashes_in_maildir = [path.name.split(".")[-1] for path in files_in_maildir]
    #    ic(len(hashes_in_maildir))
    #    skip_hashes = hashes_in_maildir

    #    # decrypt_list_of_messages(
    #    #    message_list=files_in_gpgmaildir,
    #    #    skip_hashes=skip_hashes,
    #    #    email_address=email_address,
    #    #    maildir=maildir,
    #    #    verbose=verbose,
    #    # )


def search_list_of_strings_for_substring(
    *,
    list_to_search: list,
    substring: str,
    verbose: bool | int | float,
):
    item_found = ""
    for item in list_to_search:
        try:
            if substring in item:
                item_found = item
                break
        except TypeError:
            pass
    return item_found


def update_notmuch_db(
    *,
    email_address: str,
    email_archive_folder: Path,
    gpgmaildir: Path,
    notmuch_config_file: Path,
    notmuch_config_folder: Path,
    verbose: bool | int | float,
):

    run_notmuch(
        mode="update_notmuch_db",
        email_address=email_address,
        email_archive_folder=email_archive_folder,
        gpgmaildir=gpgmaildir,
        query=None,
        notmuch_config_file=notmuch_config_file,
        notmuch_config_folder=notmuch_config_folder,
        verbose=verbose,
    )


def update_notmuch_address_db(
    *,
    email_address: str,
    email_archive_folder: Path,
    gpgmaildir: Path,
    notmuch_config_file: Path,
    notmuch_config_folder: Path,
    verbose: bool | int | float,
):

    run_notmuch(
        mode="update_address_db",
        email_address=email_address,
        email_archive_folder=email_archive_folder,
        gpgmaildir=gpgmaildir,
        query=None,
        notmuch_config_file=notmuch_config_file,
        notmuch_config_folder=notmuch_config_folder,
        verbose=verbose,
    )


def update_notmuch_address_db_build(
    *,
    email_address,
    email_archive_folder,
    gpgmaildir,
    notmuch_config_file,
    notmuch_config_folder,
    verbose: bool | int | float,
):

    run_notmuch(
        mode="build_address_db",
        email_address=email_address,
        email_archive_folder=email_archive_folder,
        gpgmaildir=gpgmaildir,
        query=None,
        notmuch_config_file=notmuch_config_file,
        notmuch_config_folder=notmuch_config_folder,
        verbose=verbose,
    )


def check_noupdate_list(
    *,
    gpgmda_config_folder: Path,
    email_address: str,
    verbose: bool | int | float,
):

    noupdate_list = open(
        gpgmda_config_folder / Path(".noupdate"), "r"
    ).readlines()  # todo move config to ~/.gpgmda
    for item in noupdate_list:
        if email_address in item:
            eprint(email_address + " is listed in .noupdate, exiting")
            sys.exit(1)


@click.group(no_args_is_help=True, cls=AHGroup)
@click.option("--verbose", is_flag=True)
@click_add_options(click_global_options)
@click.pass_context
def client(
    ctx,
    verbose: bool | int | float,
    verbose_inf: bool,
    dict_output: bool,
):

    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )

    start_time = time.time()
    if verbose:
        ic(time.asctime())

    gpgmda_config_folder = os.path.expanduser("~/.gpgmda/")
    ctx.obj["gpgmda_config_folder"] = gpgmda_config_folder
    # ctx.gpgmda_config_folder = gpgmda_config_folder

    if verbose:
        ic(time.asctime())
        ic("TOTAL TIME IN MINUTES:")
        ic((time.time() - start_time) / 60.0)


@client.command()
@click.argument("email_address", nargs=1, required=True, type=str)
# @click.option("--email-archive-type", help="", type=click.Choice(['gpgMaildir']), default="gpgMaildir")
@click_add_options(click_global_options)
@click.pass_context
def build_paths(
    ctx,
    email_address: str,
    verbose: bool | int | float,
    verbose_inf: bool,
    dict_output: bool,
):

    assert "@" in email_address
    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )

    ctx.email_archive_type = "gpgMaildir"

    ctx.email_archive_folder = Path("/home/user/__email_folders")
    check_or_create_dir(ctx.email_archive_folder)

    ctx.gpgMaildir_archive_folder_base_path = ctx.email_archive_folder / Path(
        "_gpgMaildirs"
    )
    check_or_create_dir(ctx.gpgMaildir_archive_folder_base_path)

    ctx.gpgMaildir_archive_folder = ctx.gpgMaildir_archive_folder_base_path / Path(
        email_address
    )
    check_or_create_dir(ctx.gpgMaildir_archive_folder)

    ctx.gpgmaildir = Path(ctx.gpgMaildir_archive_folder) / Path("gpgMaildir")
    check_or_create_dir(ctx.gpgmaildir)

    stdMaildir_archive_folder = (
        ctx.email_archive_folder / Path("_Maildirs") / Path(email_address)
    )
    check_or_create_dir(stdMaildir_archive_folder)

    ctx.maildir = stdMaildir_archive_folder / Path("Maildir")
    check_or_create_dir(ctx.maildir / Path("new"))
    check_or_create_dir(ctx.maildir / Path("cur"))
    check_or_create_dir(ctx.maildir / Path(".sent"))

    ctx.notmuch_config_folder = ctx.email_archive_folder / Path("_notmuch_config")
    check_or_create_dir(ctx.notmuch_config_folder)

    ctx.notmuch_config_file = ctx.notmuch_config_folder / Path(".notmuch_config")
    make_notmuch_config(
        email_address=email_address,
        email_archive_folder=ctx.email_archive_folder,
        verbose=verbose,
    )
    return ctx


@client.command()
@click.argument("email_address", nargs=1)
@click.argument("query", type=str)
@click_add_options(click_global_options)
@click.pass_context
def address_query(
    ctx,
    email_address: str,
    query: str,
    verbose: bool | int | float,
    verbose_inf: bool,
    dict_output: bool,
):
    """search for address string"""
    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )
    ctx = ctx.invoke(build_paths, email_address=email_address)
    run_notmuch(
        mode="query_address_db",
        email_address=email_address,
        query=query,
        email_archive_folder=ctx.email_archive_folder,
        gpgmaildir=ctx.gpgmaildir,
        notmuch_config_file=ctx.notmuch_config_file,
        notmuch_config_folder=ctx.notmuch_config_folder,
        verbose=verbose,
    )


@client.command()
@click.argument("email_address", nargs=1)
@click_add_options(click_global_options)
@click.pass_context
def read(
    ctx,
    email_address: str,
    verbose: bool | int | float,
    verbose_inf: bool,
    dict_output: bool,
):

    """read mail without checking for new mail"""
    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )
    ctx = ctx.invoke(build_paths, email_address=email_address)
    load_ssh_key(
        email_address=email_address,
        verbose=verbose,
    )  # so mail can be sent without having to unlock the key
    make_notmuch_config(
        email_address=email_address,
        email_archive_folder=ctx.email_archive_folder,
        verbose=verbose,
    )
    start_alot(
        email_address=email_address,
        email_archive_folder=ctx.email_archive_folder,
        verbose=verbose,
    )


@client.command()
@click.argument("email_address", nargs=1)
@click_add_options(click_global_options)
@click.pass_context
def decrypt(
    ctx,
    email_address: str,
    verbose: bool | int | float,
    verbose_inf: bool,
    dict_output: bool,
):
    """decrypt new mail in encrypted maildir to unencrypted maildir"""
    ic()
    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )

    ctx = ctx.invoke(build_paths, email_address=email_address)
    check_noupdate_list(
        gpgmda_config_folder=ctx.obj["gpgmda_config_folder"],
        email_address=email_address,
        verbose=verbose,
    )

    if ctx.email_archive_type == "gpgMaildir":
        ctx.invoke(warm_up_gpg)
        gpgmaildir_to_maildir(
            email_address=email_address,
            gpgMaildir_archive_folder=ctx.gpgMaildir_archive_folder,
            gpgmaildir=ctx.gpgmaildir,
            maildir=ctx.maildir,
            verbose=verbose,
        )

        ic("done with gpgmaildir_to_maildir()")
    else:
        ic("Unsupported:", ctx.email_archive_type, "Exiting.")
        sys.exit(1)


@client.command()
@click.argument("email_address", nargs=1)
@click_add_options(click_global_options)
@click.pass_context
def update_notmuch(
    ctx,
    email_address: str,
    verbose: bool | int | float,
    verbose_inf: bool,
    dict_output: bool,
):
    """update notmuch with new mail from (normal, unencrypted) maildir"""
    ic()
    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )

    ctx = ctx.invoke(build_paths, email_address=email_address)
    check_noupdate_list(
        gpgmda_config_folder=ctx.obj["gpgmda_config_folder"],
        email_address=email_address,
        verbose=verbose,
    )

    if ctx.email_archive_type == "gpgMaildir":
        ctx.invoke(warm_up_gpg)

    elif ctx.email_archive_type == "getmail":
        ic('gpgmda_program_folder/getmail_gmail "${email_address}" || exit 1')
        ic("todo, call /getmail_gmail ${email_address}")

    else:
        ic("unknown folder type", ctx.email_archive_type, "exiting")

    update_notmuch_db(
        email_address=email_address,
        email_archive_folder=ctx.email_archive_folder,
        gpgmaildir=ctx.gpgmaildir,
        notmuch_config_file=ctx.notmuch_config_file,
        notmuch_config_folder=ctx.notmuch_config_folder,
        verbose=verbose,
    )

    update_notmuch_address_db(
        email_address=email_address,
        email_archive_folder=ctx.email_archive_folder,
        gpgmaildir=ctx.gpgmaildir,
        notmuch_config_file=ctx.notmuch_config_file,
        notmuch_config_folder=ctx.notmuch_config_folder,
        verbose=verbose,
    )


@client.command()
@click.argument("email_address", nargs=1)
@click_add_options(click_global_options)
@click.pass_context
def download(
    ctx,
    email_address: str,
    verbose: bool | int | float,
    verbose_inf: bool,
    dict_output: bool,
):
    """rsync new mail to encrypted maildir"""
    ic()
    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )
    ctx = ctx.invoke(build_paths, email_address=email_address)
    check_noupdate_list(
        gpgmda_config_folder=ctx.obj["gpgmda_config_folder"],
        email_address=email_address,
        verbose=verbose,
    )

    if ctx.email_archive_type == "gpgMaildir":
        ctx.invoke(warm_up_gpg)
        rsync_mail(
            email_address=email_address,
            gpgMaildir_archive_folder=ctx.gpgMaildir_archive_folder,
            verbose=verbose,
        )

    else:
        ic("Unsupported:", ctx.email_archive_type, "Exiting.")
        sys.exit(1)


@client.command()
@click.argument("email_address", nargs=1)
@click_add_options(click_global_options)
@click.pass_context
def address_db_build(
    ctx,
    email_address: str,
    verbose: bool | int | float,
    verbose_inf: bool,
    dict_output: bool,
):
    """build address database for use with address_query"""
    ic()

    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )

    ctx = ctx.invoke(build_paths, email_address=email_address)
    update_notmuch_address_db_build(
        email_address=email_address,
        email_archive_folder=ctx.email_archive_folder,
        gpgmaildir=ctx.gpgmaildir,
        notmuch_config_file=ctx.notmuch_config_file,
        notmuch_config_folder=ctx.notmuch_config_folder,
        verbose=verbose,
    )


@client.command()
@click.argument("email_address", nargs=1)
@click.argument("query", type=str)
@click_add_options(click_global_options)
@click.pass_context
def afew_query(
    ctx,
    email_address: str,
    query: str,
    verbose: bool | int | float,
    verbose_inf: bool,
    dict_output: bool,
):
    """execute arbitrary afew query"""
    ic()

    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )
    ctx = ctx.invoke(build_paths, email_address=email_address)
    ic(query)
    run_notmuch(
        mode="query_afew",
        email_address=email_address,
        query=query,
        email_archive_folder=ctx.email_archive_folder,
        gpgmaildir=ctx.gpgmaildir,
        notmuch_config_file=ctx.notmuch_config_file,
        notmuch_config_folder=ctx.notmuch_config_folder,
        verbose=verbose,
    )


@client.command()
@click.argument("email_address", nargs=1)
@click.argument("query", type=str)
@click_add_options(click_global_options)
@click.pass_context
def notmuch_query(
    ctx,
    email_address: str,
    query: str,
    verbose: bool | int | float,
    verbose_inf: bool,
    dict_output: bool,
):
    '''execute arbitrary notmuch query notmuch search --output=files "thread:000000000003c194"'''
    ic()

    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )
    ctx = ctx.invoke(build_paths, email_address=email_address)
    ic(query)
    run_notmuch(
        mode="query_notmuch",
        email_address=email_address,
        query=query,
        email_archive_folder=ctx.email_archive_folder,
        gpgmaildir=ctx.gpgmaildir,
        notmuch_config_file=ctx.notmuch_config_file,
        notmuch_config_folder=ctx.notmuch_config_folder,
        verbose=verbose,
    )


@client.command()
@click.argument("email_address", nargs=1)
@click_add_options(click_global_options)
@click.pass_context
def show_message_counts(
    ctx,
    email_address: str,
    verbose: bool | int | float,
    verbose_inf: bool,
    dict_output: bool,
):

    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )

    ctx = ctx.invoke(build_paths, email_address=email_address)
    print(
        get_maildir_file_counts(
            gpgmaildir=ctx.gpgmaildir,
            maildir=ctx.maildir,
            verbose=verbose,
        )
    )


@client.command()
@click_add_options(click_global_options)
@click.pass_context
def warm_up_gpg(
    ctx,
    *,
    verbose: bool | int | float,
    verbose_inf: bool,
    dict_output: bool,
):
    """make sure gpg is working"""
    ic()

    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )
    # due to https://bugs.g10code.com/gnupg/issue1190 first get gpg-agent warmed up by decrypting a test message.
    decrypt_test = 0

    while decrypt_test != 1:
        ic("generating gpg test string")
        test_string = short_random_string()
        ic(test_string)

        command = "gpg --yes --trust-model always --throw-keyids --encrypt -o - | gpg --decrypt"
        gpg_cmd_proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
        )
        ic("writing test_string to gpg_cmd_proc and reading output")
        (
            gpg_cmd_proc_output_stdout,
            gpg_cmd_proc_output_stderr,
        ) = gpg_cmd_proc.communicate(test_string)
        # ic(gpg_cmd_proc_output_stdout)
        gpg_cmd_proc_output_stdout_decoded = gpg_cmd_proc_output_stdout.decode("utf-8")
        for line in gpg_cmd_proc_output_stdout_decoded.split("\n"):
            ic("STDOUT:", line)

        ic("gpg_cmd_proc_output_stderr:")
        gpg_cmd_proc_output_stderr_decoded = gpg_cmd_proc_output_stderr.decode("utf-8")
        for line in gpg_cmd_proc_output_stderr_decoded.split("\n"):
            ic("STDERR:", line)

        ic(gpg_cmd_proc.returncode)

        if gpg_cmd_proc.returncode != 0:
            ic("warm_up_gpg did not return 0, exiting")
            sys.exit(1)

        if test_string not in gpg_cmd_proc_output_stdout:
            ic(
                "test_string:",
                test_string,
                "is not in",
                gpg_cmd_proc_output_stdout,
                "Exiting.",
            )
            sys.exit(1)
        else:
            ic("found test string in gpg_cmd_proc_output_stdout, gpg is working")
            decrypt_test = 1

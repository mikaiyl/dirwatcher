#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import argparse
import datetime
import logging
import logging.config # noqa
import os
import signal
import time
import warnings # noqa

# Setup logger
logging.config.fileConfig('logger_config.ini')
logger = logging.getLogger('mainLogger')

exit_flag = False
start_time = time.time()


def banner(text, delim='*', length=100):
    '''
    Print banner for logger
    '''

    if not text:
        return delim * length
    elif len(text) + 2 + len(delim) > length:
        return text
    else:
        r = length - len(text) + 2
        p_len = r / 2
        s_len = r - p_len
        prefix = delim * int( p_len if len(delim) is 1 else p_len/len(delim) + delim[:p_len%len(delim)] ) # noqa
        suffix = delim * int( s_len if len(delim) is 1 else s_len/len(delim) + delim[:s_len%len(delim)] ) # noqa
        return prefix + ' ' + text + ' ' + suffix


def signal_handler(sig_num, frame):
    """
    This is a handler for SIGTERM and SIGINT. Other signals can
    be mapped here as well (SIGHUP?) Basically it just sets a global
    flag, and main() will exit it's loop if the signal is trapped.
    :param sig_num: The integer signal number that was trapped from the OS.
    :param frame: Not used
    :return None
    """

    # log the associated signal name (the python3 way)
    # log the signal name (the python2 way)
    # signames = dict((k, v) for v, k in reversed(sorted(signal.__dict__.items())) if v.startswith('SIG') and not v.startswith('SIG_')) # noqa
    # logger.warn('Received ' + signames[sig_num])
    logger = logging.getLogger('mainLogger')
    logger.info('Received ' + signal.Signals(sig_num).name)

    global exit_flag
    exit_flag = True


def scan_file(file, word, history=None, curdir=os.path.curdir):
    '''
    Scans files,
    keep track of line count,
    log found keywords,
    '''

    if not history:
        history = {}

    logger = logging.getLogger('mainLogger')
    logger.debug('Scanning {} for {}'.format(file, word))

    if file.path in history:
        if history[file.path][1] == os.stat(file.path).st_size:
            return history
    else:
        # log
        logger.info('New file: {}, found in {}'.format(file.name, curdir))
        history[file.path] = (0, os.stat(file.path).st_size) # noqa

    # Open file and find occurences of search term
    with open(os.path.abspath(file.path), 'r') as f:
        max_num = history[file.path][0]
        for j, line in enumerate(list(f)):
            i = j-1
            if i > max_num and word in line or j == 1:
                # Log
                logger.info('Found {} in {} at line {}'.format(word, file.name, i)) # noqa
                max_num = i

        history.update({file.path: (max_num, os.stat(file.path).st_size)})

    return history


def watch_dir(directory, word, ext, history=None, wait=5):
    '''
    This actively scans the dirs being watched.
    '''

    if not history:
        history = {}

    logger = logging.getLogger('mainLogger')

    # Does the directory exist?
    if os.path.isdir(directory):
        logger.debug('Scanning {}'.format(os.path.abspath(directory)))
        if ext:
            files = list(filter(lambda f: f.path.endswith(ext), list(os.scandir(directory)))) # noqa
        else:
            files = list(os.scandir(directory)) # noqa

        for file in files:
            if not file.is_dir():
                history.update(scan_file(file, word, history, directory))

        for file in history:
            to_kill = []
            if file not in map(lambda f: f.path, files):
                logger.info('File {} removed'.format(file))
                to_kill.append(file)

            for kill in to_kill:
                history.pop(kill)
    else:
        logger.warn('Directory {} not found. Waiting'.format(directory))
        time.sleep(wait)

    return history


def main():
    # Hook these two signals from the OS ..
    # Now my signal_handler will get called if
    # OS sends either of these to my process.
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Setup argparser
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', '--dir', '-D', '-d', default=os.path.abspath('.'), help='Dir name or comma separated list of dirs') # noqa
    parser.add_argument('--extension', '--ext', '-E', '-e', default=None, help='Specifies the filetype being watched') # noqa
    parser.add_argument('--interval', '--int', '-I', '-i', type=int, default=1, help='Number of seconds between scans') # noqa
    parser.add_argument('--magic', '--word', '-m', '-w', type=str, help='Word to search for', required=True) # noqa
    # parser.add_argument('--debug', action='store_true', help='Sets debug level') # noqa
    args = parser.parse_args()

    logger.info(banner('Starting', length=40))

    # Run until SIGTERM
    history = {}
    while not exit_flag:
        try:
            # call my directory watching function..
            dirpath = os.path.abspath(args.directory)
            history.update(watch_dir(dirpath, args.magic, args.extension, history)) # noqa
        except FileNotFoundError as e: # noqa
            logger.error(e)
        except Exception as e:
            # This is an UNHANDLED exception
            # Log an ERROR level message here
            logger.error(e)

        # put a sleep inside my while loop
        # so I don't peg the cpu usage at 100%
        time.sleep(args.interval)

    logger.info(banner('Exiting', length=40))
    global start_time
    logger.info(banner('Uptime: {}'.format(datetime.timedelta(seconds=time.time()-start_time)), length=40)) # noqa
    # final exit point happens here
    # Log a message that we are shutting down
    # Include the overall uptime since program start.


if __name__ == '__main__':
    main()

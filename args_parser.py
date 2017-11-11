import sys
import os

from constants import *

def roleValid(role):
    return role == TRACKER_ROLE_NAME or role == PEER_ROLE_NAME

def is_peer(settings):
    return settings[SETTINGS_ROLE_KEY] == PEER_ROLE_NAME

def is_tracker(settings):
    return settings[SETTINGS_ROLE_KEY] == TRACKER_ROLE_NAME

def portValid(port):
    try:
        port_number = int(port)
        if port_number >= 0 and port_number <= 65535:
            return True
        else:
            return False
    except ValueError:
        return False

def validSettings(settings):
    if SETTINGS_ROLE_KEY not in settings:
        return False
    if settings[SETTINGS_ROLE_KEY] == TRACKER_ROLE_NAME:
        return all(name in settings for name in TRACKER_SETTINGS)
    else:
        return all(name in settings for name in PEER_SETTINGS)


def parse_args(system_arguments):
    settings = {};
    system_arguments = system_arguments[1:]

    flag = ""
    for arg in system_arguments:
        if flag == "":
            if arg in SUPPORTED_FLAGS:
                if arg == HOLE_PUNCHING_FLAG:
                    settings[SETTINGS_HOLE_PUNCHING_KEY] = True
                else:
                    flag = arg
            else:
                sys.exit(UNSUPPORTED_FLAG_MESSAGE + arg)
        else:
            if flag == ROLE_FLAG:
                if roleValid(arg):
                    settings[SETTINGS_ROLE_KEY] = arg
                else:
                    sys.exit(ROLE_INVALID_MESSAGE)
            if flag == PORT_FLAG:
                if portValid(arg):
                    settings[SETTINGS_PORT_KEY] = int(arg)
                else:
                    sys.exit(PORT_INVALID_MESSAGE)
            if flag == TRACKER_ADDRESS_FLAG:
                settings[SETTINGS_TRACKER_ADDRESS_KEY] = arg
            if flag == TRACKER_PORT_FLAG:
                if portValid(arg):
                    settings[SETTINGS_TRACKER_PORT_KEY] = int(arg)
                else:
                    sys.exit(PORT_INVALID_MESSAGE)
            if flag == PEER_DIRECTORY_FLAG:
                if os.path.exists(arg):
                    settings[SETTINGS_PEER_DIRECTORY_KEY] = arg
                else:
                    sys.exit(DIRECTORY_DOES_NOT_EXIST_MESSAGE)
            if flag == SIGNAL_PORT_FLAG:
                if portValid(arg):
                    settings[SETTINGS_SIGNAL_PORT_KEY] = int(arg)
            if flag == TRACKER_SIGNAL_PORT_FLAG:
                if portValid(arg):
                    settings[SETTINGS_TRACKER_SIGNAL_PORT_KEY] = int(arg)
            flag = ""

    # Arguments are left hanging
    if flag != "":
        sys.exit(flag + " is missing")

    if not validSettings(settings):
        sys.exit(SETTINGS_INVALID_MESSAGE)
    return settings

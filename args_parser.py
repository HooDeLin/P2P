import sys
import os

def roleValid(role):
    return role == "tracker" or role == "peer"

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
    tracker_settings = ["role", "port", "signal-port"]
    peer_settings = ["role", "port", "tracker-address", "tracker-port", "peer-directory", "signal-port", "tracker-signal-port"]
    if "role" not in settings:
        return False
    if settings["role"] == "tracker":
        return all(name in settings for name in tracker_settings)
    else:
        return all(name in settings for name in peer_settings)


def parse_args(system_arguments):
    settings = {};
    system_arguments = system_arguments[1:]

    supported_flags = ["--role", "--port", "--tracker-address", "--tracker-port", "--peer-directory", "--hole-punching", "--signal-port", "--tracker-signal-port"]
    flag = ""
    for arg in system_arguments:
        if flag == "":
            if arg in supported_flags:
                if arg == "--hole-punching":
                    settings["hole-punching"] = True
                else:
                    flag = arg
            else:
                sys.exit("Unsupported flag: " + arg)
        else:
            if flag == "--role":
                if roleValid(arg):
                    settings["role"] = arg
                else:
                    sys.exit("Role invalid")
            if flag == "--port":
                if portValid(arg):
                    settings["port"] = int(arg)
                else:
                    sys.exit("Port invalid")
            if flag == "--tracker-address":
                settings["tracker-address"] = arg
            if flag == "--tracker-port":
                if portValid(arg):
                    settings["tracker-port"] = int(arg)
                else:
                    sys.exit("Port invalid")
            if flag == "--peer-directory":
                if os.path.exists(arg):
                    settings["peer-directory"] = arg
                else:
                    sys.exit("Directory does not exist")
            if flag == "--signal-port":
                if portValid(arg):
                    settings["signal-port"] = int(arg)
            if flag == "--tracker-signal-port":
                if portValid(arg):
                    settings["tracker-signal-port"] = int(arg)
            flag = ""

    # Arguments are left hanging
    if flag != "":
        sys.exit(flag + " is missing")

    if not validSettings(settings):
        sys.exit("Settings invalid")
    return settings

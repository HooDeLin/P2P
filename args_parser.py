import sys

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

def parse_args(system_arguments):
    settings = {};
    system_arguments = system_arguments[1:]
    if (len(system_arguments) != 4):
        sys.exit("Incorrect amount of arguments")

    supported_flags = ["--role", "--port"]
    flag = ""
    for arg in system_arguments:
        if flag == "":
            if arg in supported_flags:
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
            flag = ""

    # Arguments are left hanging
    if flag != "":
        sys.exit(flag + " is missing")
    return settings

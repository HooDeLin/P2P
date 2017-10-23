import sys

def roleValid(role):
    return role == "tracker" or role == "peer"

def parse_args(system_arguments):
    settings = {};
    system_arguments = system_arguments[1:]
    if (len(system_arguments) != 2):
        sys.exit("Incorrect amount of arguments")

    supported_flags = ["--role"]
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
            flag = ""

    # Arguments are left hanging
    if flag != "":
        sys.exit(flag + " is missing")
    return settings

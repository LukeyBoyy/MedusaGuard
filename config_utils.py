import configparser

def update_config_file(config_path, username=None, password=None, path=None, port_list_name=None,
                       scan_config=None, scanner=None, target_name=None, target_ip=None, task_name=None):
    """
    Updates the configuration file with the provided values.
    """
    config = configparser.ConfigParser()
    config.read(config_path)

    if username is not None:
        config['connection']['username'] = username
    if password is not None:
        config['connection']['password'] = password
    if path is not None:
        config['connection']['path'] = path
    if port_list_name is not None:
        config['target']['port_list_name'] = port_list_name
    if scan_config is not None:
        config['task']['scan_config'] = scan_config
    if scanner is not None:
        config['task']['scanner'] = scanner
    if target_name is not None:
        config['target']['target_name'] = target_name
    if target_ip is not None:
        config['target']['target_ip'] = target_ip
    if task_name is not None:
        config['task']['task_name'] = task_name

    with open(config_path, 'w') as configfile:
        config.write(configfile)

def read_host_from_file(file_path):
    """
    Reads a file containing IP addresses (one per line) and returns them as a comma-separated string.
    """
    with open(file_path, 'r') as file:
        hosts = [line.strip() for line in file if line.strip()]
    return ','.join(hosts)

def load_config(config_path):
    """
    Loads the configuration from the specified config file and returns the config parser object.
    """
    config = configparser.ConfigParser()
    config.read(config_path)
    return config
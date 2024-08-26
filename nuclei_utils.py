import configparser

def update_config_file(config_path, username=None, password=None, path=None, port_list_name=None,
                       scan_config=None, scanner=None, target_name=None, target_ip=None, task_name=None):
    """
    Updates the specified configuration file with the provided values.

    This function modifies the configuration settings within the config file
    based on the provided parameters. If a parameter is not provided (i.e.,
    remains None), the corresponding value in the config file is left unchanged.

    Args:
        config_path (str): Path to the configuration file.
        username (str, optional): Username for the GVM server.
        password (str, optional): Password for the GVM server.
        path (str, optional): Path to the Unix socket for GVM connection.
        port_list_name (str, optional): Port list name for target configuration.
        scan_config (str, optional): Scan configuration ID.
        scanner (str, optional): Scanner ID.
        target_name (str, optional): Name of the target.
        target_ip (str, optional): IP address of the target or file path with IPs.
        task_name (str, optional): Name of the task to be created and executed.
    """
    config = configparser.ConfigParser()
    config.read(config_path) # Read the existing configuration from the file

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

    # Write the updated configuration back to the file
    with open(config_path, 'w') as configfile:
        config.write(configfile)

def read_host_from_file(file_path):
    """
    Reads a file containing IP addresses (one per line) and returns them as a comma-separated string.
    """
    with open(file_path, 'r') as file:
        # Read each line, strip whitespace, and only keep non-empty lines
        hosts = [line.strip() for line in file if line.strip()]
    # Join the list of hosts into a single string separated by commas
    return ','.join(hosts)

def load_config(config_path):
    """
    Loads and returns the configuration from the specified file.
    """
    config = configparser.ConfigParser()
    config.read(config_path)
    return config
import os
import time
import argparse
import configparser
from termcolor import colored
from nuclei_utils import run_nuclei_scans, update_nuclei
from openvas_utils import openvas_scan, update_nvt, update_scap, update_cert
from report_utils import generate_report
from config_utils import update_config_file

def main():
    """
       Main function to handle the execution of the vulnerability scanning and exploitation tool.

       This function performs the following tasks:
       - Parses command-line arguments.
       - Verifies if the script is being run with root privileges.
       - Displays a logo and a warning message.
       - Creates directories for storing reports and results.
       - Updates the configuration file with provided arguments.
       - Runs Nuclei scans and updates.
       - Updates the Greenbone Vulnerability Manager (GVM) feeds.
       - Executes the OpenVAS scan and generates a report based on the scan results.

       Command-line Arguments:
           --config (str): Path to the config.ini file.
           --username (str): Username for the GVM server.
           --password (str): Password for the GVM server.
           --path (str): Path to the Unix socket for GVM connection.
           --port_list_name (str): Port list name for target configuration.
           --scan_config (str): Scan configuration ID.
           --scanner (str): Scanner ID.
           --target_name (str): Name of the target.
           --target_ip (str): IP address of the target to be scanned or file containing one IP address per line.
           --task_name (str): Name of the task to be created and executed.
       """
    parser = argparse.ArgumentParser(
        description="Update config.ini settings.",
        epilog="""Example usage:
    sudo python3 <script_name>.py --config config.ini --username admin --password passwd --target_name router --task_name router_scan"""
    )
    parser.add_argument('--config', type=str, default="config.ini", help='Path to the config.ini file')
    parser.add_argument('--username', type=str, help='Username for the GVM server')
    parser.add_argument('--password', type=str, help='Password for the GVM server')
    parser.add_argument('--path', type=str, help='Path to the Unix socket for GVM connection')
    parser.add_argument('--port_list_name', type=str, help='Port list name for target configuration')
    parser.add_argument('--scan_config', type=str, help='Scan configuration ID')
    parser.add_argument('--scanner', type=str, help='Scanner ID')
    parser.add_argument('--target_name', type=str, help='Name of the target')
    parser.add_argument('--target_ip', type=str,
                        help='IP address of the target to be scanned or file containing one IP address per line')
    parser.add_argument('--task_name', type=str, help='Name of the task to be created and executed')

    args = parser.parse_args()

    # Checks if script was executed using a non-root user
    if os.getuid() != 0:
        exit(colored(
            "You need to have root privileges to run this script.\nPlease try again, this time using 'sudo'. Exiting...",
            "red"))

    # Tool logo
    print(colored("""                                  
                                                   @#####              
                                                  @##@###@          
                                               .@@@.    #@##  
                                             @-=====+     ##                
                                             @@+====+.     ##@.             
                                             @@==+==+.          @.         
                            .+*              @===@=@+  -@                  
                           .===@             :%+*@@%@==@+==-                
                            +++====-@.    -====-*@@++++@@@==@@*+        
                               @@+=====@****==@=+-=======++======++         
                                   @++*@####% -=+-=======++======@@                
              _______           _                  _______                      _ 
             (_______)         | |                (_______)                    | |
              _  _  _ _____  __| |_   _  ___ _____ _   ___ _   _ _____  ____ __| |
             | ||_|| | ___ |/ _  | | | |/___|____ | | (_  | | | (____ |/ ___) _  |
             | |   | | ____( (_| | |_| |___ / ___ | |___) | |_| / ___ | |  ( (_| |
             |_|   |_|_____)\____|____/(___/\_____|\_____/|____/\_____|_|   \____| v1. 

                   Automated Vulnerability Scanning & Exploitation Framework                           
   """, "light_red", attrs=['bold']))

    print(colored(f"[WARNING] Only use this tool against authorised targets. You are responsible for your actions!\n",
                  'light_yellow', attrs=['bold']))
    time.sleep(2.5)

    # Makes directories for the openvas, nmap, and nuclei output
    os.makedirs("openvas_reports", exist_ok=True)
    os.makedirs("nuclei_results", exist_ok=True)
    os.makedirs("result_graphs", exist_ok=True)

    # Checks if script was executed using a non-root user
    if os.getuid() != 0:
        exit(colored(
            "You need to have root privileges to run this script.\nPlease try again, this time using 'sudo'. Exiting...",
            "red"))

    update_config_file(args.config, args.username, args.password, args.path, args.port_list_name,
                       args.scan_config, args.scanner, args.target_name, args.target_ip, args.task_name)

    config = configparser.ConfigParser()
    config.read(args.config)

    path = config['connection']['path']
    username = config['connection']['username']
    password = config['connection']['password']
    target_name = config['target']['target_name']
    target_ip = config['target']['target_ip']
    port_list_name = config['target']['port_list_name']
    task_name = config['task']['task_name']
    scan_config = config['task']['scan_config']
    scanner = config['task']['scanner']

    # Run Nuclei Scans
    update_nuclei()
    run_nuclei_scans(nuclei_target_dir="nuclei_results", nuclei_target_file="targets.txt")

    # Update Greenbone Vulnerability Manager feeds
    update_nvt()
    update_scap()
    update_cert()

    # Run OpenVAS Scan and get the path to the generated CSV report and task name
    csv_path, task_name, hosts_count, high_count, medium_count, low_count = openvas_scan(path, username, password,
                                                                                         target_name, target_ip,
                                                                                         port_list_name, task_name,
                                                                                         scan_config, scanner)

    # Generate the report using the generated CSV report path
    if csv_path:
        generate_report(csv_path, task_name, hosts_count, high_count, medium_count, low_count)
    else:
        print("Failed to generate the CSV report, skipping report generation.")


if __name__ == "__main__":
    main()
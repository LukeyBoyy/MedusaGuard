import os
import sys
import json
import configparser
import argparse
from termcolor import colored
from openvas_utils import openvas_scan  # Only importing OpenVAS-related functions
from report_utils import generate_report
from config_utils import update_config_file

sys.stdout.reconfigure(line_buffering=True)

def main():
    """
    Main function to handle the execution of the vulnerability scanning tool.
    This version only runs OpenVAS.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Update config.ini settings and run OpenVAS scan.",
        epilog="""Example usage:
        sudo python3 <script_name>.py --config config.ini --username admin --password passwd --target_name router --task_name router_scan"""
    )
    parser.add_argument(
        "--config", type=str, default="config.ini", help="Path to the config.ini file"
    )
    parser.add_argument("--username", type=str, help="Username for the GVM server")
    parser.add_argument("--password", type=str, help="Password for the GVM server")
    parser.add_argument("--path", type=str, help="Path to the Unix socket for GVM connection")
    parser.add_argument("--port_list_name", type=str, help="Port list name for target configuration")
    parser.add_argument("--scan_config", type=str, help="Scan configuration ID")
    parser.add_argument("--scanner", type=str, help="Scanner ID")
    parser.add_argument("--target_name", type=str, help="Name of the target")
    parser.add_argument("--target_ip", type=str, help="IP address of the target to be scanned or file containing one IP address per line")
    parser.add_argument("--task_name", type=str, help="Name of the task to be created and executed")

    args = parser.parse_args()

    # Check if the script is being run with root privileges
    if os.getuid() != 0:
        exit(
            colored(
                "You need to have root privileges to run this script.\nPlease try again, this time using 'sudo'. Exiting...",
                "red",
            )
        )

    # Create directories for storing outputs if they don't already exist
    os.makedirs("openvas_reports", exist_ok=True)

    # Update the configuration file with provided arguments
    update_config_file(
        args.config,
        args.username,
        args.password,
        args.path,
        args.port_list_name,
        args.scan_config,
        args.scanner,
        args.target_name,
        args.target_ip,
        args.task_name,
    )

    # Read configuration settings from the updated config.ini file
    config = configparser.ConfigParser()
    config.read(args.config)

    # Extract configuration values
    path = config["connection"]["path"]
    username = config["connection"]["username"]
    password = config["connection"]["password"]
    target_name = config["target"]["target_name"]
    target_ip = config["target"]["target_ip"]
    port_list_name = config["target"]["port_list_name"]
    task_name = config["task"]["task_name"]
    scan_config = config["task"]["scan_config"]
    scanner = config["task"]["scanner"]

    # Run OpenVAS scan and get the path to the generated CSV report and task details
    (
        csv_path,
        task_name,
        hosts_count,
        high_count,
        medium_count,
        low_count,
        os_count,
        apps_count,
    ) = openvas_scan(
        path,
        username,
        password,
        target_name,
        target_ip,
        port_list_name,
        task_name,
        scan_config,
        scanner,
    )

    # Generate the report using the generated CSV report path
    if csv_path:
        generate_report(
            csv_path,
            task_name,
            hosts_count,
            high_count,
            medium_count,
            low_count,
            os_count,
            apps_count,
        )
    else:
        print("Failed to generate the CSV report, skipping report generation.")

    # Write counts to counts.json
    counts = {
        "hosts_count": hosts_count,
        "apps_count": apps_count,
        "os_count": os_count,
        "high_count": high_count,
        "medium_count": medium_count,
        "low_count": low_count
    }

    with open('counts.json', 'w') as f:
        json.dump(counts, f)

if __name__ == "__main__":
    main()

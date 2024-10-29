import os
import sys
import json
import time
import argparse
import configparser
from termcolor import colored
from datetime import *
from nuclei_utils import run_nuclei_scans, update_nuclei
from openvas_utils import openvas_scan, update_nvt, update_scap, update_cert
from report_utils import generate_report
from config_utils import update_config_file
from nikto_utils import run_nikto_scans
from exploit_module import *


def main():
    """
    Main function to handle the execution of the vulnerability scanning and exploitation tool.

    This function performs the following tasks:
    - Parses command-line arguments.
    - Verifies if the script is being run with root privileges.
    - Displays a warning message.
    - Creates directories for storing reports and results.
    - Updates the configuration file with provided arguments.
    - Runs Nuclei scans and updates.
    - Runs Nikto scans.
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
    # Start timing the execution
    start_time = time.time()

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Update config.ini settings.",
        epilog="""Example usage:
    sudo python3 <script_name>.py --config config.ini --username admin --password passwd --target_name router --task_name router_scan""",
    )
    parser.add_argument(
        "--config", type=str, default="config.ini", help="Path to the config.ini file"
    )
    parser.add_argument("--username", type=str, help="Username for the GVM server")
    parser.add_argument("--password", type=str, help="Password for the GVM server")
    parser.add_argument(
        "--path", type=str, help="Path to the Unix socket for GVM connection"
    )
    parser.add_argument(
        "--port_list_name", type=str, help="Port list name for target configuration"
    )
    parser.add_argument("--scan_config", type=str, help="Scan configuration ID")
    parser.add_argument("--scanner", type=str, help="Scanner ID")
    parser.add_argument("--target_name", type=str, help="Name of the target")
    parser.add_argument(
        "--target_ip",
        type=str,
        help="IP address of the target to be scanned or file containing one IP address per line",
    )
    parser.add_argument(
        "--task_name", type=str, help="Name of the task to be created and executed"
    )

    args = parser.parse_args()

    # Check if the script is being run with root privileges
    if os.getuid() != 0:
        exit(
            colored(
                "You need to have root privileges to run this script.\nPlease try again, this time using 'sudo'. Exiting...",
                "red",
            )
        )

    # Display a warning message
    print(
        colored(
            f"[WARNING] Only use this tool against authorised targets. You are responsible for your actions!\n",
            "light_yellow",
            attrs=["bold"],
        )
    )
    time.sleep(2.5)

    # Create directories for storing outputs if they don't already exist
    os.makedirs("openvas_reports", exist_ok=True)
    os.makedirs("custom_reports", exist_ok=True)
    os.makedirs("nuclei_results", exist_ok=True)
    os.makedirs("nikto_results", exist_ok=True)
    os.makedirs("metasploit_results", exist_ok=True)
    os.makedirs("result_graphs", exist_ok=True)

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

    # Run Nuclei Scans
    update_nuclei()  # Update Nuclei templates
    nuclei_combined_output_file = run_nuclei_scans(
        nuclei_target_dir="nuclei_results", nuclei_target_file="targets.txt"
    )

    # Run Nikto Scans
    nikto_combined_output_file = run_nikto_scans(
        nikto_target_dir="nikto_results", nikto_target_file="targets.txt"
    )

    # Update Greenbone Vulnerability Manager feeds
    update_nvt()
    update_scap()
    update_cert()

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

    # Run the Exploitation Module with the obtained csv_path
    if csv_path:
        exploitedcves, incompatiblecves, reportname = run_exploit_module(
            csv_path)  # Capture counts and report path
    else:
        exploitedcves, incompatiblecves, reportname = 0, 0, None  # Default values if csv_path is not available

    # Write counts to counts.json
    counts = {
        "hosts_count": hosts_count,
        "apps_count": apps_count,
        "os_count": os_count,
        "high_count": high_count,
        "medium_count": medium_count,
        "low_count": low_count,
        "exploitedcves": exploitedcves,
        "incompatiblecves": incompatiblecves
    }
    with open('counts.json', 'w') as f:
        json.dump(counts, f)

    # Generate the report using the generated CSV report path and Nikto CSV path
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
            reportname=reportname,
            exploitedcves=exploitedcves,
            incompatiblecves=incompatiblecves,
            nikto_csv_path=nikto_combined_output_file,
            nuclei_combined_output_file=nuclei_combined_output_file,
        )
    else:
        print("Failed to generate the CSV report, skipping report generation.")

    # Calculate and print the duration of the script execution
    end_time = time.time()
    duration = end_time - start_time

    # Calculate hours, minutes, and seconds from the duration
    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    seconds = int(duration % 60)

    print(f"\nScan Duration: {hours:02d}:{minutes:02d}:{seconds:02d}")

if __name__ == "__main__":
    main()

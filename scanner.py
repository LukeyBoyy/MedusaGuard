import time
import os
import re
import argparse
import subprocess
import configparser
import xml.etree.ElementTree as ET
from base64 import b64decode
from pathlib import Path
from termcolor import colored
from gvm.connections import UnixSocketConnection
from gvm.protocols.latest import Gmp
from gvm.transforms import EtreeCheckCommandTransform
from gvm.errors import GvmError
from halo import Halo

# Makes directories for the openvas, nmap and nuclei output
os.makedirs("nmap_reports", exist_ok=True)
os.makedirs("openvas_reports", exist_ok=True)
os.makedirs("nuclei_results", exist_ok=True)

# Checks if script was executed using a non-root user
if os.getuid() != 0:
    exit(colored(
        "You need to have root privileges to run this script.\nPlease try again, this time using 'sudo'. Exiting...",
        "red"))


def update_config_file(config_path, username=None, password=None, path=None, port_list_name=None,
                       scan_config=None, scanner=None, target_name=None, target_ip=None, task_name=None):
    # Initialize the ConfigParser and read the config file
    config = configparser.ConfigParser()
    config.read(config_path)

    # Update the relevant sections based on the provided arguments
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

    # Write the changes back to the config file
    with open(config_path, 'w') as configfile:
        config.write(configfile)


def main():
    parser = argparse.ArgumentParser(
        description="Update config.ini settings.",
        epilog="""Example usage:
    sudo python3 <script_name>.py --config config.ini --username admin --password passswd --target_name router --task_name router_scan"""
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

    # Call the update function with parsed arguments
    update_config_file(args.config, args.username, args.password, args.path, args.port_list_name,
                       args.scan_config, args.scanner, args.target_name, args.target_ip, args.task_name)

    config = configparser.ConfigParser()
    config.read(args.config)

    # Configuration variables for connection to the GVM server
    path = config['connection']['path']
    username = config['connection']['username']
    password = config['connection']['password']

    # Details for the target to be scanned
    target_name = config['target']['target_name']  # Name of the target in GVM
    target_ip = config['target']['target_ip']  # IP address of the target to be scanned

    # Configuration variables for target creation
    port_list_name = config['target']['port_list_name']

    # Details for the scan task to be performed
    task_name = config['task']['task_name']  # Name of the task to be created and executed

    # Configuration variables for task creation
    scan_config = config['task']['scan_config']
    scanner = config['task']['scanner']

    # Nuclei variables
    nuclei_target_dir = "nuclei_results"
    nuclei_target_file = "targets.txt"
    max_alert_length = 102  # Maximum characters for alert messages including prefix
    alert_prefix = "[ALERT] "

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

    completion_time = time.strftime("%H:%M_%Y-%m-%d")  # Capture the completion time

    # Create results directory if it doesn't exist
    os.makedirs(nuclei_target_dir, exist_ok=True)

    # Start on Nuclei module
    print(colored(
        "--------------------------------------- Nuclei Vulnerability Scan ------------------------------------",
        attrs=['bold']))

    # Read the target IPs from the nuclei_targets.txt file
    with open(nuclei_target_file, 'r') as file:
        nuclei_targets = [line.strip() for line in file if line.strip()]

    # Define the corresponding nuclei commands
    nuclei_commands = {
        "network": "nuclei -target {} -t network/ -o {}",
        "default_login": "nuclei -target {} -t network/default-login -o {}",
        "http": "nuclei -target http://{} -o {}",
        "ssh": "nuclei -target ssh://{} -o {}",
        "ftp": "nuclei -target ftp://{} -o {}",
        "smb": "nuclei -target smb://{} -o {}"
    }

    # Create a timestamp for the combined output filename
    nuclei_timestamp = time.strftime("%Y%m%d_%H%M%S")
    nuclei_combined_output_file = os.path.join(nuclei_target_dir, f"{nuclei_timestamp}_combined.txt")

    # Spinner setup
    def nuclei_spinner_message(message):
        return Halo(text=colored(message, "white"), spinner="dots")

    # Calculate maximum message length for alerts
    max_message_length = max_alert_length - len(alert_prefix)

    # Loop through each target and execute the commands
    for nuclei_target in nuclei_targets:
        for scan_type, nuclei_command in nuclei_commands.items():
            nuclei_output_file = os.path.join(nuclei_target_dir, f"{nuclei_target}_{scan_type}.txt")
            nuclei_cmd = nuclei_command.format(nuclei_target, nuclei_output_file)
            nuclei_scan_msg = f"Running {scan_type.replace('_', ' ').capitalize()} scan on {nuclei_target}"

            nuclei_spinner = nuclei_spinner_message(nuclei_scan_msg)
            nuclei_spinner.start()

            subprocess.run(nuclei_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            nuclei_spinner.succeed(
                colored("[SUCCESS] ", "green") +
                f"{scan_type.replace('_', ' ').capitalize()} scan completed. Results saved to " +
                colored(nuclei_output_file, attrs=['bold'])
            )

            # Combine results into a single file
            with open(nuclei_output_file, 'r') as nuclei_infile, open(nuclei_combined_output_file,
                                                                      'a') as nuclei_outfile:
                for line in nuclei_infile:
                    nuclei_outfile.write(line)
                    # Check for critical, high, or medium severity in the results and print if found
                    if any(keyword in line.lower() for keyword in ['critical', 'high', 'medium']):
                        alert_message = line.strip()
                        if len(alert_message) > max_message_length:
                            alert_message = alert_message[:max_message_length - 3] + '...'
                        print(
                            colored(alert_prefix, "red", attrs=['bold']) +
                            alert_message
                        )

    # Final message after combining all files
    print(
        colored("[INFO]", "cyan") +
        " Combined output saved to " +
        colored(nuclei_combined_output_file, attrs=['bold'])
    )

    print("")

    # Remove individual output files
    try:
        print(
            colored("[INFO]", "cyan") +
            " Removed redundant nuclei output files"
        )
        for nuclei_target in nuclei_targets:
            for scan_type in nuclei_commands.keys():
                nuclei_output_file = os.path.join(nuclei_target_dir, f"{nuclei_target}_{scan_type}.txt")
                if os.path.exists(nuclei_output_file):
                    os.remove(nuclei_output_file)
    except Exception as e:
        print(
            colored(f"[ERROR] Failed to remove redundant nuclei output files: {e}", "red")
        )
    print(
        colored("[INFO]", "cyan") +
        " All Nuclei scans completed and files cleaned up\n"
    )
    # End of Nuclei module

    # Start of Nmap module
    # Output file for the Nmap results
    output_file = os.path.join("nmap_reports", f"nmap_vuln_{completion_time}")

    print(colored(
        "--------------------------------------- Namp Vulnerability Scan --------------------------------------",
        attrs=['bold']))

    def run_nmap(target_ip, output_file):
        nmap_msg = colored(f"Running Nmap vuln scans against {target_ip}", "white")
        spinner = Halo(text=nmap_msg, spinner="dots")
        spinner.start()
        # Nmap scan command nmap -sV -A --top-ports=3500 --script=vuln -oN -iL
        command = ['nmap', '-sV', '--top-ports=1000', '--script=vuln', '-T4', '-n', '-oN', output_file, '-iL', target_ip]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.stderr:
            print("Error:", result.stderr)
            return None

        nmap_spinner = colored("[SUCCESS]", "green")
        spinner.succeed(colored(colored(nmap_spinner + " Nmap scan completed.", "cyan")))

        print(
            colored(f"[INFO]", 'cyan') +
            f" Results saved to" +
            colored(f" {output_file}\n", attrs=['bold']))

        print(colored(
            "------------------------------------------ Nmap Scan Results -----------------------------------------",
            attrs=['bold']))

        # Dictionary to store whether vulnerabilities were found for each IP
        nmap_vulnerabilities = {}

        current_ip = None
        for line in result.stdout.splitlines():
            ip_match = re.match(r'Nmap scan report for (.*)', line)
            if ip_match:
                current_ip = ip_match.group(1)
                nmap_vulnerabilities[current_ip] = False
            elif 'cve' in line and current_ip:
                nmap_vulnerabilities[current_ip] = True

        # Print vulnerabilities for each IP
        for ip, has_vuln in nmap_vulnerabilities.items():
            if has_vuln:
                print(
                    colored(f"[{completion_time}]", "red", attrs=['bold']) +
                    colored(" [ALERT]", "red", attrs=['bold']) +
                    f" Vulnerabilities found on {ip}:"
                )
            else:
                print(
                    colored("[INFO]", 'cyan') +
                    f" No vulnerabilities found on {ip}."
                )

        if nmap_vulnerabilities:
            print(
                colored("[INFO]", "red") +
                f" Please refer to the output file" +
                colored(f" ({output_file})", attrs=['bold']) +
                " for information\n"
            )

        spinner.stop()

    # Run the Nmap scan and save the results to the specified file
    run_nmap(target_ip, output_file)
    time.sleep(2.5)

    # Start of Greenbone/OpenVAS module
    print(colored(
        "------------------------------------- Greenbone Vulnerability Scan -----------------------------------",
        attrs=['bold']))

    # Updating vuln feeds
    print(
        colored("[INFO]", "cyan") +
        " Updating vulnerability feeds"
    )

    def update_nvt():
        try:
            nvt_command = ["greenbone-nvt-sync"]
            nvt_msg = colored("Updating NVT feed", "white")
            spinner = Halo(text=nvt_msg, spinner="dots")
            spinner.start()
            subprocess.run(nvt_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            nvts = colored("[SUCCESS]", "green")
            spinner.succeed(colored(nvts + " NVT update successful", "white"))
            spinner.stop()
        except subprocess.CalledProcessError as e:
            print(colored(f"[ERROR] An error occured while updating the feeds: {e}", "red"))
        except Exception as e:
            print(colored(f"[ERROR] Unexpected error: {e}", "red"))

    update_nvt()

    def update_scap():
        try:
            scap_command = ["greenbone-scapdata-sync"]
            scap_msg = colored("Updating SCAP feed", "white")
            spinner = Halo(text=scap_msg, spinner="dots")
            spinner.start()
            subprocess.run(scap_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            scaps = colored("[SUCCESS]", "green")
            spinner.succeed(colored(scaps + " SCAP data update successful", "white"))
            spinner.stop()
        except subprocess.CalledProcessError as e:
            print(colored(f"[ERROR] An error occurred while updating the feeds: {e}", "red"))
        except Exception as e:
            print(colored(f"[ERROR] Unexpected error: {e}", "red"))

    update_scap()

    def update_cert():
        try:
            cert_command = ["greenbone-certdata-sync"]
            cert_msg = colored("Updating CERT feed", "white")
            spinner = Halo(text=cert_msg, spinner="dots")
            spinner.start()
            subprocess.run(cert_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            certs = colored("[SUCCESS]", "green")
            spinner.succeed(colored(certs + " CERT data update successful", "white"))
            spinner.stop()
            print(
                colored("[INFO]", "cyan") +
                " Feed updates completed\n"
            )
        except subprocess.CalledProcessError as e:
            print(colored(f"[ERROR] An error occurred while updating the feeds: {e}", "red"))
        except Exception as e:
            print(colored(f"[ERROR] Unexpected error: {e}", "red"))

    update_cert()

    def read_host_from_file(file_path):
        with open(file_path, 'r') as file:
            hosts = [line.strip() for line in file if line.strip()]
        return ','.join(hosts)

    hosts = read_host_from_file(target_ip)

    try:
        # Establish a connection to the GVM server using a Unix socket
        connection = UnixSocketConnection(path=path, timeout=500)
        transform = EtreeCheckCommandTransform()  # XML transformation to ensure proper parsing
        # Open a session with the GVM server
        with Gmp(connection=connection) as gmp:
            gmp.authenticate(username, password)  # Authenticate with the GVM server

            # Connection test, you can uncomment the following lines to test connection with the GVM server
            # version = gmp.get_version()
            # print(f'{version}\n')

            # Retrieve the list of existing targets
            targets_list = gmp.get_targets()
            targets_list_xml = ET.fromstring(targets_list)  # Parse the XML response
            targetid = None  # Initialise variable to store target ID

            # Check if target already exists by searching the target list
            for target in targets_list_xml.findall(".//target"):
                if target.find("name").text == target_name:  # Compare target names
                    targetid = target.get("id")  # Get the ID of the existing target
                    print(
                        colored("[INFO]", "cyan") +
                        f" Target {target_name} already exists with ID: {targetid}"
                    )
                    print(
                        colored("[INFO]", "cyan") +
                        " Creating task with this target"
                    )

            # If the target does not exist, create it
            if not targetid:
                print(
                    colored("[INFO]", "cyan") +
                    f" Target {target_name} does not already exist. Creating a new target"
                )
                # Creating a target
                target_response = gmp.create_target(
                    name=target_name,
                    hosts=[hosts],
                    port_list_id=port_list_name
                )
                # Extracting the new target ID from the response
                target_xml = ET.fromstring(target_response)
                targetid = target_xml.get('id')
                print(
                    colored("[INFO]", "cyan") +
                    f" Target ID is: {targetid}"
                )

                # Check if the target was created successfully
                if targetid:
                    print(
                        colored("[INFO]", "cyan") +
                        f" Target created successfully with ID: {targetid}"
                    )
                else:
                    print(colored('[ERROR] Failed to create target', 'red'))
                    exit(1)

            # Creating a new scan task
            create_task = gmp.create_task(
                name=task_name,
                config_id=scan_config,
                target_id=targetid,
                scanner_id=scanner
            )

            # Extracting task ID
            task_xml = ET.fromstring(create_task)
            taskid = task_xml.get('id')
            if taskid:
                print(
                    colored("[INFO]", "cyan") +
                    f" Task created with ID: {taskid}"
                )
            else:
                print(colored('[ERROR] Failed to create task', 'red'))
                exit(1)  # Exit the script if task creation failed

            print(
                colored("[INFO]", "cyan") +
                " Waiting for task to be ready"
            )
            time.sleep(5)  # Wait for a short period to ensure the task is ready

            # Starting a task
            start_task = gmp.start_task(
                task_id=taskid
            )

            print(
                colored("[INFO]", "cyan") +
                f" Task started successfully with ID: {taskid}\n"
            )

            # Extract report ID value from the start_task output
            report_xml = ET.fromstring(start_task)
            reportid = report_xml.find("report_id").text
            csv_reportid = report_xml.find("report_id").text

            gvm_text = colored("Scanning.", "white")
            spinner = Halo(text=gvm_text, spinner="dots")
            spinner.start()

            # While loop that checks the status of the task/scan every 2 mins
            task_status = ''
            while task_status not in ['Done', 'Stopped', 'Failed']:
                time.sleep(0.2)
                task_response = gmp.get_task(task_id=taskid)
                task_status_xml = ET.fromstring(task_response)
                task_status = task_status_xml.find('.//status').text  # Extract the status from the XML

            spinner.stop()
            gvm_spinner = colored("[SUCCESS]", "green")
            spinner.succeed(gvm_spinner + f" Scan completed, status: {task_status}")

            # If task is completed, the report will be downloaded
            if task_status == 'Done':
                completion_time = time.strftime("%H:%M:%S %Y/%m/%d")  # Capture the completion time
                print(
                    colored(f"[{completion_time}] [INFO]", "cyan") +
                    " Greenbone vulnerability scan completed\n"

                )

                print(colored(
                    "-------------------------------------------- Report Summary ------------------------------------------",
                    attrs=['bold']))

                try:
                    # Get PDF report
                    pdf_report_response = gmp.get_report(
                        report_id=reportid,
                        report_format_id="c402cc3e-b531-11e1-9163-406186ea4fc5",  # PDF report format ID
                        ignore_pagination=True,
                        details=True,
                    )

                    # Creates a timestamp
                    timestamp = time.strftime("%Y:%m:%d_%H:%M:%S")
                    # Creates the filename for the report
                    pdf_filename = os.path.join("openvas_reports", f"openvas_{task_name}_report_{timestamp}.pdf")

                    # Extracts the report content from the response
                    root = ET.fromstring(pdf_report_response)
                    report_element = root.find("report")
                    content = report_element.find(
                        "report_format").tail.strip()  # Extract the base64-encoded PDF Content
                    binary_pdf = b64decode(content.encode("ascii"))  # Decode the base64 content into binary PDF data

                    # Save the PDF to a file with the constructed filename
                    pdf_path = Path(pdf_filename).expanduser()  # Create the full path for the PDF file
                    pdf_path.write_bytes(binary_pdf)  # Write the binary data to the file
                    time.sleep(5)
                except Exception as e2:
                    print(colored(f"[ERROR] Failed to download PDF report: {e2}", "red"))

                # Report summary logic
                try:
                    # Get XML report
                    xml_report_response = gmp.get_report(
                        report_id=reportid,
                        report_format_id="a994b278-1f62-11e1-96ac-406186ea4fc5",  # XML report format ID
                        ignore_pagination=True,
                        details=True
                    )

                    def get_count_value(element, path):
                        count_element = element.find(path)
                        return int(count_element.text)

                    rep_xml = ET.fromstring(xml_report_response)
                    hosts_count = get_count_value(rep_xml, './/hosts/count')
                    os_count = get_count_value(rep_xml, './/os/count')
                    apps_count = get_count_value(rep_xml, './/apps/count')
                    high_count = 0
                    medium_count = 0
                    low_count = 0

                    for threat in rep_xml.findall('.//original_threat'):
                        level = threat.text
                        if level == "High":
                            high_count += 1
                        elif level == "Medium":
                            medium_count += 1
                        elif level == "Low":
                            low_count += 1

                    print(
                        colored("- Hosts Scanned", "cyan") +
                        colored(f"              : {hosts_count}", "white")
                    )
                    print(
                        colored("- Applications Scanned", "cyan") +
                        colored(f"       : {apps_count}", "white")
                    )
                    print(
                        colored("- Operating Systems Scanned", "cyan") +
                        colored(f"  : {os_count}", "white")
                    )

                    print(
                        colored("- High Vulnerabilities", "cyan") +
                        colored(f"       : {high_count}", "red", attrs=['bold'])
                    )
                    print(
                        colored("- Medium vulnerabilities", "cyan") +
                        colored(f"     : {medium_count}", "yellow", attrs=['bold'])
                    )
                    print(
                        colored("- Low vulnerabilities", "cyan") +
                        colored(f"        : {low_count}\n", "green", attrs=['bold'])
                    )
                except Exception as e3:
                    print(colored(f"[ERROR] Unable to print report summary: {e3}"))

                print("-" * 102)
                print(
                    colored(f"[{completion_time}] [INFO]", 'cyan') +
                    " Downloading report"
                )

                # Writes the csv file
                try:
                    time.sleep(10)

                    csv_report_format_id = "c1645568-627a-11e3-a660-406186ea4fc5"

                    # Retrieve CSV report
                    csv_report_response = gmp.get_report(
                        report_id=reportid,
                        report_format_id=csv_report_format_id,
                        ignore_pagination=True,
                        details=True,
                    )

                    csv_root = ET.fromstring(csv_report_response)
                    csv_element = csv_root.find("report")

                    if csv_element is not None:
                        csv_content = csv_element.find("report_format").tail
                        if csv_content:
                            binary_base64_encoded_csv = csv_content.encode("ascii")
                            binary_csv = b64decode(binary_base64_encoded_csv)
                            csv_filename = os.path.join("openvas_reports", f"{task_name}_report_{timestamp}.csv")
                            csv_path = Path(csv_filename).expanduser()
                            csv_path.write_bytes(binary_csv)

                            print(
                                colored("[INFO]", "cyan") +
                                f" CSV Report downloaded as" +
                                colored(f" {csv_path}", attrs=['bold'])
                            )

                except Exception as e1:
                    print(colored(f"[ERROR] Failed to download CSV report: {e1}", "red"))

                # print(colored(f'[INFO] Report downloaded as {pdf_path}\n', 'green'))
                print(
                    colored("[INFO]", "cyan") +
                    f" PDF Report downloaded as" +
                    colored(f" {pdf_path}", attrs=['bold'])
                )

                print(
                    colored("[SUCCESS]", "green") +
                    " All scans completed. Reports generated successfully"
                )
    except GvmError as e:
        print(colored(f'An error occurred: {e}', 'red'))


if __name__ == "__main__":
    main()
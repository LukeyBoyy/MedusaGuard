import os
import time
import subprocess
import xml.etree.ElementTree as ET
from termcolor import colored
from gvm.connections import UnixSocketConnection
from gvm.protocols.latest import Gmp
from gvm.errors import GvmError
from pathlib import Path
from base64 import b64decode


print_timestamp = time.strftime("%Y/%m/%d_%H:%M:%S")


def update_nvt():
    """
    Update the Network Vulnerability Tests (NVT) feed for Greenbone Vulnerability Management (GVM).

    This function runs 'greenbone-nvt-sync' to ensure that the NVT feed is up-to-date.
    It handles any exceptions that may occur during the update process.
    """
    print(colored(">>> Greenbone Vulnerability Scan", attrs=["bold"]))
    print(
        colored(f"[{print_timestamp}] [+] ", "cyan")
        + "Greenbone Vulnerability Scan Started"
    )
    try:
        # Command to update the NVT feed
        nvt_command = ["greenbone-nvt-sync"]
        nvt_msg = colored("Updating NVT feed", "white")

        print(nvt_msg)

        # Run the NVT update command with a timeout of 2700 seconds (45 minutes)
        subprocess.run(
            nvt_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=2700,
        )
        print(colored("NVT update successful", "white"))
    except subprocess.CalledProcessError as e:
        print(
            colored(f"[ERROR] An error occurred while updating the feeds: {e}", "red")
        )
    except Exception as e:
        print(colored(f"[ERROR] Unexpected error: {e}", "red"))


def update_scap():
    """
    Update the Security Content Automation Protocol (SCAP) feed for Greenbone Vulnerability Management (GVM).

    This function runs 'greenbone-scapdata-sync' to ensure that the SCAP feed is up-to-date.
    It handles any exceptions that may occur during the update process.
    """
    try:
        # Command to update the SCAP feed
        scap_command = ["greenbone-scapdata-sync"]
        scap_msg = colored("Updating SCAP feed", "white")

        print(scap_msg)

        # Run the SCAP update command with a timeout of 2700 seconds (45 minutes)
        subprocess.run(
            scap_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=2700,
        )

        print(colored("SCAP data update successful", "white"))
    except subprocess.CalledProcessError as e:
        print(
            colored(f"[ERROR] An error occurred while updating the feeds: {e}", "red")
        )
    except Exception as e:
        print(colored(f"[ERROR] Unexpected error: {e}", "red"))


def update_cert():
    """
    Update the CERT feed for Greenbone Vulnerability Management (GVM).

    This function runs 'greenbone-certdata-sync' to ensure that the CERT feed is up-to-date.
    It handles any exceptions that may occur during the update process.
    """
    try:
        # Command to update the CERT feed
        cert_command = ["greenbone-certdata-sync"]
        cert_msg = colored("Updating CERT feed", "white")

        print(cert_msg)

        # Run the CERT update command with a timeout of 2700 seconds (45 minutes)
        subprocess.run(
            cert_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=2700,
        )

        print(colored("CERT data update successful", "white"))
        print(colored("[INFO]", "cyan") + " Feed updates completed\n")
    except subprocess.CalledProcessError as e:
        print(
            colored(f"[ERROR] An error occurred while updating the feeds: {e}", "red")
        )
    except Exception as e:
        print(colored(f"[ERROR] Unexpected error: {e}", "red"))


def read_host_from_file(file_path):
    """
    Read a list of host IPs from a file and returns them as a comma-separated string.

    Args:
        file_path (str): Path to the file containing the list of host IPs.

    Returns:
        str: A comma-separated string of host IPs.
    """
    with open(file_path, "r") as file:
        # Read each line, strip whitespace, and ignore empty lines
        hosts = [line.strip() for line in file if line.strip()]
        # Join the hosts into a comma-separated string
    return ",".join(hosts)


def openvas_scan(
    path,
    username,
    password,
    target_name,
    target_ip,
    port_list_name,
    task_name,
    scan_config,
    scanner,
):
    """
    Perform an OpenVAS scan using Greenbone Vulnerability Management (GVM).

    This function handles the entire process of scanning a target, including creating the target and task,
    starting the scan, monitoring its progress, and retrieving the results.
    The scan results are saved in both PDF and CSV formats.

    Args:
        path (str): Path to the Unix socket for GVM connection.
        username (str): Username for the GVM server.
        password (str): Password for the GVM server.
        target_name (str): Name of the target to be scanned.
        target_ip (str): Path to the file containing target IPs or a single IP.
        port_list_name (str): Port list ID for target configuration.
        task_name (str): Name of the task to be created and executed.
        scan_config (str): Scan configuration ID.
        scanner (str): Scanner ID.

    Returns:
        tuple: A tuple containing:
            - csv_path (str): Path to the CSV report.
            - task_name (str): Name of the task.
            - hosts_count (int): Number of hosts scanned.
            - high_count (int): Number of high severity vulnerabilities found.
            - medium_count (int): Number of medium severity vulnerabilities found.
            - low_count (int): Number of low severity vulnerabilities found.
            - apps_count (int): Number of applications scanned.
            - os_count (int): Number of operating systems scanned.

    Raises:
        GvmError: If an error occurs while interacting with the GVM.
        Exception: For any other unexpected errors.
    """
    # Read the target IPs from the specified file
    hosts = read_host_from_file(target_ip)
    number_of_hosts = len(hosts.split(",")) if hosts else 0

    # Calculate the timeout based on the number of hosts (e.g., 3 hosts -> 3 hours)
    # Ensure at least a minimum timeout (e.g., 1 hour) to handle small numbers
    if number_of_hosts > 0:
        timeout_hours = number_of_hosts
    else:
        timeout_hours = 1  # Default to 1 hour if no hosts are specified

    connection_timeout = timeout_hours * 3600  # Convert hours to seconds

    try:
        # Establish a Unix socket connection to the GVM server
        # A high timeout value is set to prevent a timeout error during long operations
        connection = UnixSocketConnection(path=path, timeout=connection_timeout)
        with Gmp(connection=connection) as gmp:
            # Authenticate with the GVM using provided credentials
            gmp.authenticate(username, password)

            # Retrieve existing targets and check if the target already exists
            targets_list = gmp.get_targets()
            targets_list_xml = ET.fromstring(targets_list)
            targetid = None

            for target in targets_list_xml.findall(".//target"):
                if target.find("name").text == target_name:
                    targetid = target.get("id")
                    print(
                        colored("[INFO]", "cyan")
                        + f" Target {target_name} already exists with ID: {targetid}"
                    )
                    print(colored("[INFO]", "cyan") + " Creating task with this target")

            if not targetid:
                # Create a new target if it doesn't exist
                print(
                    colored("[INFO]", "cyan")
                    + f" Target {target_name} does not already exist. Creating a new target"
                )
                target_response = gmp.create_target(
                    name=target_name, hosts=[hosts], port_list_id=port_list_name
                )
                target_xml = ET.fromstring(target_response)
                targetid = target_xml.get("id")
                print(colored("[INFO]", "cyan") + f" Target ID is: {targetid}")

            if targetid:
                # Create a task for the target
                create_task = gmp.create_task(
                    name=task_name,
                    config_id=scan_config,
                    target_id=targetid,
                    scanner_id=scanner,
                )
                task_xml = ET.fromstring(create_task)
                taskid = task_xml.get("id")
                print(colored("[INFO]", "cyan") + f" Task created with ID: {taskid}")
            else:
                print(colored("[ERROR] Failed to create task", "red"))
                exit(1)

            print(colored("[INFO]", "cyan") + " Waiting for task to be ready")
            time.sleep(5)  # Wait for the task to be ready

            start_task = gmp.start_task(task_id=taskid)
            print(
                colored("[INFO]", "cyan")
                + f" Task started successfully with ID: {taskid}\n"
            )

            # Extract the report ID from the response
            report_xml = ET.fromstring(start_task)
            reportid = report_xml.find("report_id").text

            gvm_text = colored("Scanning...", "white")

            print(gvm_text)

            # Monitor the status of the task until it's completed
            task_status = ""
            while task_status not in ["Done", "Stopped", "Failed"]:
                # Checks the status of the scan every 30 seconds, increase this value if timeout errors persist
                time.sleep(30)
                task_response = gmp.get_task(task_id=taskid)
                task_status_xml = ET.fromstring(task_response)
                task_status = task_status_xml.find(".//status").text

            print(colored(f"Scan completed, status: {task_status}", "white"))

            if task_status == "Done":
                completion_time = time.strftime("%H:%M:%S %Y/%m/%d")
                print(
                    colored(f"[{completion_time}] [INFO]", "cyan")
                    + " Greenbone vulnerability scan completed\n"
                )
                print(
                    colored(
                        ">>> Report Summary",
                        attrs=["bold"],
                    )
                )

                # Report summary logic
                try:
                    # Get XML report
                    xml_report_response = gmp.get_report(
                        report_id=reportid,
                        report_format_id="a994b278-1f62-11e1-96ac-406186ea4fc5",  # XML report format ID
                        ignore_pagination=True,
                        details=True,
                    )

                    def get_count_value(element, path):
                        """
                        Helper function to extract count values from XML.

                        Args:
                            element (Element): XML element to search within.
                            path (str): XPath to the desired count element.

                        Returns:
                            int: The count value extracted from the XML.
                        """
                        count_element = element.find(path)
                        return int(count_element.text)

                    rep_xml = ET.fromstring(xml_report_response)
                    hosts_count = get_count_value(rep_xml, ".//hosts/count")
                    os_count = get_count_value(rep_xml, ".//os/count")
                    apps_count = get_count_value(rep_xml, ".//apps/count")
                    high_count = 0
                    medium_count = 0
                    low_count = 0

                    # Count vulnerabilities by severity
                    for threat in rep_xml.findall(".//original_threat"):
                        level = threat.text
                        if level == "High":
                            high_count += 1
                        elif level == "Medium":
                            medium_count += 1
                        elif level == "Low":
                            low_count += 1

                    # Display the report summary
                    print(
                        colored("- Hosts Scanned", "cyan")
                        + colored(f"              : {hosts_count}", "white")
                    )
                    print(
                        colored("- Applications Scanned", "cyan")
                        + colored(f"       : {apps_count}", "white")
                    )
                    print(
                        colored("- Operating Systems Scanned", "cyan")
                        + colored(f"  : {os_count}", "white")
                    )

                    print(
                        colored("- High Vulnerabilities", "cyan")
                        + colored(f"       : {high_count}", "red", attrs=["bold"])
                    )
                    print(
                        colored("- Medium vulnerabilities", "cyan")
                        + colored(f"     : {medium_count}", "yellow", attrs=["bold"])
                    )
                    print(
                        colored("- Low vulnerabilities", "cyan")
                        + colored(f"        : {low_count}\n", "green", attrs=["bold"])
                    )
                except Exception as e:
                    print(colored(f"[ERROR] Unable to print report summary: {e}"))

                print(
                    colored(f"[{completion_time}] [INFO]", "cyan")
                    + " Downloading report"
                )

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
                    pdf_filename = os.path.join(
                        "openvas_reports", f"openvas_{task_name}_report_{timestamp}.pdf"
                    )

                    # Extracts the report content from the response
                    root = ET.fromstring(pdf_report_response)
                    report_element = root.find("report")
                    content = report_element.find(
                        "report_format"
                    ).tail.strip()  # Extract the base64-encoded PDF Content
                    binary_pdf = b64decode(
                        content.encode("ascii")
                    )  # Decode the base64 content into binary PDF data

                    # Save the PDF to a file with the constructed filename
                    pdf_path = Path(
                        pdf_filename
                    ).expanduser()  # Create the full path for the PDF file
                    pdf_path.write_bytes(
                        binary_pdf
                    )  # Write the binary data to the file
                    time.sleep(5)
                    print(
                        colored("[INFO]", "cyan")
                        + f" PDF Report downloaded as"
                        + colored(f" {pdf_path}", attrs=["bold"])
                    )
                except Exception as e:
                    print(colored(f"[ERROR] Failed to download PDF report: {e}", "red"))

                # Writes the csv file
                try:
                    time.sleep(10)  # Wait to ensure the report is ready

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
                            csv_filename = os.path.join(
                                "openvas_reports", f"{task_name}_report_{timestamp}.csv"
                            )
                            csv_path = Path(csv_filename).expanduser()
                            csv_path.write_bytes(binary_csv)

                            print(
                                colored("[INFO]", "cyan")
                                + f" CSV Report downloaded as"
                                + colored(f" {csv_path}", attrs=["bold"])
                            )

                            # Return the necessary information for report generation
                            return (
                                str(csv_path),
                                str(task_name),
                                hosts_count,
                                high_count,
                                medium_count,
                                low_count,
                                apps_count,
                                os_count,
                            )

                        print(
                            colored(f"[{print_timestamp}] [+]", "cyan")
                            + " Greenbone scan completed.\n"
                        )

                except Exception as e:
                    print(colored(f"[ERROR] Failed to download CSV report: {e}", "red"))
    except GvmError as e:
        # Handle GVM-specific errors
        print(colored(f"[ERROR] An error occurred: {e}", "red"))
    except Exception as e:
        # Handle any unexpected exceptions
        print(colored(f"[ERROR] An unexpected error occurred: {e}", "red"))

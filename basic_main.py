import os
import sys
import subprocess
from termcolor import colored
from logger import logger
import time  # Ensure you import time

def run_nuclei_scans(nuclei_target_dir, nuclei_target_file):
    """
    Run Nuclei scans using Docker on a list of targets and combine the results.
    This function reads target hosts from a file, runs Nuclei scans on each target
    using specified templates, combines the individual scan outputs into a single
    output file, and displays alerts for findings with certain keywords.
    Args:
        nuclei_target_dir (str): The directory where Nuclei output files will be saved.
        nuclei_target_file (str): The file containing the list of target hosts.
    """
    max_alert_length = 102  # Maximum length for alert messages
    alert_prefix = "[ALERT] "  # Prefix for alert messages

    # Generate a timestamp to append to output filenames
    nuclei_timestamp = time.strftime("%Y%m%d_%H%M%S")
    nuclei_combined_output_file = os.path.join(
        nuclei_target_dir, f"{nuclei_timestamp}_combined.txt"
    )

    # Read target hosts from the target file
    with open(nuclei_target_file, "r") as file:
        nuclei_targets = [line.strip() for line in file if line.strip()]

    # Define the Nuclei scan commands to execute using Docker container
    nuclei_commands = {
        "network": "docker run --rm -v {0}:{0} projectdiscovery/nuclei -target {1} -t network/ -o {2}",
    }

    # Run the Nuclei scan for each target
    for nuclei_target in nuclei_targets:
        for scan_type, nuclei_command in nuclei_commands.items():
            nuclei_output_file = os.path.join(nuclei_target_dir, f"{nuclei_target}_{scan_type}.txt")
            nuclei_cmd = nuclei_command.format(nuclei_target_dir, nuclei_target, nuclei_output_file)

            print(colored(f"Running {scan_type} scan on {nuclei_target}...", "white"))
            
            # Run the Nuclei scan command and stream the output in real-time
            process = subprocess.Popen(nuclei_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            # Stream output line by line
            for line in iter(process.stdout.readline, ''):
                print(line, end="")  # Print each line to the console immediately
                sys.stdout.flush()  # Ensure real-time display by flushing output

            # Wait for the process to complete
            process.wait()

            if process.returncode != 0:
                print(colored(f"Scan failed for {nuclei_target}", "red"))
            else:
                print(colored(f"Scan completed for {nuclei_target}, results saved to {nuclei_output_file}", "green"))

    # Return combined output path
    return nuclei_combined_output_file

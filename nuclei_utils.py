import os
import time
import subprocess
from termcolor import colored
from logger import logger


print_timestamp = time.strftime("%d-%m-%Y %H:%M:%S")


def run_nuclei_scans(nuclei_target_dir, nuclei_target_file):
    """
    Run Nuclei scans on a list of targets and combine the results.

    This function reads target hosts from a file, runs Nuclei scans on each target
    using specified templates, combines the individual scan outputs into a single
    output file, and cleans up the individual output files. It also displays alerts
    for findings with certain keywords.

    Args:
        nuclei_target_dir (str): The directory where Nuclei output files will be saved.
        nuclei_target_file (str): The file containing the list of target hosts.
    """
    max_alert_length = 102  # Maximum length for alert messages
    alert_prefix = "[ALERT] "  # Prefix for alert messages
    # Generate a timestamp to append to output filenames
    nuclei_timestamp = time.strftime("%Y%m%d_%H%M%S")
    # Path to the combined output file where all individual outputs will be appended
    nuclei_combined_output_file = os.path.join(
        nuclei_target_dir, f"{nuclei_timestamp}_combined.txt"
    )

    # Read target hosts from the target file, removing any empty lines
    with open(nuclei_target_file, "r") as file:
        nuclei_targets = [line.strip() for line in file if line.strip()]

    # Define the Nuclei scan commands to execute
    nuclei_commands = {
        "network": "nuclei -target {} -t network/ -o {}",
        # "http": "nuclei -target {} -t http/ -o {}",
        # "rdp": "nuclei -target rdp://{} -o {}"
        # You can add more scan types and their corresponding commands here
    }

    print(
        colored(f"[{print_timestamp}] [+] ", "cyan")
        + "Nuclei Vulnerability Scan Started"
    )
    logger.info("Nuclei vulnerability scsn started")

    # Iterate over each target and run Nuclei scans
    for nuclei_target in nuclei_targets:
        for scan_type, nuclei_command in nuclei_commands.items():
            # Path to the individual output file for this target and scan type
            nuclei_output_file = os.path.join(
                nuclei_target_dir, f"{nuclei_target}_{scan_type}.txt"
            )
            # Construct the Nuclei command for the target
            nuclei_cmd = nuclei_command.format(nuclei_target, nuclei_output_file)
            nuclei_scan_msg = colored(
                f"Running {scan_type.replace('_', ' ')} scan on {nuclei_target}...",
                "white",
            )
            logger.info(f"Running {scan_type.replace('_', ' ')} scan on {nuclei_target}")

            # Display the scan message
            print(nuclei_scan_msg, end="", flush=True)

            # Run the Nuclei scan command
            try:
                subprocess.run(
                    nuclei_cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=3600,
                    check=True,
                )
            except subprocess.CalledProcessError as e:
                print(colored(f"\n[ERROR] Scan failed: {e}", "red"))
                logger.error(f"An error occurred when scanning while scanning {nuclei_target}: {e}")

            print(
                f"\n{scan_type.replace('_', ' ').capitalize()} scan results saved to "
                + colored(nuclei_output_file, attrs=["bold"])
            )

            max_message_length = max_alert_length - len(alert_prefix)

            with open(nuclei_output_file, "r") as nuclei_infile, open(
                nuclei_combined_output_file, "a"
            ) as nuclei_outfile:
                for line in nuclei_infile:
                    nuclei_outfile.write(line)
                    if any(
                        keyword in line.lower()
                        for keyword in ["critical", "high", "medium"]
                    ):
                        alert_message = line.strip()
                        if len(alert_message) > max_alert_length:
                            alert_message = (
                                alert_message[: max_message_length - 3] + "..."
                            )
                        print(
                            colored(alert_prefix, "red", attrs=["bold"]) + alert_message
                        )
    print(
        colored("[INFO]", "cyan") +
        " Combined output saved to " +
        colored(f"{nuclei_combined_output_file}", attrs=['bold']
    )
    )
    logger.info(f"Nuclei output saved to {nuclei_combined_output_file}")

    # Clean up individual output files to save space
    try:
        logger.info("Removing individual Nuclei output files")
        print(colored("[INFO]", "cyan") + " Removing redundant Nuclei output files...")
        for nuclei_target in nuclei_targets:
            for scan_type in nuclei_commands.keys():
                nuclei_output_file = os.path.join(
                    nuclei_target_dir, f"{nuclei_target}_{scan_type}.txt"
                )
                if os.path.exists(nuclei_output_file):
                    os.remove(nuclei_output_file)
        print(colored("[INFO]", "cyan") + " Redundant Nuclei output files removed.")
        logger.info("Removed individual Nuclei output files")
    except Exception as e:
        # Handle any exceptions that occur during file deletion
        print(
            colored(
                f"[ERROR] Failed to remove redundant Nuclei output files: {e}", "red"
            )
        )
        logger.error(f"Failed to remove individual Nuclei output files: {e}")

    # Inform the user that all scans are completed and cleanup is done
    print(
        colored(f"[{print_timestamp}] [+]", "cyan")
        + " All Nuclei scans completed and files cleaned up.\n"
    )
    logger.info("All Nuclei scans completed and files cleaned up.\n")

    return nuclei_combined_output_file

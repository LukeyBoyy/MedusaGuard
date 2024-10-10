import os
import time
import subprocess
from termcolor import colored
from logger import logger


print_timestamp = time.strftime("%d-%m-%Y %H:%M:%S")


def run_nikto_scans(nikto_target_dir, nikto_target_file):
    """
    Run Nikto scan on a list of targets and combine the results.

    This function reads target hosts from a file, runs Nikto against each target,
    combines the individual scan outputs into a single CSV file, and cleans up
    the individual output files. It also returns the path to the combined output file.

    Args:
        nikto_target_dir (str): The directory where Nikto output files will be saved.
        nikto_target_file (str): The file containing the list of target hosts.

    Returns:
        str: The path to the combined Nikto CSV output file.
    """
    # Generate a timestamp to append to output filenames
    nikto_timestamp = time.strftime("%Y%m%d_%H%M%S")
    # Path to the combined output file where all individual outputs will be appended
    nikto_combined_output_file = os.path.join(
        nikto_target_dir, f"{nikto_timestamp}_combined.csv"
    )

    print(colored(">>> Nikto Vulnerability Scan", attrs=["bold"]))
    print(
        colored(f"[{print_timestamp}] [+] ", "cyan")
        + "Nikto Vulnerability Scan Started"
    )
    logger.info("Nikto vulnerability scan started")

    # Read target hosts from the target file, removing any empty lines
    with open(nikto_target_file, "r") as file:
        nikto_targets = [line.strip() for line in file if line.strip()]

    # Iterate over each target and run a Nikto scan
    for nikto_target in nikto_targets:
        # Path to the individual output file for this target
        nikto_output_file = os.path.join(
            nikto_target_dir, f"{nikto_target}_{nikto_timestamp}.csv"
        )
        # Construct the Nikto command
        nikto_cmd = f"nikto -h {nikto_target} -nointeractive -Format csv -output {nikto_output_file}"
        nikto_scan_msg = f"Running Nikto scan on {nikto_target}"
        logger.info(f"Running NIkto scan on {nikto_target}")

        print(nikto_scan_msg)

        try:
            # Run the Nikto scan command with a timeout of 3600 seconds (1 hour)
            subprocess.run(
                nikto_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=3600,
            )
            print(
                f"Nikto scan completed. Results saved to "
                + colored(nikto_output_file, attrs=["bold"])
            )
            logger.info(f"NIkto scan completed. Results saved to {nikto_output_file}")
        except subprocess.TimeoutExpired:
            print(colored(f"Nikto scan timed out for target {nikto_target}", "red"))
            logger.error(f"Nikto scan timed out for target {nikto_target}")
        except Exception as e:
            print(
                colored(f"An error occurred while scanning {nikto_target}: {e}", "red")
            )
            logger.error(f"An error occurred while scanning {nikto_target}: {e}")

    # Combine individual Nikto output files into the combined output file
    try:
        print(colored("[INFO]", "cyan") + " Combining Nikto output files")
        logger.info("Combining Nikto output files")
        with open(nikto_combined_output_file, "w") as outfile:
            for idx, nikto_target in enumerate(nikto_targets):
                nikto_output_file = os.path.join(
                    nikto_target_dir, f"{nikto_target}_{nikto_timestamp}.csv"
                )
                with open(nikto_output_file, "r") as infile:
                    if idx == 0:
                        # Write header for the first file
                        outfile.write(infile.read())
                    else:
                        # Skip the header line for subsequent files
                        next(infile)  # Skip header line
                        outfile.write(infile.read())
        print(
            colored("[INFO]", "cyan")
            + f" Combined output saved to "
            + colored(f"{nikto_combined_output_file}", attrs=["bold"])
        )
        logger.info(f"Combined output saved to {nikto_combined_output_file}")
    except Exception as e:
        print(colored(f"[ERROR] Failed to combine Nikto output files: {e}", "red"))
        logger.error(f"Failed to combine Nikto output files: {e}")

    # Remove individual Nikto output files after combining
    try:
        print(colored("[INFO]", "cyan") + " Removing individual Nikto output files")
        logger.info("Removing individual Nikto output files")
        # Inform the user that all scans are completed and cleanup is done
        print(
            colored(f"[{print_timestamp}] [+]", "cyan")
            + " All Nikto scans completed and files cleaned up.\n"
        )

        for nikto_target in nikto_targets:
            nikto_output_file = os.path.join(
                nikto_target_dir, f"{nikto_target}_{nikto_timestamp}.csv"
            )
            if os.path.exists(nikto_output_file):
                os.remove(nikto_output_file)

        logger.info("All Nikto scans completed and files cleaned up.\n")
    except Exception as e:
        # Handle any exceptions that occur during file deletion
        print(
            colored(
                f"[ERROR] Failed to remove individual Nikto output files: {e}", "red"
            )
        )
        logger.error(f"Failed to remove individual Nikto output files: {e}\n")

    # Return the path to the combined Nikto CSV output file
    return nikto_combined_output_file

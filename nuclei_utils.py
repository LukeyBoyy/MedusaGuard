import os
import time
import subprocess
from termcolor import colored
from halo import Halo


def nuclei_spinner_message(message):
    return Halo(text=colored(message, "white"), spinner="dots")

def update_nuclei():
    print(colored(
        "--------------------------------------- Nuclei Vulnerability Scan ------------------------------------",
        attrs=['bold']))
    try:
        nuclei_command = ["nuclei", "-version"]
        nuclei_msg = colored("Updating Nuclei", "white")
        spinner = Halo(text=nuclei_msg, spinner="dots")
        spinner.start()
        subprocess.run(nuclei_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        spinner.succeed(colored("Nuclei update successful", "white"))
        spinner.stop()
    except subprocess.CalledProcessError as e:
        print(colored(f"[ERROR] An error occurred while updating Nuclei: {e}", "red"))
    except Exception as e:
        print(colored(f"[ERROR] Unexpected error: {e}", "red"))

def run_nuclei_scans(nuclei_target_dir, nuclei_target_file):
    max_alert_length = 102
    alert_prefix = "[ALERT] "
    nuclei_timestamp = time.strftime("%Y%m%d_%H%M%S")
    nuclei_combined_output_file = os.path.join(nuclei_target_dir, f"{nuclei_timestamp}_combined.txt")

    with open(nuclei_target_file, 'r') as file:
        nuclei_targets = [line.strip() for line in file if line.strip()]

    nuclei_commands = {
        "network": "nuclei -target {} -t network/ -o {}"
    }

    for nuclei_target in nuclei_targets:
        for scan_type, nuclei_command in nuclei_commands.items():
            nuclei_output_file = os.path.join(nuclei_target_dir, f"{nuclei_target}_{scan_type}.txt")
            nuclei_cmd = nuclei_command.format(nuclei_target, nuclei_output_file)
            nuclei_scan_msg = f"Running {scan_type.replace('_', ' ')} scan on {nuclei_target}"

            nuclei_spinner = nuclei_spinner_message(nuclei_scan_msg)
            nuclei_spinner.start()

            subprocess.run(nuclei_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            nuclei_spinner.succeed(
                f"{scan_type.replace('_', ' ')} scan completed. Results saved to " +
                colored(nuclei_output_file, attrs=['bold'])
            )

            max_message_length = max_alert_length - len(alert_prefix)

            with open(nuclei_output_file, 'r') as nuclei_infile, open(nuclei_combined_output_file, 'a') as nuclei_outfile:
                for line in nuclei_infile:
                    nuclei_outfile.write(line)
                    if any(keyword in line.lower() for keyword in ['critical', 'high', 'medium']):
                        alert_message = line.strip()
                        if len(alert_message) > max_alert_length:
                            alert_message = alert_message[:max_message_length - 3] + '...'
                        print(colored(alert_prefix, "red", attrs=['bold']) + alert_message)

    print(colored("[INFO]", "cyan") + " Combined output saved to " + colored(nuclei_combined_output_file, attrs=['bold']))

    try:
        print(colored("[INFO]", "cyan") + " Removed redundant nuclei output files")
        for nuclei_target in nuclei_targets:
            for scan_type in nuclei_commands.keys():
                nuclei_output_file = os.path.join(nuclei_target_dir, f"{nuclei_target}_{scan_type}.txt")
                if os.path.exists(nuclei_output_file):
                    os.remove(nuclei_output_file)
    except Exception as e:
        print(colored(f"[ERROR] Failed to remove redundant nuclei output files: {e}", "red"))

    print(colored("[INFO]", "cyan") + " All Nuclei scans completed and files cleaned up\n")
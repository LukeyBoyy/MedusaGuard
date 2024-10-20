import os
import sys
import subprocess
from termcolor import colored

def run_nuclei_scan(target_url, output_dir):
    """
    Run a basic Nuclei scan on a single target using Docker.
    
    Args:
        target_url (str): The URL of the target to scan.
        output_dir (str): The directory where Nuclei output files will be saved.
    """
    # Define the Nuclei Docker command
    docker_command = f"docker run --rm -v {output_dir}:{output_dir} projectdiscovery/nuclei -target {target_url} -t network/ -o {output_dir}/nuclei_output.txt"
    
    print(f"Running Docker command: {docker_command}")

    try:
        # Run the Docker command
        result = subprocess.run(
            docker_command,
            shell=True,
            stdout=sys.stdout,
            stderr=sys.stderr,
            text=True
        )
        
        # Print the output from Docker
        print(result.stdout)
        if result.stderr:
            print(colored(result.stderr, "red"))
        
        if result.returncode != 0:
            print(colored(f"Scan failed with error code: {result.returncode}", "red"))
        else:
            print(colored(f"Scan completed successfully. Output saved to {output_dir}/nuclei_output.txt", "green"))
    
    except Exception as e:
        print(colored(f"An error occurred while running the Docker command: {e}", "red"))

if __name__ == "__main__":
    # Example target and output directory
    target_url = "http://example.com"
    output_dir = os.path.expanduser("~/medusaguard/nuclei_results")

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Run the Nuclei scan
    run_nuclei_scan(target_url, output_dir)

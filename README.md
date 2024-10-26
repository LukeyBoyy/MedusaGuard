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
5. [Getting Started Guide for Medusa Guard](#getting-started-guide-for-medusa-guard)
6. [Dependencies](#Dependencies)
7. [License](#license)
8. [Credits](#credits)

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

---

## **Getting Started Guide for Medusa Guard**
[MedusaGuard - Getting Started Guide.pdf](https://github.com/user-attachments/files/17359582/MedusaGuard.-.Getting.Started.Guide.pdf)

---

## **API Commands**

#### GVM
Used in the OpenVAS module. List of API commands:
```python
gmp.get_version()

gmp.authenticate(username, password)
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
Used in the Nuclei Module:
```python
MsfRpcClient(password, server=server, port=port, ssl=ssl) # Establishes a connection to the Metasploit RPC server with the specified credentials and connection parameters.
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

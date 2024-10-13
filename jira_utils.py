import csv
from atlassian import *

APItoken = '' 
# Insert the API token of an account specifically created for the purposes of using this module. To create the key, visit id.atlassian.com/manage-profile/security/api-tokens. 
# This script only creates tickets and the related account should only have the permissions to do this; anything else is excessive, especially noting the vulnerability in leaving an API key publically visible.
# This is used as the password for the account.

jira = Jira(
        url = '', # The url should end in .atlassian.net/
        username = '', # Username of the account created to process these tickets
        password = APItoken, # See above for details on the API token
        cloud = True)

with open('', 'r') as csvfile: # The first argument should be the file path to the OpenVAS reports, as this is what this code block is designed for.
    openvasresults = csv.DictReader(csvfile)
    for row in openvasresults:
        ip = row["IP"]
        cves = row["CVEs"]
        cvss = row["CVSS"]
        soltype = row["Solution Type"]
        nvtname = row["NVT Name"]
        specres = row["Specific Result"]
        impact = row["Impact"]
        solution = row["Solution"]
        # The above are pulled from the CSV. When attempting to replicate this, ensure that the column titles are typed in exactly.

        summary = "CVSS Score: " + cvss + " IP: " + ip + " Vulnerability Type: " + nvtname
        description = "Specific Results: \n" + specres + "\n \n Impact: \n" + impact + "\n\n Known CVEs: \n" + cves + "\n \n Solution Type: \n" + soltype + "\n \n Solution Details: \n" + solution
        # These are example text selections, pulled directly from the CSV, to fill in the details of the ticket. These can and should be modified at your discretion.

        jira.issue_create(
            fields = {
                'project': {
                    'key': '' # The issue key can be located by visiting your url.atlassian.net/jira/projects
                },
                'summary': summary,
                'description': description,
                # Insert any additional fields as required in a dictionary format. For the field names as used on Jira, they are case insensitive.
                'issuetype': {
                    "name": "Task"
                }
            }
        )
        print("Issue for " + summary + " created.")

print("Done.")

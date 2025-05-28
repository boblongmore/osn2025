# math_server.py
from mcp.server.fastmcp import FastMCP
import time
import requests
from dotenv import load_dotenv
import os

load_dotenv()

# Define the Ansible Automation Platform API URL and credentials
api_url = "https://10.236.72.62"
endpoint = "/api/controller/v2/job_templates/39/launch/"
token = os.getenv("AAP_TOKEN")

mcp = FastMCP("Math")

# Define the payload for the playbook launch (if any extra
# variables are needed) for future use
payload = {
    "extra_vars": {
        "dut": "eda-sw100"
    }
}

# Define the headers necessary for the
# API request to Ansible Automation Platform
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}


def launch_template():
    """Launch the playbook template that gathers ACL data"""
    url = api_url + "/api/controller/v2/job_templates/39/launch/"
    launch = req_helper("POST", url)
    print("Playbook launched successfully!")
    job_id = launch.json().get("id")
    print(f"Job ID: {job_id}")
    return job_id


def get_job_payload(job_id):
    status = api_url + f"/api/controller/v2/jobs/{job_id}/"
    get_status_info = req_helper("GET", status)
    while get_status_info.json().get("status") != "successful":
        print("Job is not completed yet. Waiting...")
        time.sleep(3)  # Wait for 3 seconds before checking again
        get_status_info = req_helper("GET", status)  # Refresh the job status
    output = api_url + f"/api/controller/v2/jobs/{job_id}/"
    get_output = req_helper("GET", output)
    print(get_output.json().get("artifacts").get("acl_data"))
    return get_output.json().get("artifacts").get("acl_data")


def req_helper(method, url, headers=headers):
    """
    Helper function to make HTTP requests.
    """
    try:
        response = requests.request(method, url, headers=headers, verify=False)
        response.raise_for_status()  # Raise an error for bad responses
        return response
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None


@mcp.tool()
def acl_audit():
    """Verify the functionality of an ACL
    returns the ACL object in json format"""
    job_id = launch_template()
    acl = get_job_payload(job_id)
    return acl


if __name__ == "__main__":
    mcp.run(transport="stdio")

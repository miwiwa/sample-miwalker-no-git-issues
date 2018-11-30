#!/usr/bin/env python
# Program submits PagerDuty incidents or Git issues upon request

import pip
package = 'requests'
pip.main(['install', package])

import requests
import json
import argparse
from os import environ
import subprocess
import re

# Read in argument(s)
description = 'Specify creation of incident/issue in Pagerduty and Git Issues'
   
parser = argparse.ArgumentParser(     description=__doc__)
parser.add_argument('-a','--ALERTS', nargs='+', type=str.lower, dest='ALERTS', help="Enter 'PagerDuty' and/or 'Git' to open incident/issue", required=True)

args = parser.parse_args()
alerts = args.ALERTS

# Import Pipeline environment variables 
ids_job_name = environ.get('IDS_JOB_NAME')
#ids_job_name = IDS_JOB_NAME#print(type(ids_job_name))
ids_job_id = environ.get('IDS_JOB_ID')
print(type(ids_job_id))
ids_stage_name = environ.get('IDS_STAGE_NAME')
ids_project_name = environ.get('IDS_PROJECT_NAME')
ids_url = environ.get('IDS_URL')
git_url = environ.get('GIT_URL')
task_id = environ.get('TASK_ID')
pipeline_id = environ.get('PIPELINE_ID')
pipeline_stage_id = environ.get('PIPELINE_STAGE_ID')
pipeline_stage_name = environ.get('PIPELINE_STAGE_NAME')
pipeline_stage_input_job_id = environ.get('PIPELINE_STAGE_INPUT_JOB_ID')
pipeline_initial_stage_execution_id = environ.get('PIPELINE_INITIAL_STAGE_EXECUTION_ID')
workspace = environ.get('WORKSPACE')
github_token = environ.get('github_accessToken')

print("GIT_URL:", git_url)

# Load toolchain json to dict for parsing
toolchain_json = "%s/_toolchain.json" % workspace

with open(toolchain_json) as f:
    data = json.load(f)

ids_region_id = data['region_id']

instance_id = [i['instance_id'] for i in data["services"] if 'pipeline' in i['broker_id']]
ids_instance_id = instance_id[0]

pipeline_base_url = "https://console.bluemix.net/devops/pipelines/" 
pipeline_full_url = pipeline_base_url + pipeline_id + "/" + pipeline_stage_id +  "/" + ids_job_id + "?env_id=" + ids_region_id


def trigger_incident():
	# Function creates request to create new PagerDuty incident and submits
    
    # Parse dict for PagerDuty parameters
    try:
        pd_service_id = [i['parameters']['service_id'] for i in data["services"] if 'pagerduty' in i['broker_id']]
        pd_api_key = [i['parameters']['api_key'] for i in data["services"] if 'pagerduty' in i['broker_id']]
        pd_user_email = [i['parameters']['user_email'] for i in data["services"] if 'pagerduty' in i['broker_id']]
    	
        api_key = pd_api_key[0]
        service_id = pd_service_id[0]
        user_email = pd_user_email[0]
    except (KeyError, IndexError):
        print("ERROR: Pager Duty is not configured correctly with the toolchain")
        return 1
     
	# Develop request to create incident through API
    url = 'https://api.pagerduty.com/incidents'
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/vnd.pagerduty+json;version=2',
        'Authorization': 'Token token={token}'.format(token=api_key),
        'From': user_email
    }

    payload = {
        "incident": {
            "type": "incident",
            "title": "Job: " + ids_job_name + " in Stage: " + ids_stage_name + " and Project: " + ids_project_name + " failed" ,
            "service": {
                "id": service_id,
                "type": "service_reference"
            },
            "body": {
                "type": "incident_body",
                "details":  pipeline_full_url
            }
          }
        }
	
	# Send request to PagerDuty
    r = requests.post(url, headers=headers, data=json.dumps(payload))
    
    code=r.status_code
    
    # Check if request was successful. If not successful then fail the job   
    if code != 201:
    	print("ERROR: PagerDuty incident request did not complete successfully")
        exit()
    else:
		print("PagerDuty incident request created successfully")
		
def trigger_issue(title, body=None, labels=None):
	# Function creates request to create Git Issue and submits
	
    api_base_url = "https://api.github.ibm.com/"
    
    
    
    git_repo_name = re.search(r'(.*)/(.*)',git_url).group(2).split('.')[0]
    git_repo_owner = re.search(r'(.*)/(.*)',git_url).group(1)
  
    
    try:
      repo_owner = [i['parameters']['owner_id'] for i in data["services"] if 'git' in i['broker_id']]
      git_repo_owner = repo_owner[0]
     # git_repo_name = repo_name[0]
    except (KeyError, IndexError):
      print("ERROR: Git Issues is not configured correctly with the toolchain")
      return 1
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "token " + github_token
    }

    issue = {'title': title,
             'body': body,
             'labels': labels}
    
    # Specifies URL for github api
    url = api_base_url + "repos/" + git_repo_owner + "/" + git_repo_name + "/issues"
    r = requests.post(url, headers=headers, data=json.dumps(issue))
  	
    if r.status_code != 201:
        print("status code:",r.status_code)
        print("status text:",r.text)
        print("status_content:",r.content)
    	print ('ERROR: Could not create Git Issue {0:s}'.format(title))
        exit()   
    else:
        print ('Successfully created Git Issue {0:s}'.format(title))

if __name__ == '__main__':	
	print("=============================")
	print("Creating alerts")
	
	if all(alert_type in alerts for alert_type in ('incident', 'issue')):		
		trigger_incident()	
		trigger_issue("Job: " + ids_job_name + " in Stage: " + ids_stage_name + " and Project: " + ids_project_name + " failed", pipeline_full_url, ['bug'])	
	elif 'incident' in alerts:		
		trigger_incident()
	elif 'issue' in alerts:
		trigger_issue("Job: " + ids_job_name + " in Stage: " + ids_stage_name + " failed", pipeline_full_url, ['bug'])
	else:
		print("Alert type was not specified in call")

	
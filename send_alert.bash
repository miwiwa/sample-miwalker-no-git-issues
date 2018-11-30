#!/bin/bash
#
#  Sends alert with link to failing job to Pager Duty or Git Issue depending on pipeline config
#

enable_alerts=()

# exclude file contains list of alerts not to send
filename="notification.exclude.conf"

# Retrieve line from exclusion list for current job
var=$(grep $IDS_JOB_NAME $filename | sed 's:[^;]*/\(.*\):\1:')

# Check length of array for loop
num=$(echo $var | tr -cd ';' | wc -c)

# Loop through line and add exclusion to array
for ((i=2;i<=$num+1;i++)); do
        alert_type=$(echo "\"$var"\ | cut -d ";" -f $i"")
        enable_alerts+=$alert_type
done

# Call python script to send alerts based on content of array
if [[ " ${enable_alerts[@]} " =~ "no-pagerduty" ]] && [[ " ${enable_alerts[@]} " =~ "no-git" ]] ; then
    echo "PagerDuty and Git Issues not configured for this job"
    exit 0
elif [[ " ${enable_alerts[@]} " =~ "no-pagerduty" ]]; then
	echo "Creating git issue"
	/usr/bin/python create_alert.py -a issue
elif [[ " ${enable_alerts[@]} " =~ "no-git" ]]; then
	echo "Creating Pager Duty incident"
	/usr/bin/python create_alert.py -a incident
else
	echo "Creating both Pager Duty incident and Git issue"
	/usr/bin/python create_alert.py -a incident issue
fi

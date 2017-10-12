#!/bin/bash
# Script helps to trigger copy and deploy API using DeployNow.

originalEnvironment="demo"
newEnvironment=$originalEnvironment-001

response=$(curl -k -i -H 'Authorization:chaitanya.katari@reancloud.com:Deploynow1!' -H 'Content-Type: application/json' -X POST -d '{ "deployConfig": { "emailToNotify": "", "deployEmailTemplateName": "", "destroyEmailTemplateName":""}, "copyConfig": { "newEnvironment": "'"$newEnvironment"'", "originalEnvironment": "'"$originalEnvironment"'" } }' 'https://34.210.5.43/DeployNow/rest/env/copyanddeploy' -D /tmp/copyAndDeploy.log )

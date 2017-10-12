#!/usr/bin/env python
""" copy existing environment to new one """
import sys
import json
import time
import re
import argparse
import requests


from utils.deploy_utils import flatten_config, region_to_short, report_15ln_error
from utils.log_utils import Wyndhamlog

PATH_TO_BLUEPRINTS = "Environments/"


def line_and_status(lineno, r, logger):
    logger.info('Line %d', lineno)
    logger.info('r: %s', str(r))
    logger.info('status code: %d', r.status_code)


def main():
    """ copy an existing environment to a new one and deploy the new environment to REANDeploy """
    logger = Wyndhamlog('copy_and_deploy').logger
    parser = argparse.ArgumentParser()
    parser.add_argument('config_file')
    parser.add_argument('deploy_param_file')
    parser.add_argument('original_environment')
    parser.add_argument('new_environment')
    parser.add_argument('--label', default='current')
    args = parser.parse_args()

    config_file = args.config_file
    deploy_param_file = args.deploy_param_file
    original_environment = args.original_environment
    new_environment = args.new_environment
    label = args.label

    deploy_parameters = json.load(open(deploy_param_file, "r"))
    version_timestamp = str(int(time.time() * 100.0))
    configuration = json.load(open(config_file, "r"))
    configuration = flatten_config(configuration)

    new_environment = new_environment + "-" + str(int(time.time()))

    logger.info('new environment is %s', new_environment)

    provider_name = "trainee" + \
        region_to_short(deploy_parameters['aws_region'])

    headers = {
        'Authorization': configuration["deploy_username"] + ":" + configuration["deploy_password"]
    }

    # Will use original_environment to get blueprint file name for right now
    # Probably ought to be layer at some point instead of original_environment something like app layer,web layer

    logger.info('Reading blueprint for %s', original_environment)
    bpfilename = PATH_TO_BLUEPRINTS + original_environment + \
        ".blueprint.reandeploy"
    with open(bpfilename, 'r') as f:
        bpdata = f.read()
    bpdj = json.loads(bpdata)

    # Walk the data looking for the Input Variables.
    # assume one environment per blueprint here, use 0th environment

    for res in bpdj['environments'][0]['resources']:
        if res['name'] == "Input Variables":
            invarstr = res['attributes']['input_variables']
    # We can update this string and add it back in to our payload
            invar = json.loads(invarstr)
    # Overlay our params on top of the ones in the blueprint
            newinvar = dict(list(invar.items()) +
                            list(deploy_parameters.items()))
            newinvar['layer_version'] = version_timestamp
    # put it back together
            invarstr = json.dumps(newinvar)
            res['attributes']['input_variables'] = invarstr

    bpdata = json.dumps(bpdj)

    logger.info("Prepping blueprint for import")
    bpfiledata = {'file': ('filenamegoesherefakeisfine', bpdata)}
    r = requests.post(configuration["deploy_server"] +
                      "/DeployNow/rest/env/import/blueprint/prepare", headers=headers,
                      files=bpfiledata)
    line_and_status(109, r, logger)
    if r.status_code != 200:
        logger.error('prepare returned status code %d', r.status_code)
        sys.exit(1)

    prepped = r.json()

    # Now we are prepped
    logger.info("Prepped. Updating name and provider id.")

    preppy = prepped[0]           # json is a list and we need the first one

    # We will need to set the importConfig.name and .description before importing
    # Output from prep contains [{"exportedEnvironment":{...},
    # "importConfig":{...} }]
    preppy['importConfig']['name'] = new_environment

    # We need to walk this and find the provider whose name matches our provider_name
    # prep output contains:
    # importConfig:{selectableProviders:["name":"string","id":int,...]}

    selProvs = preppy['importConfig']['selectableProviders']
    newprov = [prov['id']
               for prov in selProvs if prov['name'] == provider_name]
    if len(newprov) != 1:
        logger.error("didn't find one provider named: %s", provider_name)
        sys.exit(1)

    preppy['importConfig']['providerId'] = newprov[0]

    logger.info("Found provider id %s, importing", newprov[0])

    r = requests.post(configuration["deploy_server"] +
                      "/DeployNow/rest/env/import/multiple", headers=headers,
                      json=prepped)

    line_and_status(145, r, logger)
    if r.status_code != 200:
        logger.error("import returned status code %d", r.status_code)
        sys.exit(1)

    # Now we are imported
    logger.info('imported; deploying')
    dnow_env_created = r.json()['environments'][0]  # Assume there's only one
    dnow_new_env_modified = dnow_env_created['modifiedOn']
    dnow_new_env_id = dnow_env_created['id']

    deployheaders = headers
    deployheaders['headerEnvId'] = str(dnow_new_env_id)
    deployheaders['modifiedOn'] = str(dnow_new_env_modified)

    call_data = {
        "deployConfig": {
            "environmentId": dnow_new_env_id,
            "emailToNotify": "chaitanya.katari@reancloud.com",
            "deployEmailTemplateName": "deploy_successful.html",
            "destroyEmailTemplateName": "destroy_started.html",
        }
    }

    r = requests.post(configuration["deploy_server"] +
                      "/DeployNow/rest/env/deploy/" + str(dnow_new_env_id), headers=deployheaders,
                      json=call_data)

    line_and_status(174, r, logger)
    # Now we are prepped, imported, and deployed
    response_object = json.loads(r.content)

    logger.info('response object:%s', str(response_object))

    deploy_env_id = response_object["config"]["envId"]
    status = response_object["status"]

    logger.info('deploy environment ID: %d', deploy_env_id)
    logger.info('deploy status: %s', status)

    while status == "DEPLOYING":
        r = requests.get(configuration["deploy_server"] +
                         "DeployNow/rest/env/" + str(deploy_env_id), headers=headers)
        line_and_status(205, r, logger)
        status = json.loads(r.content)["status"]

        logger.info("Environment %d is %s", deploy_env_id, status)
        if status == "DEPLOYING":
            time.sleep(10)

    if status != "DEPLOYED":
        report_15ln_error(logger, configuration, deploy_env_id, headers)
        sys.exit(1)

    r = requests.get(configuration["deploy_server"] +
                     "DeployNow/rest/env/deploy/" + str(deploy_env_id), headers=headers)

    line_and_status(220, r, logger)
    output = get_output(json.loads(r.content))

    if output is None:
        logger.error('Could not find Output object')
        sys.exit(1)

    logger.info("Other attributes: %s", json.dumps(
        output[0]["otherAttributes"]))


if __name__ == "__main__":
    main()

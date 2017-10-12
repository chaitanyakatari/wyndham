import sys
import boto3
import requests


def flatten_config(configs):
    flat_config = {}
    for config in configs:
        print config
        try:
            flat_config[config["key"]] = str(config["value"])
        except:
            try:
                flat_config[config["Key"].split('/')[-1]] = config["Value"]
            except:
                print "Cannot build param for : " + config
    return flat_config


def region_to_short(region_name):
    region_split = region_name.split('-')
    if len(region_split) != 3:
        print 'Invalid region supplied, region should be a proper AWS formatted region, ie. us-west-2'
        return False
    return region_split[0] + region_split[1][:1] + region_split[2][:1]


def eip_to_allocid(region_name, eip):
    session = boto3.Session(region_name=region_name)
    ec2 = session.client('ec2')
    filters = [{'Name': 'domain', 'Values': ['vpc']}]
    resp = ec2.describe_addresses(PublicIps=[eip], Filters=filters)
    addresses = resp['Addresses']
    if len(addresses) < 1:
        print('Failed to find address')
        sys.exit(1)
    allocid = addresses[0]['AllocationId']
    return allocid


def create_eip(region_name):
    session = boto3.Session(region_name=region_name)
    ec2 = session.client('ec2')
    resp = ec2.allocate_address(Domain='vpc')
    return resp


def release_eip(region_name, eipid):
    session = boto3.Session(region_name=region_name)
    ec2 = session.client('ec2')
    resp = ec2.release_address(AllocationId=eipid)
    return resp


def report_15ln_error(logger, configuration, deploy_env_id, headers):
    logger.error("Environment failed to destroy. Checking logs.")
    r = requests.get(configuration["deploy_server"] +
                     "DeployNow/rest/env/deploy/resource/" +
                     str(deploy_env_id) + "/-1", headers=headers)
    logger.error("Last 15 lines:")

    logger.error('\n'.join(r.text.splitlines()[-16:-1]))
    logger.error("Full logs available from: ")
    logger.error(configuration["deploy_server"] + "#/home/dnow/" +
                 str(deploy_env_id))

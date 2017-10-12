#!/usr/bin/env python

import json
import argparse

from utils.deploy_utils import flatten_config
from utils.log_utils import Wyndhamlog


def main():
    """ build a parameters.json file from config and list of params. """

    logger = Wyndhamlog('copy_and_deploy').logger

    parser = argparse.ArgumentParser()
    parser.add_argument('config_file')
    parser.add_argument('param_file')
    args = parser.parse_args()

    parameters = json.load(open(args.param_file, "r"))
    configuration = json.load(open(args.config_file, "r"))
    logger.info('parameters: %s', str(parameters))
    logger.info('configuration: %s', str(configuration))

    parameters = flatten_config(parameters)
    configuration = flatten_config(configuration)

    logger.info('aws_region: %s', parameters["aws_region"])

    deploy_parameters = open("deploy_parameters.json", "w")
    deploy_parameters.write(json.dumps(parameters))
    deploy_parameters.close()


if __name__ == "__main__":
    main()

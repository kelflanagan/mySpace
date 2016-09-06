from __future__ import print_function

import boto3
import github
import httplib
import json
import string
import time
import urllib


def build_aws_services(cfg):
    info = {}
    service_name = cfg['name']
    
    return True, info


""" service_GET_request() service the http GET method for the root resource
parameters: event which contains the passed parameters if any.
returns: a list of all installed services
"""
def service_GET_request(event):
    obj = {
        "test" : "we made it new",
        "next" : "who knows"
        }
    return obj


""" service_POST_request servies the http POST method on the root resource.
parameters: event which contains the passed parameters if any.
returns: True for success and False for failure. A service is installed as a
result of the call.
"""
def service_POST_request(event):
    service = {}
    # reject requests with the incorrect payload
    if len(event.keys()) != 5:
        raise Exception('Server')
    # collect information from payload
    if 'service_name' in event:
        service['name'] = event['service_name']
    else:
        raise Exception('Server')
    if 'github_service_repo_owner' in event:
        service['owner'] = event['github_service_repo_owner']
    else:
        raise Exception('Server')
    if 'github_service_repo' in event:
        service['repo'] = event['github_service_repo']
    else:
        raise Exception('Server')

    # get files from repo
    # get service config file
    success, service_cfg = github.get_zipfile(
        service['name'] + '.cfg', 
        service['repo'], 
        service['owner']
        )
    if success:
        cfg = json.loads(service_cfg)
    else:
        raise Exception('Server')

    # API file
    success, service_api = github.get_zipfile(
        service['name'] + '.api', 
        service['repo'], 
        service['owner']
        )
    if success:
        api = json.loads(service_api)
    else:
        raise Exception('Server')

    # lambda file
    success, service_lambda = github.get_zipfile(
        service['name'] + '.zip', 
        service['repo'], 
        service['owner']
        )
    if not success:
        raise Exception('Server')

    success, service_info =  build_aws_services(cfg)
    if not success:
        raise Exception('Server')
    
    return service_info


""" mySpace() is installed when a new mySpace is created. It is them used to
list installed services, install new services, and delete services that are no 
longer desired.
"""
def mySpace(event, context):
    # test to see if called via API
    if 'resource_path' in event:
        if event['resource_path'] == '/':
            if event['http_method'] == 'GET':
                return service_GET_request(event)
            elif event['http_method'] == 'POST':
                return service_POST_request(event)
            else:
                raise Exception('MethodNotAllowed')
        else:
            raise Exception('NotFound')

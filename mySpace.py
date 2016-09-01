from __future__ import print_function

import boto3
import github
import httplib
import json
import string
import time
import urllib

""" deal_with_API_request receives the calling event dictionary and the name of
the services state table.
"""
def deal_with_API_request(event, state_table):
    service = {}
    if event['http_method'] == 'GET': 
        if event['resource_path'] == '/':
            obj = {
                "test" : "we made it new",
                "next" : "who knows"
                }
            return obj

    if event['http_method'] == 'POST':
        if event['resource_path'] == '/':
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
            service_cfg = github.get_file(
                service['name'] + '.cfg', 
                service['repo'], 
                service['owner']
                )

            return service

        else:
            raise Exception('NotFound')
    # should never get here
    raise Exception('MethodNotAllowed')


""" mySpace() is installed when a new mySpace is created. It is them used to
list installed services, install new services, and delete services that are no 
longer desired.
"""
def mySpace(event, context):
    # test to see if called via API
    if 'resource_path' in event:
        return deal_with_API_request(event, context.function_name)

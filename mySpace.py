from __future__ import print_function

import string
import json
import boto3
import httplib
import time
import urllib
import iot

""" deal_with_API_request receives the calling event dictionary and the name of
the services state table.
"""
def deal_with_API_request(event, state_table):
    if event['http_method'] == 'GET': 
        if event['resource_path'] == '/':
            obj = {
                "test" : "we made it",
                "next" : "who knows"
                }
            return obj
"""            
    if event['http_method'] == 'PUT':
        if event['resource_path'] == '/desired_temperature':
            # get state
            state = get_service_state(state_table)
            if state == None:
                raise Exception('Server Error')

            dts = json.loads(state['desired_temperatures'])
            for item in dts:
                if item in event:
                    dts[item] = event[item]
            
            valid = update_service_state(
                state_table, 
                'desired_temperatures', 
                json.dumps(dts), 
                'S'
                )        
            if not valid:
                raise Exception('Server Error')
            return    
        else:
            raise Exception('NotFound')
"""    
    if event['http_method'] == 'POST':
        if event['resource_path'] == '/':
            # get state
            state = get_service_state(state_table)
            if state == None:
                raise Exception('Server Error')

            dts = json.loads(state['desired_temperatures'])
            for item in event:
                if item != 'resource_path' and item != 'http_method':
                    dts[item] = event[item]

            valid = update_service_state(
                state_table, 
                'desired_temperatures', 
                json.dumps(dts), 
                'S'
                )        
            if not valid:
                raise Exception('Server Error')
            return    
        else:
            raise Exception('NotFound')
    # should never get here
    raise Exception('MethodNotAllowed')
"""    
    if event['http_method'] == 'DELETE':
        if event['resource_path'] == '/desired_temperature':
            # get state
            state = get_service_state(state_table)
            if state == None:
                raise Exception('Server Error')

            dts = json.loads(state['desired_temperatures'])
            for item in event:
                if item != 'resource_path' and item != 'http_method':
                    if item in dts:
                        del dts[item]
            
            valid = update_service_state(
                state_table, 
                'desired_temperatures', 
                json.dumps(dts), 
                'S'
                )        
            if not valid:
                raise Exception('Server Error')
            return    
        else:
            raise Exception('NotFound')
"""            



""" mySpace() is installed when a new mySpace is created. It is them used to
list installed services, install new services, and delete services that are no 
longer desired.
"""
def mySpace(event, context):
    # test to see if called via API
    if 'resource_path' in event:
        return deal_with_API_request(event, context.function_name)

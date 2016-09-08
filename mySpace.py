from __future__ import print_function

import aws
import boto3
import github
import httplib
import json
import string
import time
import urllib


""" install_sns_services() installs an SNS topic for each topic listed in the 
input paramter. Each topic is namespaced with the api_name as a prefix.
If topic exists it is not recreated, but included in return
parameters: topics, SNS topics to create
returns: dictionary of SNS topic names and ARNs
"""
def install_sns_services(sns_services, api_name):
    topic_list = {}
    # create SNS topics
    for topic in sns_services['topics']:
        # create namespace topic
        topic_name = (
            api_name
            + '_'
            + topic['topic_name']
            )

        topic_arn = aws.create_sns_topic(topic_name)
        if topic_arn != None:
            topic_list[topic_name] = topic_arn
        else:
            return False, None
    
    return True, topic_list


""" install_dynamodb_services() installs database tables
parameters: tables (an array of JSON objects) to be created
            api_name
returns: list of dbs created
"""
def install_dynamodb_services(tables, api_name):
    print("Got here")
    print("Got here")
    # get list of tables
    table_list = aws.list_dynamodb_tables()
    if table_list == None:
        return False, None

    # iterate through tables to create
    for table in tables:
        # namespace table
        table_name = (
            api_name + 
            '_' 
            + table['table_name']
            )

        if table_name not in table_list:
            # create table
            table_arn = aws.create_dynamodb_table(
                table_name,
                table['primary_key']
                )
            if table_arn == None:
                return False, None

            # wait for table to be created
            while aws.get_dynamodb_table_status(table_name) != 'ACTIVE':
                print(".")

            print("+++++++")
            # add items to table
            for item in table['table_items']:
                success = aws.put_dynamodb_item(
                    table_name,
                    item['item_name'],
                    item['item_type'],
                    item['item_value']
                    )
                if not success:
                    return False, None
        else:
            table_arn = aws.get_dynamodb_table_arn(table_name)
            if table_arn == None:
                return False, None
            
    return True, {'table_arn' : table_arn}


""" install_aws_services() reads through the configuration (cfg) file
and performs the tasks defined. The api_name is used to namespace items
parameters: cfg (JSON formatted configuration file and api_name
"""
def install_aws_services(cfg, api_name):
    if 'aws_services' not in cfg:
        False, None
    services_to_install = cfg['aws_services'].keys()

    # perform tasks for each service and deal with lambda function last
    if 'sns' in services_to_install:
        success, sns_topics = install_sns_services(
            cfg['aws_services']['sns'], 
            api_name
            )
        if not success:
            return False, None

    if 'dynamodb' in services_to_install:
        success, db_list = install_dynamodb_services(
            cfg['aws_services']['dynamodb']['tables'], 
            api_name
            )
        if not success:
            return False, None

#        success = install_dynamodb_services(cfg['aws_services']['dynamodb'])
#    if 'lambda' in services_to_install:
#        success = install_lambda_services(cfg['aws_services']['dynamodb'])

    return True, db_list


""" service_GET_request() service the http GET method for the root resource
parameters: event which contains the passed parameters if any.
            api_name
returns: a list of all installed services
"""
def service_GET_request(event, api_name):
    obj = {
        "test" : "we made it new",
        "next" : "who knows"
        }
    return obj


""" service_POST_request servies the http POST method on the root resource.
parameters: event which contains the passed parameters if any.
            api_name
returns: True for success and False for failure. A service is installed as a
result of the call.
"""
def service_POST_request(event, api_name):
    service = {}
    service_info = {}
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

    success, service_info =  install_aws_services(cfg, api_name)
    if not success:
        raise Exception('Server')
    
    return service_info


""" mySpace() is installed when a new mySpace is created. It is them used to
list installed services and install new services.
"""
def mySpace(event, context):
    # test to see if called via API
    if 'resource_path' in event:
        if event['resource_path'] == '/':
            if event['http_method'] == 'GET':
                return service_GET_request(event, context.function_name)
            elif event['http_method'] == 'POST':
                return service_POST_request(event, context.function_name)
            else:
                raise Exception('MethodNotAllowed')
        else:
            raise Exception('NotFound')

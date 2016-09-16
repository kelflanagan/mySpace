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


""" install_dynamodb_services() installs database tables and associated items
parameters: tables (JSON array describing tables and items to be created)
            api_name (to namespace the table)
returns: list of tables and associated arns created
"""
def install_dynamodb_services(tables, api_name):
    table_arn_list = {}
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
                time.sleep(1)

            # add items to table
            for item in table['table_items']:
                success = aws.update_dynamodb_item(
                    table_name,
                    table['primary_key'],
                    table['primary_key_type'],
                    table['primary_key_value'],
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
            
        # add table to list to return
        table_arn_list[table_name] = table_arn

    return True, table_arn_list


""" install_lambda_services() installs one or more lambda functions to process
the needs of the service being installed.
parameters: 
returns: 
"""
def install_lambda_services(lambda_functions, api_name, github_info):
    list_of_roles = aws.list_roles()
    # create functions
    for function in lambda_functions:
        # find arn for lambda execution role
        role_name = api_name + function['role']
        if role_name in list_of_roles:
            role_arn = list_of_roles[role_name]
        else:
            return False, None

        print(role_name)
        # create namespace topic
        function_name = (
            api_name
            + '_'
            + function['function_name']
            )

        print(function_name)
        # lambda file

        print("getting code from github")
        success, function_code = github.get_zipfile(
            function['lambda_zip_file'],
            github_info['repo'], 
            github_info['owner']
            )
        if not success:
            return False, None
        print("got code")

        print("creating function")
        function_arn = aws.create_function(
            function_name,
            function['handler'],
            function['code_language'],
            role_arn, 
            function_code, 
            function['description']
            )
        if function_arn == None:
            return False, None

        # add triggers if any
        if 'triggers' in function:
            for trigger in function['triggers']:
                topic_arn = aws.subscribe_to_sns_topic(
                    api+name + '_' + trigger['topic_name'],
                    function_arn
                    )
                if topic_arn == None:
                    return False, None
                    
    return True, {'arn' : topic_arn }


""" install_aws_services() reads through the configuration (cfg) file
and performs the tasks defined. The api_name is used to namespace items
parameters: cfg (JSON formatted configuration file, api_name, and 
github (a dictionary with github owner and repo information)
"""
def install_aws_services(cfg, api_name, github):
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

    if 'lambda' in services_to_install:
        success, function_name = install_lambda_services(
            cfg['aws_services']['lambda']['functions'],
            api_name,
            github
            )
        if not success:
            return False, None

    return True, function_name


""" service_GET_request() service the http GET method for the root resource
parameters: event which contains the passed parameters if any.
            api_name
returns: a list of all installed services
"""
def service_GET_request(event, api_name):
    return event
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
        print('wrong number of elements in payload')
        raise Exception('Server')
    # collect information from payload
    if 'service_name' in event:
        service['name'] = event['service_name']
    else:
        print('no service name in payload')
        raise Exception('Server')
    if 'github_service_repo_owner' in event:
        service['owner'] = event['github_service_repo_owner']
    else:
        print('no repo owner in payload')
        raise Exception('Server')
    if 'github_service_repo' in event:
        service['repo'] = event['github_service_repo']
    else:
        print('no repo name in payload')
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
        print('unable to get configuration file from github')
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
        print('unable to get api file from github')
        raise Exception('Server')


    success, service_info =  install_aws_services(cfg, api_name, service)
    if not success:
        print('unable to install services')
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

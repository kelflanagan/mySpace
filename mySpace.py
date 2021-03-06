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
returns: True on success and False on failure
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
            return False
    
    return True


""" install_dynamodb_services() installs database tables and associated items
parameters: tables (JSON array describing tables and items to be created)
            api_name (to namespace the table)
returns: True on success and False on failure
"""
def install_dynamodb_services(tables, api_name):
    table_arn_list = {}
    # get list of tables
    table_list = aws.list_dynamodb_tables()
    if table_list == None:
        return False

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
                return False

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
                    return False
        else:
            table_arn = aws.get_dynamodb_table_arn(table_name)
            if table_arn == None:
                return False
            
    return True


""" install_lambda_services() installs one lambda function to process
the needs of the service being installed.
parameters: function (JSON from config file)
            api_name
            github_info
returns: lambda_arn
"""
def install_lambda_services(function, api_name, github_info):
    list_of_roles = aws.list_roles()

    # find arn for lambda execution role
    role_name = api_name + function['role']
    if role_name in list_of_roles:
        role_arn = list_of_roles[role_name]
    else:
        return None

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
        return None
    print("got code")

    print("creating function")
    timeout = 20
    function_arn = aws.create_function(
        function_name,
        function['handler'],
        function['code_language'],
        role_arn, 
        function_code, 
        function['description'],
        timeout
        )
    if function_arn == None:
        return None

    # add triggers if any
    if 'triggers' in function:
        for trigger in function['triggers']:
            if trigger['source'] == 'sns':
                topic_arn = aws.subscribe_to_sns_topic(
                    api_name + '_' + trigger['name'],
                    function_arn
                    )
                if topic_arn == None:
                    return None
            elif trigger['source'] == 'scheduled':
                success = schedule_lambda(
                    api_name + '_' + trigger['name'],
                    trigger['rate'],
                    function_arn
                    )
                if not success:
                    return None
                    
    return function_arn


""" install_aws_services() reads through the configuration (cfg) file
and performs the tasks defined. The api_name is used to namespace items
parameters: cfg (JSON formatted configuration file, api_name, and 
github (a dictionary with github owner and repo information)
"""
def install_aws_services(cfg, api_name, github):
    if 'aws_services' not in cfg:
        return None
    services_to_install = cfg['aws_services'].keys()

    # perform tasks for each service and deal with lambda function last
    if 'sns' in services_to_install:
        success = install_sns_services(
            cfg['aws_services']['sns'], 
            api_name
            )
        if not success:
            return None

    if 'dynamodb' in services_to_install:
        success = install_dynamodb_services(
            cfg['aws_services']['dynamodb']['tables'], 
            api_name
            )
        if not success:
            return None

    if 'lambda' in services_to_install:
        function_arn = install_lambda_services(
            cfg['aws_services']['lambda'],
            api_name,
            github
            )
        if function_arn == None:
            return None

    return function_arn


""" install_service_api() installs resources and connects methods to associated
lambda function.
parameters: api (JSON formatted swagger file
            api_name
returns: True on success and False on failure
"""
def install_service_api(api, function_arn, api_name):
    # lame check
    if 'swagger' not in api:
        return False

    # determine api_id
    api_list = aws.list_apis()
    if api_list == None:
        return False
    if api_name not in api_list:
        return False

    # get api_role_arn
    api_role_name = api_name + '_' + 'api_invoke_lambda'
    role_list = aws.list_roles()
    if role_list == None:
        return False
    if api_role_name not in role_list:
        return False
    api_role_arn = role_list[api_role_name]

    # get region from function_arn
    region = string.split(function_arn, ':')[3]

    # fix a few things in the definition object
    api['info']['title'] = api_name
    
    # things that need to be done
    # 1. uri fields need to point to the lambda function created above
    # 2. credentials field needs to point to role identified above

    # form uri value
    uri_value = (
        'arn:aws:apigateway:' 
        + region
        + ':lambda:path/2015-03-31/functions/'
        + function_arn
        + '/invocations'
        )
    # write value into api object in the uri location for each method
    # also write api_role_arn into the credentials value
    api_gw_int = 'x-amazon-apigateway-integration'
    for path in api['paths'].keys():
        for method in api['paths'][path].keys():
            print('doing path {} with method {}'.format(path, method))
            api['paths'][path][method][api_gw_int]['uri'] = uri_value
            api['paths'][path][method][api_gw_int]['credentials'] = api_role_arn

    new_api_id = aws.put_api(api, api_list[api_name])
    if new_api_id == None:
        return False

    # deploy API
    prod_id = aws.add_api_deployment(api_name, new_api_id)
    if prod_id == None:
        return False

    return True


""" service_GET_request() service the http GET method for the root resource
parameters: event which contains the passed parameters if any.
            api_name
returns: a list of all installed services
"""
def service_GET_request(api_name):
    # get id of api
    api_list = aws.list_apis()
    if api_name not in api_list:
        return None
    api_id = api_list[api_name]

    api = boto3.client('apigateway')
    # get list of resources in associated with API
    resource_list = aws.list_api_resources(api_id)

    return resource_list


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
        return False
    # collect information from payload
    if 'service_name' in event:
        service['name'] = event['service_name']
    else:
        print('no service_name in payload')
        return False
    if 'github_service_repo_owner' in event:
        service['owner'] = event['github_service_repo_owner']
    else:
        print('no github_service_repo_owner in payload')
        return False
    if 'github_service_repo' in event:
        service['repo'] = event['github_service_repo']
    else:
        print('no github_service_repo in payload')
        return False

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
        return False

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
        return False

    function_arn = install_aws_services(cfg, api_name, service)
    if function_arn == None:
        print('unable to install services')
        return False

    success = install_service_api(api, function_arn, api_name)
    if not success:
        print('unable to install API')
        return False
    
    return True


""" mySpace() is installed when a new mySpace is created. It is them used to
list installed services and install new services.
"""
def mySpace(event, context):
    # test to see if called via API
    if 'resource_path' in event:
        if event['resource_path'] == '/':
            if event['http_method'] == 'GET':
                return service_GET_request(context.function_name)
            elif event['http_method'] == 'POST':
                if service_POST_request(event, context.function_name):
                    return
                else:
                    raise Exception('Server')
            else:
                raise Exception('MethodNotAllowed')
        else:
            raise Exception('NotFound')

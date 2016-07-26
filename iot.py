import boto3

""" raise_event() takes three arguments
    topic - string
    message - dict
    subject - string
    requester - string
    
    the message and subject are published to the appropriate topic
"""
def raise_event(topic, message, subject, requester):
    message['requester'] = requester
    sns = boto3.client('sns')
    response = sns.publish(
        TopicArn = topic,
        Message = json.dumps(message),
        Subject = subject
    )
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        print(subject + ' raised')
        print(message)
        return True
    else:
        raise_exception(
            'raise event in desired_temperature',
            'Unable to raise ' + subject + ' event'
        )
        return False
    
    
""" raise_exceotion() has two parameter
        function_name - string
        message - string
    
    the function_name: message are posted to the exception topic
"""
def raise_exception(function_name, message):
    print('Exception: ' + function_name + ': ' + message)
    sns = boto3.client('sns')
    response = sns.publish(
        TopicArn = "arn:aws:sns:us-west-2:356335180012:exception",
        Message = '{"Exception" : "' + function_name + ': ' + message + '"}',
        Subject = "Exception"
    )
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        return True
    else:
        return False


"""get_service_state takes a table name as a parameter and acquires the state of
the service from a dynamoDB for use by the function during its execution. The 
dictionary returned from dynamoDb looks somehting like this

    {
        "key1" : {"type1" : value1},
        "key2" : {"type2" : value2}
    }

The loop at the end of this method iterates over this dictionary and transforms
it to the following,

    {
        "key1" : value1,
        "key2" : value2
    }
"""
def get_service_state(table_name):
    db = boto3.client('dynamodb')
    # find the item labelled 'service_state'
    response = db.get_item(
        TableName=table_name,
        Key={
            'state' : {'S' : 'service_state'}
        }
    )
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        items = response['Item']
        for k, v in items.iteritems():
            items[k] = items[k][v.keys()[0]]
        return items
    else:
        raise_exception(
            table_name, 
            'DynamoDB Read Failure'
        )
        return None          


""" update_service_state() takes four arguments
    table_name - string
    item_name - string
    item_value - string
    value_type - string 'S' | 'N' | 'BOOL' or other dynamoDB types
    
    the item_name is updated to the item_value
"""
def update_service_state(table_name, item_name, item_value, value_type):
    db = boto3.client('dynamodb')
    response = db.update_item(
        TableName = table_name,
        Key = {
            'state' : {'S' : 'service_state'}
        },
        UpdateExpression = (
            'set ' + item_name + ' = :iv'
        ),
        ExpressionAttributeValues = {
            ':iv' : {value_type : item_value}
        }
    )
    # test for failure
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        return True
    else:
        raise_exception(
            'google_access_token',
            'DynamoDB Update Failure'
        )
        return False

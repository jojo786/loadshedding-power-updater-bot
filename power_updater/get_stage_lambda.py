import time
import requests
from bs4 import BeautifulSoup
import boto3
import os

dynamodb = boto3.resource('dynamodb')

def GetLoadsheddingStage():
    """ Return the current Loadshedding Stage
    0 = No load shedding
    1-3 = Stage 1-3
    Eskom responds with a single number
    1 = No load shedding
    2 = Stage 1
    3 = Stage 2
    4 = Stage 3
    """

    timestamp=str(int(time.time()*1000))
    stage = requests.get("https://loadshedding.eskom.co.za/LoadShedding/GetStatus?_="+timestamp)
    soup_stage = BeautifulSoup(stage.content, "html.parser")
    print (soup_stage)
    load_stage = int(soup_stage.string) - 1
        
    print("Loadshedding stage:" + str(load_stage))

    return load_stage



def WriteToDB(area, load_stage):
    load_table = dynamodb.Table(os.environ["PowerUpdaterTableName"])
    try:
        print("Update to Dynamo")
        response = load_table.update_item(
        Key={
             'area': area
       },
        UpdateExpression="set load_stage = :load_stage",
        ExpressionAttributeValues={
            ':load_stage': load_stage
        },
    )
    except:
        print("ERROR CANT UPDATED, so doing Put to Dynamo")
        response = load_table.put_item(
        Item={
            'area': area,
            'load_stage': load_stage
       }
    )

def lambda_handler(event, context):
    
    #See if this is a bedrock agent invocation
    print(event)
    try:
        """This function handles requests for the load shedding tool.

        Parameters:
        event (dict): The details and metadata for the request
        context (dict): additional context for the request

        Returns:
        response (dict): The response for the tool
        """
        actionGroup = event['actionGroup']
        function = event['function']
        parameters = event.get('parameters', [])
        session_attributes = event.get('sessionAttributes', {})
        area = None
        stage = None
        responseBody = None
        
        for param in parameters:
            if param["name"] == "area":
                area = param["value"]
            if param["name"] == "stage":
                stage = param["value"]

        # agent = event['agent']
        actionGroup = event['actionGroup']
        function = event['function']
        parameters = event.get('parameters', [])
        session_attributes = event.get('sessionAttributes', {})

        if function == 'GetLoadsheddingStage': 
            print("Get Loadshedding Stage")
            load_stage = GetLoadsheddingStage() 
            responseBody = {
                    'TEXT': {
                        "body": f"Load shedding stage is: {load_stage}"
                    }
                }

        action_response = {
            'actionGroup': actionGroup,
            'function': function,
            'functionResponse': {
                'responseBody': responseBody
            }
        }

        function_response = {'response': action_response, 'messageVersion': event['messageVersion']}
        #logger.info("Response: {}".format(function_response))

        return function_response
    except:
        print("NOT Bedrock Agent invocation")
      
    #A normal Telegram command or Step Function invocation  
    load_stage = GetLoadsheddingStage()
    if load_stage > -1: #sometimes eskom loads negative numbers, so ignore
        WriteToDB('Buccleuch', load_stage)

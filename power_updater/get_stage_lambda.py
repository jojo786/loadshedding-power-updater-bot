import time
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import boto3
import os

dynamodb = boto3.resource('dynamodb', 'af-south-1')
load_table = dynamodb.Table(os.environ["PowerUpdaterTableName"])

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
    load_stage = GetLoadsheddingStage()
    if load_stage > -1: #sometimes eskom loads negative numbers, so ignore
        WriteToDB('Buccleuch', load_stage)

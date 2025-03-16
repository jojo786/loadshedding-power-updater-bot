import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import boto3
import os

dynamodb = boto3.resource('dynamodb')
try:
    load_table = dynamodb.Table(os.environ["PowerUpdaterTableName"])
except:
    print("ERROR: Cannot load the DynamoDB table. Make sure the table name is correct in the environment variable.")

def GetLoadsheddingSchedule(stage):
    print ("Getting Schedule for stage " + str(stage))

    #hard coded for Buccleuch
    schedule = requests.get("https://loadshedding.eskom.co.za/LoadShedding/GetScheduleM/1020715/"+str(stage)+"/Gauteng/2808")

    # parse the whole page
    soup = BeautifulSoup(schedule.content, "html.parser")

    #1. Find just the daily schedule, which contains the load-shedding dates and times
    daily_schedule = soup.find_all("div", class_="scheduleDay")
    
    schedule = {}

    for day in daily_schedule:
        #print(type(day))
        #print (day)
        if isinstance(day, NavigableString):
            #print(day.a.string)
            continue
        if isinstance(day, Tag) and day is not None:
            load_dates = day.find_all("div", class_="dayMonth")
            for date in load_dates:
                load_date = date.get_text(strip=True)
                print("Date: " + load_date)
                load_times = day.select("a")
                #print("Times on this date: " + str(len(load_times)))
                for time in load_times:
                    load_time = time.text
                    print("Time: "+ load_time)
                    if time == load_times[0]:
                        #print("1st time")
                        schedule[load_date] = load_time
                    else: 
                        #print("2nd time")
                        schedule[load_date] = schedule[load_date] + ", " + load_time
    
    sorted(schedule.items(), reverse=True)
    print("after sorting:....")
    print(schedule)
    return schedule

def WriteToDB(area, schedule):
    print("Schedule size: " + str(len(schedule)))
    if len(schedule) > 0:
        print("Update to Dynamo")
        response = load_table.update_item(
            Key={
                'area': area
            },
            UpdateExpression="set schedule = :schedule",
            ExpressionAttributeValues={
                ':schedule': schedule
            },
        )
    
def getStage():
    print ("Getting Stage from DynamoDB")
    response = load_table.get_item(Key={'area': 'Buccleuch'})
    #print (response)
    load_stage = response['Item']['load_stage']
    return load_stage
       

def lambda_handler(event, context):
    #See if this is a bedrock agent invocation
    print("GetSchedule: lambda_handler")
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

        if function == 'GetLoadsheddingSchedule':
            print("Get Loadshedding Schedule")
            schedule = GetLoadsheddingSchedule(stage)
            responseBody = {
                    'TEXT': {
                        "body": f"Load shedding schedule is: {schedule}"
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
    stage = getStage()
    schedule = GetLoadsheddingSchedule(stage)
    WriteToDB('Buccleuch', schedule)

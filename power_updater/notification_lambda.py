import requests
import boto3
import os
import datetime

dynamodb = boto3.resource('dynamodb')
load_table = dynamodb.Table(os.environ["PowerUpdaterTableName"])
TelegramBotToken = os.environ['TelegramBotToken']
TelegramChatID = os.environ['TelegramChatID']

today = datetime.datetime.now()
tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)

def PostToTelegram_Schedule(area, load_stage, schedule):
    print ("PostToTelegram_Schedule")
    print(schedule)
    
    try:
        schedule_today = schedule[today.strftime("%a, %d %b")]['S']
    except:
        schedule_today = "NO LOADSHEDDING"
        
    try:
        schedule_tomorrow = schedule[tomorrow.strftime("%a, %d %b")]['S']
    except:
        schedule_tomorrow = "NO LOADSHEDDING"

    if int(load_stage) > 0:
        #print(schedule[today.strftime("%a, %d %b")]['S'])
        load_message = (area + " Loadshedding Notice \n"
        "Stage " + str(load_stage) + "  \n"
        "The load shedding schedule for today is as follows: \n" 
        " " + schedule_today + "  \n" +
        "The load shedding schedule for tomorrow is as follows: \n" 
        " " + schedule_tomorrow)

        telegram_response = requests.post(
                url='https://api.telegram.org/bot' + TelegramBotToken + '/sendMessage',
                data={'chat_id': TelegramChatID, 'text': load_message}).json()
        print(telegram_response)
    else:
        print("Stage 0 - no need to send a schedule")

def PostToTelegram_Stage(area, load_stage):

    if int(load_stage) == 0:
       load_stage = "0 (No Loadshedding)"
        
    load_message = (area + " Loadshedding Notice \n"
        "Eskom has now moved to stage " + str(load_stage) + "  \n")

    telegram_response = requests.post(
            url='https://api.telegram.org/bot' + TelegramBotToken + '/sendMessage',
            data={'chat_id': TelegramChatID, 'text': load_message}).json()
    print(telegram_response)


def ProcessDynamoStreamEvent(event):
    for record in event['Records']:
        #print (record)
        area = record['dynamodb']['NewImage']['area']['S']

        try:
            print("trying to read from Dynamo Event Stream")
            load_stage = record['dynamodb']['NewImage']['load_stage']['N']
            print("Load stage: " + str(load_stage))
            PostToTelegram_Stage(area, load_stage)
        except Exception as err:
            print("Exception: ProcessDynamoStreamEvent")
            print (err)
            #load_stage = record['dynamodb']['OldImage']['load_stage']['N']
            
        try:   
            schedule = record['dynamodb']['NewImage']['schedule']
        except:
            schedule = record['dynamodb']['OldImage']['schedule']

        PostToTelegram_Schedule(area, load_stage, schedule['M'])

def CheckSchedule():
    print ("CheckSchedule")
    response = load_table.get_item(Key={'area': 'Buccleuch'})
    print (response)
    area = response['Item']['area']
    load_stage = response['Item']['load_stage']
    schedule = response['Item']['schedule']

    PostToTelegram_Schedule(area, load_stage, schedule)

def lambda_handler(event, context):
    print("Event: " )
    print(event)
    try:
        print("Trying to see if this is a DynamoStreamEvent")
        if event['Records'][0]['eventSource'] == 'aws:dynamodb':
            ProcessDynamoStreamEvent(event)
    except Exception as err:
        print("Exception: lambda_handler")
        print (err)
        print("this is a EventEngineEvent event (cron) or manual testing")
        #if event['source'] == 'aws.events':
        CheckSchedule()

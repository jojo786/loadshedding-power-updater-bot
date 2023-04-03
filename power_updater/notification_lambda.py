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
        print("trying to read the today schedule with NO 'S' ")
        schedule_today = schedule[today.strftime("%a, %d %b")]

        #check to see if one of the load-shedding times has already passed, so it can be excluded from the schedule
        schedule_today_temp = ''
        for time in schedule_today.split(","):
            start_time, stop_time = time.split("-")
        
            if stop_time.strip() > today.strftime("%H:%M"):
                schedule_today_temp += (start_time +" - " + stop_time + "\n")

        schedule_today = schedule_today_temp
    except:
        try:
            print("trying to read the today schedule with 'S' ")
            schedule_today = schedule[today.strftime("%a, %d %b")]['S']
        except:
            print("no schedule set for today ")
            schedule_today = "NO LOADSHEDDING"

    try:
        print("trying to read the tomorrow schedule with NO 'S' ")
        schedule_tomorrow = schedule[tomorrow.strftime("%a, %d %b")]
    except:
        try:
            print("trying to read the tomorrow schedule with 'S' ")
            schedule_tomorrow = schedule[tomorrow.strftime("%a, %d %b")]['S']
        except:
            print("no schedule set for tomorrow ")
            schedule_tomorrow = "NO LOADSHEDDING"

    if int(load_stage) > 0:
        #print(schedule[today.strftime("%a, %d %b")]['S'])
        load_message = (area + " Loadshedding Notice \n"
        "Stage " + str(load_stage) + "  \n"
        "The loadshedding schedule for today - " + today.strftime("%a, %d %b") + ": \n" 
        " " + schedule_today + "  \n" +
        "The loadshedding schedule for tomorrow - " + tomorrow.strftime("%a, %d %b") + ": \n" 
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
        + today.strftime("%a, %d %b") + "  \n"
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

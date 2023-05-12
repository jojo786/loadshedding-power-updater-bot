import requests
import boto3
import os
from datetime import datetime, timedelta
import json

dynamodb = boto3.resource('dynamodb')
load_table = dynamodb.Table(os.environ['PowerUpdaterTableName'])
lambda_client = boto3.client('lambda')
get_schedule = os.environ['PowerUpdaterGetScheduleFunction']
TelegramBotToken = os.environ['TelegramBotToken']
TelegramChatID = os.environ['TelegramChatID']

today = datetime.now() + timedelta(hours=2) #AWS Cape Town region runs on GMT, which is 2 hours behind SA.
tomorrow = datetime.now() + timedelta(days=1)
TimeFormat = "%H:%M"

def PostToTelegram_Schedule(area, load_stage, schedule):
    print ("PostToTelegram_Schedule")
    print(schedule)
    
    schedule_today = ''
    schedule_today_temp = ''

    try:
        print("trying to read the today schedule WITH 'S' ")
        schedule_today = schedule[today.strftime("%a, %d %b")]['S']
    except:
        try:
            print("trying to read the today schedule with NO 'S' ")
            schedule_today = schedule[today.strftime("%a, %d %b")]
        except:
             print("could NOT read the today schedule with NO 'S' ")
    finally:
        if not schedule_today.strip(): #for certain stages, like stage 1, there are no loadshedding on some days
            schedule_today = 'NO LOADSHEDDING\n'
        else:
            #pretty print with new lines
            for time in schedule_today.split(","): #tokenise on , then - 
                start_time, stop_time = time.split("-")
                #check to see if one of the loadshedding times has already passed, so it can be excluded from the schedule
                if ((start_time.strip() > today.strftime(TimeFormat)) or (stop_time.strip() > today.strftime(TimeFormat))):
                    #calculate duration of each slot
                    tdelta = datetime.strptime(stop_time.strip(), TimeFormat) - datetime.strptime(start_time.strip(), TimeFormat)
                    print (tdelta)
                    if (tdelta > timedelta(hours=4)): #if the duration of any the loadshedding times is greater than 4 hours, then include duration in the message
                        schedule_today_temp += (start_time +" - " + stop_time + " (" + str(int(datetime.strftime(datetime.strptime(str(tdelta), "%H:%M:%S"), "%H"))) + " hours)" + "\n")
                    else:
                        schedule_today_temp += (start_time +" - " + stop_time + "\n")

        schedule_today = schedule_today_temp
        if not schedule_today: #if all the time slots have passed
            schedule_today = 'NO LOADSHEDDING\n'
         
    schedule_tomorrow = ''
    schedule_tomorrow_temp = ''

    try:
        print("trying to read the tomorrow schedule WITH 'S' ")
        schedule_tomorrow = schedule[tomorrow.strftime("%a, %d %b")]['S']
    except:
        try:
            print("trying to read the tomorrow schedule with NO 'S' ")
            schedule_tomorrow = schedule[tomorrow.strftime("%a, %d %b")]
        except:
            print("could NOT read the tomorrow schedule with NO 'S' ")
    finally:
        if not schedule_tomorrow.strip(): #for certain stages, like stage 1, there are no loadshedding on some days
            schedule_tomorrow = 'NO LOADSHEDDING'
        else:
            #pretty print with new lines
            for time in schedule_tomorrow.split(","): #tokenise on , then - 
                start_time, stop_time = time.split("-")
                #calculate duration of each slot
                tdelta = datetime.strptime(stop_time.strip(), TimeFormat) - datetime.strptime(start_time.strip(), TimeFormat)
                print (tdelta)
                #if the stop time is in the next day
                #tday, ttime = str(tdelta).split(",")
                #print (ttime)
                if (tdelta > timedelta(hours=4)): #if the duration of any the loadshedding times is greater than 4 hours, then include duration in the message
                    schedule_tomorrow_temp += (start_time +" - " + stop_time + " (" + str(int(datetime.strftime(datetime.strptime(str(tdelta), "%H:%M:%S"), "%H"))) + " hours)" + "\n")
                else:
                    schedule_tomorrow_temp += (start_time +" - " + stop_time + "\n")

        schedule_tomorrow = schedule_tomorrow_temp
    

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

def PostToTelegram_StageChange(area, load_stage):

    if int(load_stage) == 0:
       load_stage = "0 (NO LOADSHEDDING)"
        
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
            new_load_stage = record['dynamodb']['NewImage']['load_stage']['N']
            print("New Load stage: " + str(new_load_stage))
            old_load_stage = record['dynamodb']['OldImage']['load_stage']['N']
            print("Old Load stage: " + str(old_load_stage))
            
            #Only post to telegram if the stage has changed
            if not (old_load_stage == new_load_stage):
                PostToTelegram_StageChange(area, new_load_stage)
                
                #Invoke get_schedule_lambda function sync to make sure we pull the latest schedule from Eskom for the new stage
                lambda_client.invoke(FunctionName=get_schedule, 
                     InvocationType='RequestResponse',
                     Payload=json.dumps({}))
                #read the new schedule from DDB
                response = load_table.get_item(Key={'area': 'Buccleuch'})
                schedule = response['Item']['schedule']
                
                PostToTelegram_Schedule(area, new_load_stage, schedule['M'])
        except Exception as err:
            print("Exception: ProcessDynamoStreamEvent")
            print (err)
             

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
        print("Trying to see if this is a DynamoStreamEvent") #if this is a DynamoStreamEvent, then the stage has been updated in Dynamo, so we need to check if the stage has changed. 
        if event['Records'][0]['eventSource'] == 'aws:dynamodb':
            ProcessDynamoStreamEvent(event)
    except Exception as err:
        print("Exception: lambda_handler - this is a EventEngineEvent event (cron) or manual testing")
        CheckSchedule() #this is a regular scheduled event, so get the stage and scheduel from Dynamo, and post to Telegram.

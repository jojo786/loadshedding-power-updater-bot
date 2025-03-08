import requests
import boto3
import os
from datetime import datetime, timedelta
import json
from aws_lambda_powertools.utilities import parameters

StackName = os.environ['StackName']

# Initialize boto3 clients
ssm = boto3.client('ssm')
lambda_client = boto3.client('lambda')
dynamodb = boto3.resource('dynamodb')

load_table = dynamodb.Table(os.environ['PowerUpdaterTableName'])
get_schedule = os.environ['PowerUpdaterGetScheduleFunction']

# Get the Telegram bot token from Parameter Store
ssm_provider = parameters.SSMProvider()
TelegramBotToken = ssm_provider.get('/'+StackName+'/telegram/prod/bot_token', decrypt=True)
TelegramChatID = ssm_provider.get('/'+StackName+'/telegram/prod/chat_id', decrypt=True)


today = datetime.now() + timedelta(hours=2) #AWS Cape Town region runs on GMT, which is 2 hours behind SA (GMT+2).
tomorrow = datetime.now() + timedelta(days=1)
TimeFormat = "%I:%M %p" #12 hour format, with AM/PM

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
                #strip out leading and tailing empty spaces
                start_time = start_time.strip()
                stop_time = stop_time.strip()

                #convert from 24 hour format to 12 hour format
                start_time = datetime.strftime(datetime.strptime(start_time, "%H:%M"), TimeFormat)
                stop_time = datetime.strftime(datetime.strptime(str(stop_time), "%H:%M"), TimeFormat)
                                
                if True: 
                    #calculate duration of each slot
                    tdelta = datetime.strptime(stop_time, TimeFormat) - datetime.strptime(start_time, TimeFormat)
                    print (tdelta)
                    if (tdelta > timedelta(hours=4)): #if the duration of any the loadshedding times is greater than 4 hours, then include duration in the message
                        schedule_today_temp += (start_time +" to " + stop_time + " \\(" + str(int(datetime.strftime(datetime.strptime(str(tdelta), "%H:%M:%S"), "%H"))) + " hours\\)" + "\n")
                    else:
                        schedule_today_temp += (start_time +" to " + stop_time + "\n")

        schedule_today = schedule_today_temp
        schedule_today = format_schedule_with_passed_times(schedule_today)
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
            schedule_tomorrow_temp = 'NO LOADSHEDDING'
        else:
            #pretty print with new lines
            for time in schedule_tomorrow.split(","): #tokenise on , then - 
                start_time, stop_time = time.split("-")
                #strip out leading and tailing empty spaces
                start_time = start_time.strip()
                stop_time = stop_time.strip()

                #convert from 24 hour format to 12 hour format
                start_time = datetime.strftime(datetime.strptime(start_time, "%H:%M"), TimeFormat)
                stop_time = datetime.strftime(datetime.strptime(str(stop_time), "%H:%M"), TimeFormat)
                
                #calculate duration of each slot
                tdelta = datetime.strptime(stop_time, TimeFormat) - datetime.strptime(start_time, TimeFormat)
                print (tdelta)
                #if the stop time is in the next day
                #tday, ttime = str(tdelta).split(",")
                #print (ttime)
                if (tdelta > timedelta(hours=4)): #if the duration of any the loadshedding times is greater than 4 hours, then include duration in the message
                    schedule_tomorrow_temp += (start_time +" to " + stop_time + " \\(" + str(int(datetime.strftime(datetime.strptime(str(tdelta), "%H:%M:%S"), "%H"))) + " hours\\)" + "\n")
                else:
                    schedule_tomorrow_temp += (start_time +" to " + stop_time + "\n")

        schedule_tomorrow = schedule_tomorrow_temp
    

    if int(load_stage) > 0:
        #print(schedule[today.strftime("%a, %d %b")]['S'])
        load_message = (area + " **Loadshedding** Notice \n"
        "Stage _" + str(load_stage) + "_  \n"
        "The loadshedding schedule for __today__ \\- " + today.strftime("%a, %d %b") + ": \n" 
        "" + schedule_today + "  \n" +
        "The loadshedding schedule for __tomorrow__ \\- " + tomorrow.strftime("%a, %d %b") + ": \n" 
        "" + schedule_tomorrow)

        print(load_message)

        telegram_response = requests.post(
                url='https://api.telegram.org/bot' + TelegramBotToken + '/sendMessage',
                data={'chat_id': TelegramChatID, 'parse_mode': 'MarkdownV2','text': load_message}).json()
        print(telegram_response)
    else:
        print("Stage 0 - no need to send a schedule")

def format_schedule_with_passed_times(schedule):
    # Get current time and add 2 hours for GMT+2
    current_time = datetime.now() + timedelta(hours=2)
    formatted_slots = []
    
    # Split the schedule into individual time slots
    slots = schedule.split('\n')
    
    for slot in slots:
        if not slot.strip():  # Skip empty lines
            continue
            
        # Split the time range and extract end time
        end_time_str = slot.split('to')[1].strip()
        try:
            # Parse the 12-hour format time
            end_time = datetime.strptime(end_time_str, '%I:%M %p').replace(
                year=current_time.year,
                month=current_time.month,
                day=current_time.day
            )
            
            # If the end time has passed, apply strikethrough
            if current_time > end_time:
                formatted_slots.append(f"~{slot}~")
            else:
                formatted_slots.append(slot)
        except ValueError as e:
            # In case of parsing errors, add the slot without modification
            formatted_slots.append(slot)
            print(f"Error parsing time: {e}")
    
    # Join the formatted slots back together
    return '\n'.join(formatted_slots)


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

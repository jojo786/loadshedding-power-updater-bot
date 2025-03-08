import json
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import boto3
from aws_lambda_powertools.utilities import parameters

StackName = os.environ['StackName']
TelegramScheduleCommandStateMachine = os.environ['TelegramScheduleCommandStateMachine']

# Initialize SSM client
ssm = boto3.client('ssm')
# Get the Telegram bot token from Parameter Store
ssm_provider = parameters.SSMProvider()
TelegramBotToken = ssm_provider.get('/'+StackName+'/telegram/prod/bot_token', decrypt=True)
TelegramChatID = ssm_provider.get('/'+StackName+'/telegram/prod/chat_id', decrypt=True)


application = ApplicationBuilder().token(TelegramBotToken).build()

stepfunctions = boto3.client('stepfunctions')

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Start health command")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm here")

async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Start Schedule command - Step Functions")
    try:
        response = stepfunctions.start_execution(
                stateMachineArn=TelegramScheduleCommandStateMachine, input='{ }')
    except Exception as err:
            print("Exception: TelegramScheduleCommandStateMachine")
            print (err) 
    else:
        return response['executionArn']

def lambda_handler(event, context):
    return asyncio.get_event_loop().run_until_complete(main(event, context))

async def main(event, context):
   
    application.add_handler(CommandHandler('health', health))
    application.add_handler(CommandHandler('schedule', schedule))

    try:    
        await application.initialize()
        await application.process_update(
            Update.de_json(json.loads(event["body"]), application.bot)
        )
    
        return {
            'statusCode': 200,
            'body': 'Success'
        }

    except Exception as exc:
        return {
            'statusCode': 500,
            'body': 'Failure'
        }


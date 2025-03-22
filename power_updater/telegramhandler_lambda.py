import json
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import os
import boto3
from aws_lambda_powertools.utilities import parameters
import pytz
from datetime import datetime


StackName = os.environ['StackName']
TelegramScheduleCommandStateMachine = os.environ['TelegramScheduleCommandStateMachine']
agent_id = os.environ['AgentId']
agent_alias_id = os.environ['AgentAliasId']
subscribers_table = os.environ['SubscribersTableName']

# Initialize boto3 clients
stepfunctions = boto3.client('stepfunctions')
ssm = boto3.client('ssm')
bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
dynamodb = boto3.client('dynamodb')

# Get the Telegram bot token from Parameter Store
ssm_provider = parameters.SSMProvider()
TelegramBotToken = ssm_provider.get('/'+StackName+'/telegram/prod/bot_token', decrypt=True)
TelegramBotAPISecretToken = ssm_provider.get('/'+StackName+'/telegram/prod/api_secret_token', decrypt=True)

application = ApplicationBuilder().token(TelegramBotToken).build()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Hello, I am PowerUpdater - an Eskom Loadshedding GenAI Agent chatbot, powered by Amazon Bedrock, running on AWS Serverless. Check the menu for the commands I support, or ask me anything!")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="PowerUpdater is running!")
    
async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Start subscribe command")
    
    try:
        # Get chat ID and current timestamp
        chat_id = str(update.effective_chat.id)
        timestamp = datetime.now().isoformat()
        
        # Save subscription to DynamoDB
        response = dynamodb.put_item(
            TableName=subscribers_table,
            Item={
                'chat_id': {'S': chat_id},
                'area': {'S': 'Buccleuch'}, #hardcoded for now until multiple areas supported
                'type': {'S': 'user'},
                'date_subscribed': {'S': timestamp},
                'active': {'BOOL': True}
            }
        )
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="You have successfully subscribed to receive loadshedding notifications"
        )
        
    except Exception as e:
        print(f"Error saving subscription: {str(e)}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, there was an error processing your subscription. Please try again later."
        )    

async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    print("Start lambda_handler")

    # Check if secret token header exists and matches expected value
    if 'headers' not in event or \
       'X-Telegram-Bot-Api-Secret-Token' not in event['headers'] or \
       event['headers']['X-Telegram-Bot-Api-Secret-Token'] != TelegramBotAPISecretToken:
        print("Unauthorized - Telegram Secret not found")
        return {
            'statusCode': 401,
            'body': 'Unauthorized'
        }
    
    return asyncio.get_event_loop().run_until_complete(main(event, context))

    
async def bedrock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Start bedrock")
     # Get current date and time in South Africa timezone
    sa_timezone = pytz.timezone('Africa/Johannesburg')
    current_time = datetime.now(sa_timezone)
    formatted_datetime = current_time.strftime("%Y-%m-%d %H:%M:%S %Z")
        
    try:
        # Get the user's message text from the update object
        chat_id = update.effective_chat.id
        user_message = update.message.text
        
        # Call the Bedrock agent
        response = bedrock_agent.invoke_agent(
            agentId=agent_id, 
            agentAliasId=agent_alias_id, 
            sessionId=str(chat_id),  # use Telegram chat_id as the session ID - Bedrock agent will manage chat history per chat_id
            inputText=user_message,
            sessionState={
                "promptSessionAttributes": {
                    "currentDateTime": formatted_datetime,
                    "timeZone": "Africa/Johannesburg"
                }
            }
        )
        print(response)

        # Process the event stream
        complete_response = []
        for event in response['completion']:
            try:
                # Print raw bytes for debugging
                raw_bytes = event['chunk']['bytes']
                #print("Raw bytes:", raw_bytes)
                
                # Decode bytes to string
                decoded_str = raw_bytes.decode('utf-8')
                print("Decoded string:", decoded_str)
                
                if decoded_str.strip():
                    complete_response.append(decoded_str)

            except Exception as e:
                print(f"Error processing chunk: {str(e)}")
        
         # Join all responses and send back to Telegram
        final_response = ''.join(complete_response)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=final_response
        )
        
    except Exception as e:
        error_message = f"Error: {str(e)}"
        print(error_message)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Sorry, I encountered an error: {error_message}"
        )

async def main(event, context):
   
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('status', status_command))
    application.add_handler(CommandHandler('schedule', schedule_command))
    application.add_handler(CommandHandler('subscribe', subscribe_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), bedrock))

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


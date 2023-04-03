# Loadshedding Power Updater Telegram Bot
Telegram Bot that gives you Loadshedding information, running on AWS Serverless

Loosely-based off https://github.com/daffster/mypowerstats, but complelty re-written to run as a Telegram bot, running on AWS Lambda and DynamoDB, deployed using AWS SAM.

Pulls loadshedding stage and schedule info from https://loadshedding.eskom.co.za/LoadShedding/, and makes it available as a Telegram bot. This bot can be added to your community groups/channels, and will post the schedule for your area.

The bot will post the following information five times a day (or depending on the EventBridge Schedule):
```
Buccleuch Loadshedding Notice 
Stage 3  
The loadshedding schedule for today - Mon, 03 Apr: 
  14:00  -  16:30
  
The loadshedding schedule for tomorrow - Tue, 04 Apr: 
 06:00  -  08:30
 14:00  -  16:30
 22:00  -  00:30

```

## Architecture 
![architecture](docs/Architecture.png)

1. `get_schedule_lambda.py` Lambda function gets invoked via cron schedule (EventBridge rule) to hit the [Eskom loadshedding status endpoint](https://loadshedding.eskom.co.za/LoadShedding/GetStatus) and get the loadshedding stage. This is stored on Dynamo, for each area/location/suburb.
2. A filter is setup on DynamoDB Streams to send changes to the `notification_lambda.py` Lambda service. If the loadshedding stage has changed, the new stage will be sent, which will be posted to Telegram
3. Once a day, `get_schedule_lambda.py` Lambda function gets invoked via cron schedule (EventBridge rule) to hit the [Eskom loadshedding schedule endpoint](https://loadshedding.eskom.co.za/LoadShedding/GetScheduleM) and store the schedule in DynamoDB. 
4. A filter is setup on DynamoDB Streams to send changes to the `notification_lambda.py` Lambda service. If the loadshedding schedule has changed, it will be posted to Telegram
5. Every 2 hours, `notification_lambda.py` Lambda function gets invoked via cron schedule (EventBridge rule) to send loadshedding reminders. It reads the latest stage and schedule from DynamoDB, and posts to Telegram

## How to run it
Once you have forked this repo, GitHub Actions CI/CD pipeline will run on a `git push`. But if you want to build and deploy to AWS using AWS SAM locally, then:

- Install [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html), and  [configure it](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html#cli-configure-quickstart-config)
- Install [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
- Create an SSM Parameter to store the Telegram token. `aws ssm put-parameter --region eu-west-1 --name "/telegramtasweerbot/telegram/dev/bot_token" --type "SecureString" --value "12334342:ABCD12432423" --overwrite`
- Run `sam build && sam deploy --parameter-overrides --parameter-overrides StageEnv=dev` to run it for dev. Similiar for prod.


## TODO
- If stage changes, re-pull the schedule
- Publish the schedule for more days
- Even though area is a field in the DB, need to configure it properly for multiple areas
- Add ability to ask the bot questions: latest schedule, stage
- Pull announcements from https://twitter.com/Eskom_SA
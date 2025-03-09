# Loadshedding Power Updater Telegram Bot
Power Updater is an app that provides Eskom Loadshedding updates - running on AWS Serverless. Users can interact with Power Updater in two ways:
1. A Telegram bot: [@PowerUpdatedBot](https://t.me/PowerUpdatedBot)
2. A web front-end: [https://powerupdater.hacksaw.co.za/](https://powerupdater.hacksaw.co.za/)


The app pulls the Eskom loadshedding stage and schedule info from https://loadshedding.eskom.co.za/LoadShedding/, and makes it available as a Telegram bot and Flask web app. You can interact with the bot directly and request the loadshedding using the `/schedule` command, and/or the bot can be added to your Telegram community groups/channels, and it will post the schedule for your area.

The bot will post the following information five times a day (or depending on the EventBridge Schedule):
```
Buccleuch Loadshedding Notice 
Stage 6  
The loadshedding schedule for today - Sun, 16 Apr: 
 16:00  -  20:30 (4 hours)
  
The loadshedding schedule for tomorrow - Mon, 17 Apr: 
 06:00  -  08:30
 14:00  -  18:30 (4 hours)
 22:00  -  02:30

```

The bot also supports you asking it for the schedule on an ad-hoc basis using the `/schedule` command.

The bot has a web front-end: https://powerupdater.hacksaw.co.za/ - where you can see the list of areas and schedules.

Loosely-based off https://github.com/daffster/mypowerstats, but completly re-written.

## Architecture 

For a detailed view of the architecture, [read my blog about how this uses choreography and orchestration](https://hacksaw.co.za/blog/choreography-and-orchestration-using-aws-serverless/)

![architecture](docs/Architecture.png)

1. `get_schedule_lambda.py` Lambda function gets invoked via an EventBridge schedule to call the [Eskom loadshedding status endpoint](https://loadshedding.eskom.co.za/LoadShedding/GetStatus) and get the loadshedding stage. This is stored on DynamoDB, for each area/location/suburb.
2. A filter is setup on DynamoDB Streams to send changes to the `notification_lambda.py` Lambda function. If the loadshedding stage has changed, the new stage will be sent, which will be posted to Telegram.
3. Once a day, `get_schedule_lambda.py` Lambda function gets invoked via an EventBridge schedule to call the [Eskom loadshedding schedule endpoint](https://loadshedding.eskom.co.za/LoadShedding/GetScheduleM) and store the schedule in DynamoDB. 
4. A filter is setup on DynamoDB Streams to send changes to the `notification_lambda.py` Lambda function. If the loadshedding schedule has changed, it will be posted to Telegram
5. Every 2 hours, `notification_lambda.py` Lambda function gets invoked via cron schedule (EventBridge rule) to send loadshedding reminders. It reads the latest stage and schedule from DynamoDB, and posts to Telegram

## How to run it
- Create your bot using [BotFather](https://core.telegram.org/bots/tutorial), and take note of the token, e.g. 12334342:ABCD124324234
- Store the token securely in AWS SSM: `aws ssm put-parameter --name "/power-updater/telegram/prod/bot_token" --type "SecureString" --value "12334342:ABCD124324234" --overwrite`
- Use [AWS SAM](https://aws.amazon.com/serverless/sam/) to build and deploy to AWS:

- - Install [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html), and  [configure it](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html#cli-configure-quickstart-config)
- - Install [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
- To build and deploy your application for the first time, run the following in your shell:

```bash
sam build
sam deploy --guided
```

For future deploys, you can just run:

```bash
sam build && sam deploy
```

- Update your Telegram bot to change from polling to Webhook, by pasting this URL in your browser, or curl'ing it - Use your own bot token and Lambda URL endpoint: https://api.telegram.org/bot12334342:ABCD124324234/setWebHook?url=https://1fgfgfd56.lambda-url.eu-west-1.on.aws/. You can check that it was set correctly by going to https://api.telegram.org/bot12334342:ABCD124324234/getWebhookInfo, which should include the url of your Lambda URL, as well as any errors Telegram is encounterting calling your bot on that API.
- To ensure that only Telegram (servers) are calling your webhook, use the following to protect your webhook:
- - Set [the `secret_token` on the webhook](https://core.telegram.org/bots/api#setwebhook) to ensure that header “X-Telegram-Bot-Api-Secret-Token” is sent: `https://api.telegram.org/bot12334342:ABCD124324234/setWebHook?url=https://1fgfgfd56.lambda-url.eu-west-1.on.aws/Prod&secret_token=thisismysecret`


## TODO

- Even though area is a field in the DB, need to configure it properly for multiple areas
- Pull announcements from https://twitter.com/Eskom_SA
- Use WAF to limit API GW clients to [Telegram IP](https://core.telegram.org/bots/webhooks#the-short-version)
- Use API GW HTTP Header Request Validator to ensure that the header “X-Telegram-Bot-Api-Secret-Token” exists

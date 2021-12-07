# Loadshedding Power Updater Telegram Bot
Telegram Bot that gives you Loadshedding information, running on AWS Serverless

Loosely-based off https://github.com/daffster/mypowerstats, but complelty re-written to run as a Telegram bot, running on AWS Lambda and DynamoDB, deployed using AWS SAM.

Pulls loadshedding stage and schedule info from https://loadshedding.eskom.co.za/LoadShedding/, and makes it available as a Telegram bot. This bot can be added to your area groups, and will post the schedule for your area.

## Architecture 

## TODO
- If stage changes, re-pull the schedule
- Publish the schedule for more days
- Even though area is a field in the DB, need to configure it properly for multiple areas
- Add ability to ask the bot questions: latest schedule, stage
- Pull announcements from https://twitter.com/Eskom_SA
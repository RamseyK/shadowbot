Shadow - A GroupMe bot
=======

A GroupMe bot that is meant to be triggered by a Cron job to perform timed actions.
I wrote this to be an asshole.

Features:
- Schedule messages to be sent in the future
- Replies to all DM's with "Meow"

How to use:
1. Create a GroupMe account and have it added to your desired group. Create an API key for this user
2. Rename default_config.json to config.json
3. Enter your GroupMe API key and any timed messages you want to schedule in the future in the config
4. Write a Cronjob to trigger this script every so often
eg. env EDITOR=nano crontab -e
* * * * * python shadow.py

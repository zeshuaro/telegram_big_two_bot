# Telegram Big Two Bot

Play Big Two with your friend on Telegram

Connect to [Bot](https://t.me/biggytwobot)

Stay tuned for updates and new releases on the [Telegram Channel](https://t.me/biggytwobotdev)

Find the bot at [Store Bot](https://storebot.me/bot/biggytwobot)

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and 
testing purposes

### Prerequisites

Run the following command to install the required libraries:


```
pip install -r requirements.txt
```

Below is a list of the main libraries that are included:

* [Python Telegram Bot](https://github.com/python-telegram-bot/python-telegram-bot)
* [Psycopg 2](https://github.com/psycopg/psycopg2)

You will also need postgres to be set up and running.

Make a `.env` file and put your telegram token and postgres database settings in there. 

If you want to use the webhook method to run the bot, also include `APP_URL` and `PORT` in the `.env` file. If you 
want to use polling instead, do not include `APP_URL` in your `.env` file.

Below is an example:

```
TELEGRAM_TOKEN=<telegram_token>
DB_NAME=<database_name
DB_USER=<database_username>
DB_PW=<database_password>
DB_HOST=<database_host>
DB_PORT=<database_port>
```
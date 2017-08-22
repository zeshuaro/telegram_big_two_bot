#!/usr/bin/env python3
# coding: utf-8

import gettext
import logging
import os
import random
import re
import smtplib
import urllib.parse
from collections import defaultdict

import dotenv
import langdetect
import psycopg2
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError, Unauthorized
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler, Filters, MessageHandler
from telegram.ext.dispatcher import run_async

from bigtwogame.bigtwogame import Card, Deck, get_cards_type, are_cards_bigger

# Enable logging
logging.basicConfig(format="[%(asctime)s] [%(levelname)s] %(message)s", datefmt='%Y-%m-%d %I:%M:%S %p',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
dotenv.load(dotenv_path)
app_url = os.environ.get("APP_URL")
port = int(os.environ.get('PORT', '5000'))

telegram_token = os.environ.get("TELEGRAM_TOKEN_BETA") if os.environ.get("TELEGRAM_TOKEN_BETA") \
    else os.environ.get("TELEGRAM_TOKEN")
is_testing = os.environ.get("IS_TESTING")
dev_tele_id = int(os.environ.get("DEV_TELE_ID"))
dev_email = os.environ.get("DEV_EMAIL") if os.environ.get("DEV_EMAIL") else "sample@email.com"
dev_email_pw = os.environ.get("DEV_EMAIL_PW")
is_email_feedback = os.environ.get("IS_EMAIL_FEEDBACK")
smtp_host = os.environ.get("SMTP_HOST")

if os.environ.get("DATABASE_URL"):
    urllib.parse.uses_netloc.append("postgres")
    url = urllib.parse.urlparse(os.environ["DATABASE_URL"])

    db_name = url.path[1:]
    db_user = url.username
    db_pw = url.password
    db_host = url.hostname
    db_port = url.port
else:
    db_name = os.environ.get("DB_NAME")
    db_user = os.environ.get("DB_USER")
    db_pw = os.environ.get("DB_PW")
    db_host = os.environ.get("DB_HOST")
    db_port = os.environ.get("DB_PORT")

# Queued jobs
queued_jobs = defaultdict(dict)


# Connects to database
def connect_db():
    return psycopg2.connect(database=db_name, user=db_user, password=db_pw, host=db_host, port=db_port)


# Creates database tables
def create_db_tables():
    db = connect_db()
    cur = db.cursor()

    cur.execute("select * from information_schema.tables where table_name = 'user_language'")
    if not cur.fetchone():
        # cur.execute("drop table user_language")
        cur.execute("create table user_language (tele_id int, language text)")

    cur.execute("select * from information_schema.tables where table_name = 'game_timer'")
    if not cur.fetchone():
        # cur.execute("drop table user_language")
        cur.execute("create table game_timer (group_tele_id int, join_timer int, pass_timer int)")

    cur.execute("select * from information_schema.tables where table_name = 'player_group'")
    if cur.fetchone():
        cur.execute("drop table player_group")
    cur.execute("create table player_group (player_tele_id int, group_tele_id int)")

    cur.execute("select * from information_schema.tables where table_name = 'game'")
    if cur.fetchone():
        cur.execute("drop table game")
    cur.execute("create table game (group_tele_id int, game_round int, curr_player int, player_in_control int, "
                "count_pass int)")

    cur.execute("select * from information_schema.tables where table_name = 'player'")
    if cur.fetchone():
        cur.execute("drop table player")
    cur.execute("create table player (group_tele_id int, player_id int, player_tele_id int, player_name text, "
                "num_cards int)")

    cur.execute("select * from information_schema.tables where table_name = 'player_deck'")
    if cur.fetchone():
        cur.execute("drop table player_deck")
    cur.execute("create table player_deck (group_tele_id int, player_id int, suit int, num int)")

    cur.execute("select * from information_schema.tables where table_name = 'curr_card'")
    if cur.fetchone():
        cur.execute("drop table curr_card")
    cur.execute("create table curr_card (group_tele_id int, suit int, num int)")

    cur.execute("select * from information_schema.tables where table_name = 'prev_card'")
    if cur.fetchone():
        cur.execute("drop table prev_card")
    cur.execute("create table prev_card (group_tele_id int, suit int, num int)")

    db.commit()
    db.close()


# Deletes game data with the given group telegram ID
def delete_game_data(group_tele_id):
    for key in queued_jobs[group_tele_id].keys():
        queued_jobs[group_tele_id][key].schedule_removal()

    db = connect_db()
    cur = db.cursor()

    cur.execute("delete from player_group where group_tele_id = %s", (group_tele_id,))
    cur.execute("delete from game where group_tele_id = %s", (group_tele_id,))
    cur.execute("delete from player where group_tele_id = %s", (group_tele_id,))
    cur.execute("delete from player_deck where group_tele_id = %s", (group_tele_id,))
    cur.execute("delete from curr_card where group_tele_id = %s", (group_tele_id,))
    cur.execute("delete from prev_card where group_tele_id = %s", (group_tele_id,))

    db.commit()
    db.close()


# Sends start message
@run_async
def start(bot, update):
    tele_id = update.message.chat.id
    install_lang(tele_id)

    if update.message.chat.type != "group":
        message = _("Welcome to Big Two Moderator. Add me into a group and type /startgame to start a game.\n\nYou "
                    "can also type /setlang to change the bot's language.\n\nPlease note that you can only use "
                    "/setlang for changing the bot's language in a group if you are a group admin.")

        bot.sendMessage(tele_id, message)


# Sends help message
@run_async
def help(bot, update):
    player_tele_id = update.message.from_user.id
    install_lang(player_tele_id)
    keyboard = [[InlineKeyboardButton("Rate me", "https://t.me/storebot?start=biggytwobot")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = _("Add me into a group and type /startgame to start a game. Other players can then type /join to join "
                "the game.\n\nYou will not be able to start or join a game if a game has already been set up and "
                "running.\n\nYou can only force to stop a game if you are a group admin.\n\nUse /command to get a "
                "list of commands to see what I can do.")

    bot.sendMessage(player_tele_id, message, reply_markup=reply_markup)


# Sends command message
@run_async
def command(bot, update):
    player_tele_id = update.message.from_user.id
    install_lang(player_tele_id)

    message = _("/setlang - Set your or the group's bot language\n"
                "/setjointimer <timer> - Set the timer for joining the game (e.g. /setjointimer 30)\n"
                "/setpasstimer <timer> - Set the timer for automatic pass (e.g. /setpasstimer 30)\n"
                "/startgame - Start a new game\n"
                "/join - Join a game\n"
                "/forcestop - Force to stop a game\n"
                "/showdeck - Show your deck of cards\n"
                "/help - How to use the bot\n"
                "/donate - Support my developer!")

    bot.sendMessage(player_tele_id, message)


# Sends donate message
@run_async
def donate(bot, update):
    player_tele_id = update.message.from_user.id
    install_lang(player_tele_id)
    message = _("Want to help keep me online? Please donate to %s through PayPal.\n\nDonations "
                "help me to stay on my server and keep running." % dev_email)
    bot.send_message(player_tele_id, message)


# Sends set language message
@run_async
def set_lang(bot, update):
    if update.message.chat.type == "private":
        tele_id = update.message.from_user.id
        install_lang(tele_id)
        message = _("Pick your default language from below\n\n")
    elif update.message.chat.type == "group":
        tele_id = update.message.chat.id
        install_lang(tele_id)
        message = _("Pick the group's default language from below\n\n")
        is_admin = False
        admins = bot.get_chat_administrators(tele_id)

        for admin in admins:
            if admin.user.id == update.message.from_user.id:
                is_admin = True
                break

        if not is_admin:
            return
    else:
        return

    keyboard = [[InlineKeyboardButton("English", callback_data="set_lang,en"),
                 InlineKeyboardButton("廣東話", callback_data="set_lang,zh-hk")],
                [InlineKeyboardButton("正體中文", callback_data="set_lang,zh-tw"),
                 InlineKeyboardButton("简体中文", callback_data="set_lang,zh-cn")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    bot.sendMessage(tele_id, message, reply_markup=reply_markup)


# Sets join timer
@run_async
def set_join_timer(bot, update):
    set_game_timer(bot, update, "join_timer")


# Sets pass timer
@run_async
def set_pass_timer(bot, update):
    set_game_timer(bot, update, "pass_timer")


# Sets game timer
def set_game_timer(bot, update, timer_type):
    group_tele_id = update.message.chat.id
    player_tele_id = update.message.from_user.id
    timer = re.sub("/.*?\s+", "", update.message.text)
    install_lang(player_tele_id)

    if update.message.chat.type != "group":
        message = _("You can only use this command in a group")
        bot.sendMessage(player_tele_id, message)
        return

    is_admin = False
    admins = bot.getChatAdministrators(group_tele_id)

    for admin in admins:
        if admin.user.id == player_tele_id:
            is_admin = True
            break

    if not is_admin:
        message = _("You are not a group admin")
        bot.sendMessage(player_tele_id, message)
        return

    db = connect_db()
    cur = db.cursor()

    cur.execute("select * from game where group_tele_id = %s", (group_tele_id,))
    if cur.fetchone():
        message = _("You can only change the timer when a game is not running")
        bot.sendMessage(player_tele_id, message)
        db.close()
        return

    install_lang(group_tele_id)

    if not re.match("\d+", timer) or (timer_type == "join_timer" and int(timer) not in range(10, 61)) or \
            (timer_type == "pass_timer" and int(timer) not in range(20, 121)):
        if timer_type == "join_timer":
            message = _("Join timer can only be set between 10s to 60s")
        else:
            message = _("Pass timer can only be set between 20s to 120s")
        bot.sendMessage(group_tele_id, message)
        db.close()
        return

    timer = int(timer)
    cur.execute("select * from game_timer where group_tele_id = %s", (group_tele_id,))
    if cur.fetchone():
        query = "update game_timer set %s = %s where group_tele_id = %s" % (timer_type, timer, group_tele_id)
        cur.execute(query)
    else:
        query = "insert into game_timer (group_tele_id, %s) values (%s, %s)" % (timer_type, group_tele_id, timer)
        cur.execute(query)

    db.commit()
    db.close()

    if timer_type == "join_timer":
        bot.send_message(group_tele_id, _("Join timer has been set to %ds") % timer)
    else:
        bot.send_message(group_tele_id, _("Pass timer has been set to %ds") % timer)


# Starts a new game
def start_game(bot, update, job_queue):
    group_tele_id = update.message.chat.id
    player_name = update.message.from_user.first_name
    install_lang(update.message.from_user.id)

    if update.message.chat.type != "group":
        message = _("You can only use this command in a group")
        bot.sendMessage(group_tele_id, message)
        return

    if not can_msg_player(bot, update):
        return

    db = connect_db()
    cur = db.cursor()

    cur.execute("select * from game where group_tele_id = %s", (group_tele_id,))
    if cur.fetchone():
        message = _("A game has already been started")
        bot.sendMessage(update.message.from_user.id, message)
        db.close()
        return

    cur.execute("insert into game (group_tele_id, game_round, curr_player, player_in_control, count_pass)"
                "values (%s, %s, %s, %s, %s)", (group_tele_id, -1, -1, -1, -1))
    db.commit()
    db.close()

    install_lang(group_tele_id)
    message = (_("[%s] has started Big Two. Type /join to join the game\n\n") % player_name)

    bot.sendMessage(chat_id=group_tele_id,
                    text=message,
                    disable_notification=True)

    join(bot, update, job_queue)


# Checks if bot is authorised to send user messages
def can_msg_player(bot, update):
    is_success = True
    player_tele_id = update.message.from_user.id

    try:
        bot_message = bot.send_message(player_tele_id, "Testing... You can ignore or delete this message if it doesn't"
                                                       "get deleted automatically.")
    except TelegramError or Unauthorized:
        is_success = False
        player_name = update.message.from_user.first_name
        group_tele_id = update.message.chat.id
        install_lang(group_tele_id)

        message = (_("[%s] Please PM [@biggytwobot] and say [/start]. Otherwise, you won't be able to join and "
                     "play Big Two") % player_name)

        keyboard = [[InlineKeyboardButton(text=_("Say start to me"),
                                          url="https://telegram.me/biggytwobot")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        bot.send_message(chat_id=group_tele_id,
                         text=message,
                         reply_markup=reply_markup)
    else:
        bot.delete_message(chat_id=player_tele_id,
                           message_id=bot_message.message_id)

    return is_success


# Joins a new game
def join(bot, update, job_queue):
    player_name = update.message.from_user.first_name
    player_tele_id = update.message.from_user.id
    group_name = update.message.chat.title
    group_tele_id = update.message.chat.id
    id_list = [player_tele_id]

    install_lang(player_tele_id)

    if update.message.chat.type != "group":
        message = _("You can only use this command in a group")
        bot.sendMessage(player_tele_id, message)
        return

    if not can_msg_player(bot, update):
        return

    db = connect_db()
    cur = db.cursor()

    # Checks if there exists a game
    cur.execute("select * from game where group_tele_id = %s", (group_tele_id,))
    if not cur.fetchone():
        message = _("A game has not been started yet. Type /startgame in a group to start a game.")
        bot.sendMessage(player_tele_id, message)
        return

    # Checks if player is in game
    if not is_testing:
        cur.execute("select * from player_group where player_tele_id = %s", (player_tele_id,))
        if cur.fetchone():
            message = _("You have already joined a game")
            bot.sendMessage(player_tele_id, message)
            db.close()
            return

    cur.execute("select player_tele_id from player_group where group_tele_id = %s", (group_tele_id,))
    for row in cur.fetchall():
        id_list.append(row[0])
    num_players = len(id_list)

    # Checks for valid number of players
    if num_players <= 4:
        cur.execute("insert into player_group (player_tele_id, group_tele_id)"
                    "values (%s, %s)", (player_tele_id, group_tele_id))
        cur.execute("insert into player (group_tele_id, player_id, player_tele_id, player_name, num_cards)"
                    "values (%s, %s, %s, %s, %s)", (group_tele_id, (num_players - 1), player_tele_id, player_name, 13))
        db.commit()

        install_lang(group_tele_id)
        message = (_("[%s] has joined.\nThere are now %d/4 Players\n") % (player_name, num_players))

        if "join" in queued_jobs[group_tele_id]:
            queued_jobs[group_tele_id]["join"].schedule_removal()

        cur.execute("select join_timer from game_timer where group_tele_id = %s", (group_tele_id,))
        row = cur.fetchone()
        db.close()

        join_timer = row[0] if row and row[0] else 60
        job = job_queue.run_once(stop_empty_game, join_timer, context=group_tele_id)
        queued_jobs[group_tele_id]["join"] = job

        if num_players != 4:
            message += _("%ss left to join") % join_timer
        bot.sendMessage(chat_id=group_tele_id,
                        text=message,
                        disable_notification=True)

        install_lang(player_tele_id)
        message = (_("You have joined the game in the group [%s]") % group_name)
        bot.send_message(player_tele_id, message)

        if num_players == 4:
            queued_jobs[group_tele_id]["join"].schedule_removal()
            install_lang(group_tele_id)
            message = _("Enough players, game start. I will PM your deck of cards when it is your turn. ")

            db = connect_db()
            cur = db.cursor()
            cur.execute("select pass_timer from game_timer where group_tele_id = %s", (group_tele_id,))
            row = cur.fetchone()
            db.close()
            if row is None:
                message += _("Each player has 45s to pick your cards")
            else:
                pass_timer = row[0]
                message += _("Each player has %ss to pick your cards") % pass_timer

            bot.sendMessage(chat_id=group_tele_id,
                            text=message,
                            disable_notification=True)

            setup_game(group_tele_id, id_list)
            game_message(bot, group_tele_id)
            player_message(bot, group_tele_id, False, 0, False, job_queue)  # Not edit and not sort suit

    db.close()


# Stops a game without enough players
def stop_empty_game(bot, job):
    group_tele_id = job.context
    install_lang(group_tele_id)
    message = _("Game has been stopped by me since there is no enough players.")
    bot.send_message(group_tele_id, message)

    delete_game_data(group_tele_id)


# Sets up a game
def setup_game(group_tele_id, tele_ids):
    db = connect_db()
    cur = db.cursor()

    if not is_testing:
        random.shuffle(tele_ids)

    # Creates a deck of cards in random order
    deck = Deck()

    # Sets up players
    curr_player = -1

    for i, tele_id in enumerate(tele_ids):
        player_deck = []

        for j in range(0, 13):
            card = deck.cards.pop()
            player_deck.append(card)

            # Player with ♦3 starts first
            if card.suit == 0 and card.num == 3:
                curr_player = i

        player_deck.sort()
        if not is_testing:
            cur.execute("update player set player_id = %s where group_tele_id = %s and player_tele_id = %s",
                        (i, group_tele_id, tele_id))

        for card in player_deck:
            cur.execute("insert into player_deck (group_tele_id, player_id, suit, num)"
                        "values (%s, %s, %s, %s)", (group_tele_id, i, card.suit, card.num))

    cur.execute("update game set game_round = %s, curr_player = %s, player_in_control = %s, count_pass = %s "
                "where group_tele_id = %s", (1, curr_player, curr_player, 0, group_tele_id))
    db.commit()
    db.close()


# Sends message to game group
def game_message(bot, group_tele_id):
    install_lang(group_tele_id)
    message = ""
    db = connect_db()
    cur = db.cursor()

    cur.execute("select game_round, curr_player, player_in_control from game where group_tele_id = %s",
                (group_tele_id,))
    game_round, curr_player, player_in_control = cur.fetchone()

    cur.execute("select player_name from player where group_tele_id = %s and player_id = %s",
                (group_tele_id, curr_player))
    curr_player_name = cur.fetchone()[0]

    if game_round > 1 and curr_player != (player_in_control + 1) % 4:
        prev_player_id = (curr_player - 1) % 4
        cur.execute("select player_name from player where group_tele_id = %s and player_id = %s",
                    (group_tele_id, prev_player_id))
        prev_player_name = cur.fetchone()[0]

        message += "--------------------------------------\n"
        message += _("%s decided to PASS\n") % prev_player_name

    db.close()

    message += "--------------------------------------\n"
    message += _("%s's Turn\n") % curr_player_name
    message += "--------------------------------------\n"

    message += get_game_message(group_tele_id, game_round, curr_player, player_in_control)

    bot.sendMessage(group_tele_id, message, disable_notification=True)


# Sends message to player
def player_message(bot, group_tele_id, is_edit, message_id, is_sort_suit, job_queue):
    message = ""
    db = connect_db()
    cur = db.cursor()

    cur.execute("select game_round, curr_player, player_in_control from game where group_tele_id = %s",
                (group_tele_id,))
    game_round, curr_player, player_in_control = cur.fetchone()
    cur.execute("select player_tele_id from player where group_tele_id = %s and player_id = %s",
                (group_tele_id, curr_player))
    player_tele_id = cur.fetchone()[0]
    db.close()

    install_lang(player_tele_id)
    message += get_game_message(group_tele_id, game_round, curr_player, player_in_control)

    # Checks if to display selected cards
    db = connect_db()
    cur = db.cursor()
    cur.execute("select suit, num from curr_card where group_tele_id = %s", (group_tele_id,))
    rows = cur.fetchall()
    if rows:
        cards = []
        message += _("Selected cards:\n")

        for row in rows:
            cards.append(Card(row[0], row[1]))

        cards.sort()
        for card in cards:
            message += str(card.show_suit)
            message += " "
            message += str(card.show_num)
            message += "\n"

        message += "--------------------------------------\n"

    message += _("Pick the cards that you will like to use from below, one at a time. Press done when you are finished")

    cards = []
    card_list = []

    cur.execute("select suit, num from player_deck where group_tele_id = %s and player_id = %s",
                (group_tele_id, curr_player))
    for row in cur.fetchall():
        cards.append(Card(row[0], row[1]))

    if is_sort_suit:
        cards.sort(key=lambda x: x.suit)
    else:
        cards.sort()

    for card in cards:
        show_card = str(card.show_suit)
        show_card += " "
        show_card += str(card.show_num)

        call_back_data = "%d,%d" % (card.suit, card.num)
        card_list.append(InlineKeyboardButton(text=show_card,
                                              callback_data=call_back_data))

    keyboard = [card_list[i:i + 4] for i in range(0, len(card_list), 4)]
    keyboard.append([InlineKeyboardButton(text=_("Unselect"),
                                          callback_data="unselect"),
                     InlineKeyboardButton(text=_("Done"),
                                          callback_data="useCards")])

    if is_sort_suit:
        keyboard.append([InlineKeyboardButton(text=_("Sort by number"),
                                              callback_data="sortNum"),
                         InlineKeyboardButton(text=_("PASS"),
                                              callback_data="pass")])
    else:
        keyboard.append([InlineKeyboardButton(text=_("Sort by suit"),
                                              callback_data="sortSuit"),
                         InlineKeyboardButton(text=_("PASS"),
                                              callback_data="pass")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if is_edit:
        bot_message = bot.editMessageText(text=message,
                                          chat_id=player_tele_id,
                                          message_id=message_id,
                                          reply_markup=reply_markup)
    else:
        bot_message = bot.sendMessage(chat_id=player_tele_id,
                                      text=message,
                                      reply_markup=reply_markup)

    job_context = "%d,%d,%d" % (group_tele_id, player_tele_id, bot_message.message_id)
    cur.execute("select pass_timer from game_timer where group_tele_id = %s", (group_tele_id,))
    row = cur.fetchone()
    db.close()
    if row is None:
        job = job_queue.run_once(pass_round, 45, context=job_context)
    else:
        pass_timer = row[0]
        job = job_queue.run_once(pass_round, pass_timer, context=job_context)
    queued_jobs[group_tele_id]["pass"] = job


# Returns a string a message that contains info of the game
def get_game_message(group_tele_id, game_round, curr_player, player_in_control):
    message = ""
    db = connect_db()
    cur = db.cursor()

    cur.execute("select player_name from player where group_tele_id = %s and player_id = %s",
                (group_tele_id, curr_player))
    player_name = cur.fetchone()[0]

    cur.execute("select player_name from player where group_tele_id = %s and player_id = %s",
                (group_tele_id, player_in_control))
    control_player_name = cur.fetchone()[0]

    # Stores the number of cards that each player has
    player_dict = {}
    cur.execute("select player_id, player_name, num_cards from player where group_tele_id = %s", (group_tele_id,))
    for row in cur.fetchall():
        player = "%d. %s" % (row[0], row[1])
        player_dict[player] = row[2]

    # Displays the number of cards that each player has
    for player in sorted(player_dict.keys()):
        message += _("%s has %d cards\n") % (player, player_dict[player])
    message += "--------------------------------------\n"

    # Checks if player is in control
    if game_round > 1 and curr_player == player_in_control:
        message += _("%s is in control now\n") % player_name
        message += "--------------------------------------\n"
    elif game_round > 1:
        message += _("%s used:\n") % control_player_name

        cur.execute("select suit, num from prev_card where group_tele_id = %s", (group_tele_id,))
        for row in cur.fetchall():
            card = Card(row[0], row[1])
            message += str(card.show_suit)
            message += " "
            message += str(card.show_num)
            message += "\n"

        message += "--------------------------------------\n"

    db.close()

    return message


# Forces to stop a game (admin only)
@run_async
def force_stop(bot, update):
    player_tele_id = update.message.from_user.id
    install_lang(player_tele_id)

    if update.message.chat.type != "group":
        message = _("You can only use this command in a group")
        bot.sendMessage(player_tele_id, message)
        return

    group_tele_id = update.message.chat.id
    is_admin = False
    admins = bot.getChatAdministrators(group_tele_id)

    for admin in admins:
        if admin.user.id == player_tele_id:
            is_admin = True
            break

    if not is_admin:
        message = _("You are not a group admin")
        bot.sendMessage(player_tele_id, message)
        return

    db = connect_db()
    cur = db.cursor()

    cur.execute("select * from game where group_tele_id = %s", (group_tele_id,))
    if not cur.fetchone():
        message = _("No game is running at the moment")
        bot.sendMessage(player_tele_id, message)
        db.close()
        return
    db.close()

    install_lang(group_tele_id)
    message = (_("Game has been stopped by [%s]") %
               update.message.from_user.first_name)
    bot.sendMessage(group_tele_id, message)

    delete_game_data(group_tele_id)


# Shows the deck of cards of the player
@run_async
def show_deck(bot, update):
    player_tele_id = update.message.from_user.id
    install_lang(player_tele_id)
    db = connect_db()
    cur = db.cursor()

    # Checks if player in game
    cur.execute("select group_tele_id from player_group where player_tele_id = %s", (player_tele_id,))
    group_tele_id = cur.fetchone()
    if group_tele_id is None:
        message = _("You are not in a game")
        bot.sendMessage(player_tele_id, message)
        db.close()
        return
    group_tele_id = group_tele_id[0]

    # Checks if there is a game
    cur.execute("select * from game where group_tele_id = %s", (group_tele_id,))
    if not cur.fetchone():
        message = _("No game is running at the moment")
        bot.sendMessage(player_tele_id, message)
        db.close()
        return

    cur.execute("select player_id from player where group_tele_id = %s and player_tele_id = %s",
                (group_tele_id, player_tele_id,))
    player_id = cur.fetchone()[0]

    cur.execute("select suit, num from player_deck where group_tele_id = %s and player_id = %s",
                (group_tele_id, player_id,))
    rows = cur.fetchall()
    if not rows:
        message = _("Game has not started yet")
        bot.sendMessage(player_tele_id, message)
        db.close()
        return

    message = _("Your deck of cards:\n")
    for row in rows:
        card = Card(row[0], row[1])
        message += str(card.show_suit)
        message += " "
        message += str(card.show_num)
        message += "\n"
    db.close()

    bot.sendMessage(player_tele_id, message)


# Handles inline buttons
def in_line_button(bot, update, job_queue):
    query = update.callback_query
    player_tele_id = query.message.chat_id
    message_id = query.message.message_id
    data = query.data

    if re.match("set_lang", data):
        change_lang(bot, player_tele_id, message_id, data)
        return

    db = connect_db()
    cur = db.cursor()

    cur.execute("select group_tele_id from player_group where player_tele_id = %s", (player_tele_id,))
    group_tele_id = cur.fetchone()
    # Checks if player in game
    if group_tele_id is None:
        db.close()
        return
    group_tele_id = group_tele_id[0]

    # Checks if game is running
    cur.execute("select curr_player from game where group_tele_id = %s", (group_tele_id,))
    curr_player = cur.fetchone()
    if curr_player is None:
        db.close()
        return
    curr_player = curr_player[0]

    # Checks if outdated button
    cur.execute("select player_tele_id from player where group_tele_id = %s and player_id = %s",
                (group_tele_id, curr_player))
    curr_player_tele_id = cur.fetchone()[0]
    if player_tele_id != curr_player_tele_id:
        db.close()
        return
    db.close()

    queued_jobs[group_tele_id]["pass"].schedule_removal()

    if re.match("\d,\d+", data):
        add_use_card(bot, group_tele_id, message_id, curr_player, data, job_queue)
    elif data == "useCards":
        use_selected_cards(bot, player_tele_id, group_tele_id, message_id, job_queue)
    elif data == "unselect":
        unselect_use_cards(bot, group_tele_id, message_id, curr_player, job_queue)
    elif data == "pass":
        db = connect_db()
        cur = db.cursor()
        cur.execute("update game set count_pass = 0 where group_tele_id = %s", (group_tele_id,))
        db.commit()
        db.close()
        job_context = "%d,%d,%d" % (group_tele_id, player_tele_id, message_id)
        job_queue.run_once(pass_round, 0, context=job_context)
    elif data == "sortSuit":
        player_message(bot, group_tele_id, True, message_id, True, job_queue)  # Edit and sort suit
    elif data == "sortNum":
        player_message(bot, group_tele_id, True, message_id, False, job_queue)  # Edit and not sort suit


# Changes the default language of a player/group
def change_lang(bot, tele_id, message_id, data):
    lang = re.sub(".*,", "", data)
    db = connect_db()
    cur = db.cursor()

    cur.execute("select * from user_language where tele_id = %s", (tele_id,))
    if cur.fetchone():
        cur.execute("update user_language set language = %s where tele_id = %s", (lang, tele_id))
    else:
        cur.execute("insert into user_language (tele_id, language) values (%s, %s)", (tele_id, lang))

    db.commit()
    db.close()

    install_lang(tele_id)
    bot.editMessageText(text=_("Default language has been set"),
                        chat_id=tele_id,
                        message_id=message_id)


# Adds a selected card
def add_use_card(bot, group_tele_id, message_id, curr_player, card, job_queue):
    suit, num = map(int, card.split(","))

    db = connect_db()
    cur = db.cursor()
    cur.execute("delete from player_deck where group_tele_id = %s and player_id = %s and suit = %s and num = %s",
                (group_tele_id, curr_player, suit, num))
    cur.execute("insert into curr_card (group_tele_id, suit, num) values (%s, %s, %s)", (group_tele_id, suit, num))
    db.commit()
    db.close()

    player_message(bot, group_tele_id, True, message_id, False, job_queue)  # Edit and not sort suit


# Uses the selected cards
def use_selected_cards(bot, player_tele_id, group_tele_id, message_id, job_queue):
    install_lang(player_tele_id)
    valid = True
    bigger = True
    prev_cards = []
    use_cards = []

    db = connect_db()
    cur = db.cursor()
    cur.execute("select curr_player, player_in_control, game_round from game where group_tele_id = %s",
                (group_tele_id,))
    curr_player, player_in_control, game_round = cur.fetchone()

    cur.execute("select player_name, num_cards from player where group_tele_id = %s and player_id = %s",
                (group_tele_id, curr_player))
    player_name, num_cards = cur.fetchone()

    cur.execute("select suit, num from prev_card where group_tele_id = %s", (group_tele_id,))
    for row in cur.fetchall():
        prev_cards.append(Card(row[0], row[1]))

    cur.execute("select suit, num from curr_card where group_tele_id = %s", (group_tele_id,))
    for row in cur.fetchall():
        use_cards.append(Card(row[0], row[1]))

    db.close()

    prev_cards.sort()
    use_cards.sort()

    if len(use_cards) == 0:
        return

    if get_cards_type(use_cards) == -1 or (game_round == 1 and Card(0, 3) not in use_cards) or \
            (curr_player != player_in_control and len(prev_cards) != 0 and len(prev_cards) != len(use_cards)):
        valid = False

    if valid and curr_player != player_in_control and not are_cards_bigger(prev_cards, use_cards):
        bigger = False

    if not valid:
        message = _("Invalid cards. Please try again\n")
        return_cards_to_deck(group_tele_id, curr_player)
    elif not bigger:
        message = _("You cards are not bigger than the previous cards. ")
        message += _("Please try again\n")
        return_cards_to_deck(group_tele_id, curr_player)
    else:
        message = _("These cards have been used:\n")
        for card in use_cards:
            message += str(card.show_suit)
            message += " "
            message += str(card.show_num)
            message += "\n"
        bot.editMessageText(message, player_tele_id, message_id)

        new_num_cards = num_cards - len(use_cards)

        db = connect_db()
        cur = db.cursor()
        cur.execute("update player set num_cards = %s where group_tele_id = %s and player_id = %s",
                    (new_num_cards, group_tele_id, curr_player))
        cur.execute("delete from curr_card where group_tele_id = %s", (group_tele_id,))
        cur.execute("delete from prev_card where group_tele_id = %s", (group_tele_id,))
        for card in use_cards:
            cur.execute("insert into prev_card (group_tele_id, suit, num) values (%s, %s, %s)",
                        (group_tele_id, card.suit, card.num))
        db.commit()
        db.close()

        if new_num_cards == 0:
            finish_game(bot, group_tele_id, player_tele_id, curr_player, player_name, use_cards)
            return
        else:
            advance_game(bot, group_tele_id, game_round, curr_player, player_name, use_cards)

    if valid and bigger:
        player_message(bot, group_tele_id, False, 0, False, job_queue)  # Not edit and not sort suit
    else:
        player_message(bot, group_tele_id, True, message_id, False, job_queue)  # Edit and not sort suit
        bot.sendMessage(player_tele_id, message)


# Retruns curr_cards to the player's deck
def return_cards_to_deck(group_tele_id, curr_player):
    db = connect_db()
    cur = db.cursor()

    cur.execute("select suit, num from curr_card where group_tele_id = %s", (group_tele_id,))
    for row in cur.fetchall():
        cur.execute("insert into player_deck (group_tele_id, player_id, suit, num)"
                    "values (%s, %s, %s, %s)", (group_tele_id, curr_player, row[0], row[1]))
    cur.execute("delete from curr_card where group_tele_id = %s", (group_tele_id,))

    db.commit()
    db.close()


# Unselects the selected cards
def unselect_use_cards(bot, group_tele_id, message_id, curr_player, job_queue):
    return_cards_to_deck(group_tele_id, curr_player)
    player_message(bot, group_tele_id, True, message_id, False, job_queue)


# Advances the game
def advance_game(bot, group_tele_id, game_round, curr_player, player_name, use_cards):
    game_round += 1
    player_in_control = curr_player
    curr_player = (curr_player + 1) % 4

    db = connect_db()
    cur = db.cursor()
    cur.execute("update game set game_round = %s, curr_player = %s, player_in_control = %s where group_tele_id = %s",
                (game_round, curr_player, player_in_control, group_tele_id))
    db.commit()
    db.close()

    game_message(bot, group_tele_id)

    if len(use_cards) == 1 and use_cards[0].suit == 3 and use_cards[0].num == 15:
        curr_player = (curr_player - 1) % 4

        db = connect_db()
        cur = db.cursor()
        cur.execute("update game set curr_player = %s where group_tele_id = %s", (curr_player, group_tele_id))
        db.commit()
        db.close()

        message = (_("I have passed all players since %s has used %s%s\n") %
                   (player_name, use_cards[0].show_suit, use_cards[0].show_num))
        message += "--------------------------------------\n"
        message += _("%s's Turn\n") % player_name

        bot.sendMessage(group_tele_id, message, disable_notification=True)


# Game over
def finish_game(bot, group_tele_id, player_tele_id, curr_player, player_name, use_cards):
    db = connect_db()
    cur = db.cursor()

    bot.sendMessage(player_tele_id, _("You won!"))

    cur.execute("select player_tele_id from player where group_tele_id = %s and player_id != %s",
                (group_tele_id, curr_player))
    for row in cur.fetchall():
        install_lang(row[0])
        bot.sendMessage(row[0], _("You lost!"))

    db.close()

    install_lang(group_tele_id)
    message = _("These cards have been used:\n")
    for card in use_cards:
        message += str(card.show_suit)
        message += " "
        message += str(card.show_num)
        message += "\n"
    message += "--------------------------------------\n"
    message += _("%s won!") % player_name

    bot.sendMessage(group_tele_id, message, disable_notification=True)

    delete_game_data(group_tele_id)


# Passes player's turn
def pass_round(bot, job):
    group_tele_id, player_tele_id, message_id = map(int, job.context.split(","))
    install_lang(player_tele_id)

    db = connect_db()
    cur = db.cursor()
    cur.execute("select game_round, curr_player, count_pass from game where group_tele_id = %s", (group_tele_id,))
    try:
        game_round, curr_player, count_pass = cur.fetchone()
    except TypeError:
        db.close()
        return
    db.close()

    game_round += 1
    curr_player = (curr_player + 1) % 4
    count_pass += 1

    try:
        bot.editMessageText(text=_("You Passed"),
                            chat_id=player_tele_id,
                            message_id=message_id)
    except:
        return

    if count_pass > 4:
        stop_idle_game(bot, group_tele_id)
        return

    return_cards_to_deck(group_tele_id, curr_player)

    db = connect_db()
    cur = db.cursor()
    cur.execute("update game set game_round = %s, curr_player = %s, count_pass = %s where group_tele_id = %s",
                (game_round, curr_player, count_pass, group_tele_id))
    db.commit()
    db.close()

    game_message(bot, group_tele_id)
    player_message(bot, group_tele_id, False, 0, False, job.job_queue)


# Stops an idle game
def stop_idle_game(bot, group_tele_id):
    install_lang(group_tele_id)
    message = _("Game has been stopped by me since no one is playing")
    bot.sendMessage(group_tele_id, message)

    delete_game_data(group_tele_id)


# Installs the language
def install_lang(tele_id):
    db = connect_db()
    cur = db.cursor()
    cur.execute("select language from user_language where tele_id = %s", (tele_id,))
    cursor = cur.fetchone()

    if cursor is None:
        es = gettext.translation("big_two_text", localedir="locale", languages=["en"])
        es.install()
    else:
        lang = cursor[0]
        es = gettext.translation("big_two_text", localedir="locale", languages=[lang])
        es.install()

    db.close()


# Creates a feedback conversation handler
def feedback_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('feedback', feedback)],

        states={
            0: [MessageHandler(Filters.text, receive_feedback)],
        },

        fallbacks=[CommandHandler("cancel", cancel)],

        allow_reentry=True
    )

    return conv_handler


# Sends a feedback message
@run_async
def feedback(bot, update):
    install_lang(update.message.from_user.id)
    update.message.reply_text(_("Please send me your feedback or type /cancel to cancel this operation. My developer "
                                "can understand English and Chinese."))

    return 0


# Saves a feedback
def receive_feedback(bot, update):
    feedback_msg = update.message.text
    valid_lang = False
    langdetect.DetectorFactory.seed = 0
    langs = langdetect.detect_langs(feedback_msg)

    for lang in langs:
        if lang.lang in ("en", "zh-tw", "zh-cn"):
            valid_lang = True
            break

    if not valid_lang:
        update.message.reply_text(_("The feedback you sent is not in English or Chinese. Please try again."))
        return 0

    install_lang(update.message.from_user.id)
    update.message.reply_text(_("Thank you for your feedback, I will let my developer know."))

    if is_email_feedback:
        server = smtplib.SMTP(smtp_host)
        server.ehlo()
        server.starttls()
        server.login(dev_email, dev_email_pw)

        text = "Feedback received from %d\n\n%s" % (update.message.from_user.id, update.message.text)
        message = "Subject: %s\n\n%s" % ("Telegram Big Two Bot Feedback", text)
        server.sendmail(dev_email, dev_email, message)
    else:
        logger.info("Feedback received from %d: %s" % (update.message.from_user.id, update.message.text))

    return ConversationHandler.END


# Cancels feedback opteration
def cancel(bot, update):
    update.message.reply_text(_("Operation cancelled."))
    return ConversationHandler.END


# Sends a message to a specified user
def send(bot, update, args):
    if update.message.from_user.id == dev_tele_id:
        tele_id = int(args[0])
        message = " ".join(args[1:])

        try:
            bot.send_message(tele_id, message)
        except Exception as e:
            logger.exception(e)
            bot.send_message(dev_tele_id, "Failed to send message")


# Bot status for dev
def status(bot, update):
    if update.message.from_user.id == dev_tele_id:
        db = connect_db()
        cur = db.cursor()

        cur.execute("select count(*) from user_language where tele_id > 0")
        num_users = cur.fetchone()[0]

        cur.execute("select count(*) from user_language where tele_id < 0")
        num_groups = cur.fetchone()[0]

        cur.execute("select count(*) from game")
        num_games = cur.fetchone()[0]

        db.close()

        message = "Number of users: %d\nNumber of groups: %d\nNumber of games: %d" % (num_users, num_groups, num_games)
        bot.send_message(dev_tele_id, message)


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"' % (update, error))


def main():
    create_db_tables()

    # Create the EventHandler and pass it your bot's token.
    updater = Updater(telegram_token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher
    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("command", command))
    dp.add_handler(CommandHandler("donate", donate))
    dp.add_handler(CommandHandler("setlang", set_lang))
    dp.add_handler(CommandHandler("setjointimer", set_join_timer))
    dp.add_handler(CommandHandler("setpasstimer", set_pass_timer))
    dp.add_handler(CommandHandler("startgame", start_game, pass_job_queue=True))
    dp.add_handler(CommandHandler("join", join, pass_job_queue=True))
    dp.add_handler(CommandHandler("forcestop", force_stop))
    dp.add_handler(CommandHandler("showdeck", show_deck))
    dp.add_handler(feedback_cov_handler())
    dp.add_handler(CommandHandler("send", send, pass_args=True))
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CallbackQueryHandler(in_line_button, pass_job_queue=True))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    if app_url:
        updater.start_webhook(listen="0.0.0.0",
                              port=port,
                              url_path=telegram_token)
        updater.bot.set_webhook(app_url + telegram_token)
    else:
        updater.start_polling()

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()

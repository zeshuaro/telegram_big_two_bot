#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import dotenv
import gettext
import langdetect
import logging
import os
import pydealer
import random
import re
import smtplib

from sqlalchemy import create_engine, sql
from sqlalchemy.orm import sessionmaker

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Chat, ChatMember
from telegram.error import TelegramError, Unauthorized
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler, Filters, MessageHandler
from telegram.ext.dispatcher import run_async

import base
from languages import Language
from group_settings import GroupSetting
from cards import suit_unicode, get_cards_type, are_cards_bigger
from money import get_money_lost
from game import Game
from player import Player
from stats import GroupStat, PlayerStat

# Enable logging
logging.basicConfig(format="[%(asctime)s] [%(levelname)s] %(message)s", datefmt='%Y-%m-%d %I:%M:%S %p',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
dotenv.load(dotenv_path)
app_url = os.environ.get("APP_URL")
port = int(os.environ.get('PORT', '5000'))

telegram_token = os.environ.get("TELEGRAM_TOKEN_BETA", os.environ.get("TELEGRAM_TOKEN"))
dev_tele_id = int(os.environ.get("DEV_TELE_ID"))
dev_email = os.environ.get("DEV_EMAIL", "sample@email.com")
dev_email_pw = os.environ.get("DEV_EMAIL_PW")
is_email_feedback = os.environ.get("IS_EMAIL_FEEDBACK")
smtp_host = os.environ.get("SMTP_HOST")

engine = create_engine(os.environ.get("DATABASE_URL"))
Player.__table__.drop(engine)
Game.__table__.drop(engine)
base.Base.metadata.create_all(engine, checkfirst=True)
Session = sessionmaker(bind=engine)
session = Session()

init_money = 1000
card_money = 5
queued_jobs = {}


def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(telegram_token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher
    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_msg))
    dp.add_handler(CommandHandler("command", command))
    dp.add_handler(CommandHandler("donate", donate))
    dp.add_handler(CommandHandler("setlang", set_lang))
    dp.add_handler(CommandHandler("setjointimer", set_join_timer, pass_args=True))
    dp.add_handler(CommandHandler("setpasstimer", set_pass_timer, pass_args=True))
    dp.add_handler(CommandHandler("setgamemode", set_game_mode, pass_args=True))
    dp.add_handler(CommandHandler("startgame", start_game, pass_job_queue=True))
    dp.add_handler(CommandHandler("join", join, pass_job_queue=True))
    dp.add_handler(CommandHandler("forcestop", force_stop))
    dp.add_handler(CommandHandler("showdeck", show_deck))
    dp.add_handler(CommandHandler("stats", show_stat))
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


# Sends start message
@run_async
def start(bot, update):
    tele_id = update.message.chat.id
    install_lang(tele_id)

    if update.message.chat.type not in (Chat.GROUP, Chat.SUPERGROUP):
        message = _("Welcome to Big Two Moderator. Add me into a group and type /startgame to start a game.\n\nYou "
                    "can also type /setlang to change the bot's language.\n\nPlease note that you can only use "
                    "/setlang for changing the bot's language in a group if you are a group admin.")

        bot.send_message(tele_id, message)
        make_player_stat(tele_id, update.message.from_user.first_name)


# Creates player's stats
def make_player_stat(player_tele_id, player_name):
    if not session.query(PlayerStat).filter(PlayerStat.tele_id == player_tele_id):
        player_stat = PlayerStat(tele_id=player_tele_id, player_name=player_name, num_games=0, num_games_won=0,
                                 num_cards=0, win_rate=0, money=init_money, money_earned=0)
        session.add(player_stat)
        session.commit()


# Sends help message
@run_async
def help_msg(bot, update):
    player_tele_id = update.message.from_user.id
    install_lang(player_tele_id)
    keyboard = [[InlineKeyboardButton("Rate me", "https://t.me/storebot?start=biggytwobot")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = _("Add me into a group and type /startgame to start a game. Other players can then type /join to join "
                "the game.\n\nYou will not be able to start or join a game if a game has already been set up and "
                "running.\n\nYou can only force to stop a game if you are a group admin.\n\nUse /command to get a "
                "list of commands to see what I can do.")

    bot.send_message(player_tele_id, message, reply_markup=reply_markup)


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

    bot.send_message(player_tele_id, message)


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
    if update.message.chat.type == Chat.PRIVATE:
        tele_id = update.message.from_user.id
        install_lang(tele_id)
        message = _("Pick your default language from below\n\n")
    elif update.message.chat.type in (Chat.GROUP, Chat.SUPERGROUP):
        tele_id = update.message.chat.id
        install_lang(tele_id)
        message = _("Pick the group's default language from below\n\n")

        member = bot.get_chat_member(update.message.chat.id, update.message.from_user.id)
        if member.status not in (ChatMember.ADMINISTRATOR, ChatMember.CREATOR):
            try:
                bot.send_message(update.message.from_user.id, _("You are not a group admin"))
            except:
                pass

            return
    else:
        return

    keyboard = [[InlineKeyboardButton("English", callback_data="set_lang,en"),
                 InlineKeyboardButton("廣東話", callback_data="set_lang,zh-hk")],
                [InlineKeyboardButton("正體中文", callback_data="set_lang,zh-tw"),
                 InlineKeyboardButton("简体中文", callback_data="set_lang,zh-cn")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    bot.send_message(tele_id, message, reply_markup=reply_markup)


# Sets join timer
@run_async
def set_join_timer(bot, update, args):
    if args:
        set_game_timer(bot, update, "join", args[0])


# Sets pass timer
@run_async
def set_pass_timer(bot, update, args):
    if args:
        set_game_timer(bot, update, "pass", args[0])


# Sets game mode
@run_async
def set_game_mode(bot, update, args):
    if args:
        set_group_setting(bot, update, game_mode=args[0])


# Changes the group settings
def set_group_setting(bot, update, timer_type=None, timer=None, game_mode=None):
    group_tele_id = update.message.chat.id
    player_tele_id = update.message.from_user.id
    install_lang(player_tele_id)

    if update.message.chat.type not in (Chat.GROUP, Chat.SUPERGROUP):
        message = _("You can only use this command in a group")
        bot.send_message(player_tele_id, message)
        return

    member = bot.get_chat_member(group_tele_id, player_tele_id)
    if member.status not in (ChatMember.ADMINISTRATOR, ChatMember.CREATOR):
        bot.send_message(player_tele_id, _("You are not a group admin"))
        return

    if session.query(Game).filter(Game.group_tele_id == group_tele_id).first():
        bot.send_message(player_tele_id, _("You can only change the group's settings when a game is not running"))
        return

    if re.match("/set(join|pass)timer", update.message.text):
        set_game_timer(bot, group_tele_id, timer_type, timer)
    else:
        game_mode = game_mode.lower()
        if game_mode not in ("normal", "money"):
            bot.send_message(group_tele_id, "Game mode can either be set to 'normal' or 'money'")
            return

        group_settings = session.query(GroupSetting).filter(GroupSetting.tele_id == group_tele_id).first()
        if group_settings:
            if game_mode == "normal":
                group_settings.money_mode = False
            else:
                group_settings.money_mode = True
        else:
            if game_mode == "normal":
                group_settings = GroupSetting(tele_id=group_tele_id, money_mode=False)
            else:
                group_settings = GroupSetting(tele_id=group_tele_id, money_mode=True)
            session.add(group_settings)

        session.commit()
        bot.send_message(group_tele_id, "Game mode has been set to '%s'" % game_mode)


# Sets game timer
def set_game_timer(bot, group_tele_id, timer_type, timer):
    install_lang(group_tele_id)

    if not re.match("\d+", timer) or (timer_type == "join_timer" and int(timer) not in range(10, 61)) or \
            (timer_type == "pass_timer" and int(timer) not in range(20, 121)):
        if timer_type == "join":
            message = _("Join timer can only be set between 10s to 60s")
        else:
            message = _("Pass timer can only be set between 20s to 120s")
        bot.send_message(group_tele_id, message)
        return

    timer = int(timer)
    group_settings = session.query(GroupSetting).filter(GroupSetting.tele_id == group_tele_id).first()

    if group_settings:
        if timer_type == "join":
            group_settings.join_timer = timer
        else:
            group_settings.pass_timer = timer
    else:
        if timer_type == "join":
            group_settings = GroupSetting(tele_id=group_tele_id, join_timer=timer)
        else:
            group_settings = GroupSetting(tele_id=group_tele_id, pass_timer=timer)
        session.add(group_settings)
    session.commit()

    if timer_type == "join":
        bot.send_message(group_tele_id, _("Join timer has been set to %ds") % timer)
    else:
        bot.send_message(group_tele_id, _("Pass timer has been set to %ds") % timer)


# Starts a new game
def start_game(bot, update, job_queue):
    group_tele_id = update.message.chat.id
    player_name = update.message.from_user.first_name
    install_lang(update.message.from_user.id)

    if update.message.chat.type not in (Chat.GROUP, Chat.SUPERGROUP):
        bot.send_message(group_tele_id, _("You can only use this command in a group"))
        return

    if not can_msg_player(bot, update):
        return

    if session.query(Game).filter(Game.group_tele_id == group_tele_id).first():
        bot.send_message(update.message.from_user.id, _("A game has already been started"))
        return

    game = Game(group_tele_id=group_tele_id, game_round=1, curr_player=-1, biggest_player=-1, count_pass=0,
                curr_cards=pydealer.Stack(), prev_cards=pydealer.Stack())
    session.add(game)
    session.commit()

    install_lang(group_tele_id)
    text = _("[%s] has started Big Two. Type /join to join the game\n\n" % player_name)

    bot.send_message(chat_id=group_tele_id,
                     text=text,
                     disable_notification=True)

    make_group_setting(group_tele_id)
    join(bot, update, job_queue)


# Creates group settings
def make_group_setting(group_tele_id):
    if not session.query(GroupSetting).filter(GroupSetting.tele_id == group_tele_id):
        group_settings = GroupSetting(tele_id=group_tele_id, join_timer=60, pass_timer=45, money_mode=False)
        session.add(group_settings)
        session.commit()


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

        text = (_("[%s] Please PM [@biggytwobot] and say [/start]. Otherwise, you won't be able to join and "
                  "play Big Two") % player_name)

        keyboard = [[InlineKeyboardButton(text=_("Say start to me"), url="https://telegram.me/biggytwobot")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        bot.send_message(chat_id=group_tele_id, text=text, reply_markup=reply_markup)
    else:
        bot.delete_message(chat_id=player_tele_id, message_id=bot_message.message_id)

    return is_success


# Joins a new game
def join(bot, update, job_queue):
    player_name = update.message.from_user.first_name
    player_tele_id = update.message.from_user.id
    group_name = update.message.chat.title
    group_tele_id = update.message.chat.id

    install_lang(player_tele_id)

    if update.message.chat.type not in (Chat.GROUP, Chat.SUPERGROUP):
        bot.send_message(player_tele_id, _("You can only use this command in a group"))
        return

    if not can_msg_player(bot, update):
        return

    # Checks if there exists a game
    if not session.query(Game).filter(Game.group_tele_id == group_tele_id).first():
        text = _("A game has not been started yet. Type /startgame in a group to start a game.")
        bot.send_message(player_tele_id, text)
        return

    # Checks if player is in game
    if session.query(Player).filter(Player.player_tele_id == player_tele_id).first():
        bot.send_message(player_tele_id, _("You have already joined a game"))
        return

    num_players = session.query(Player).filter(Player.group_tele_id == group_tele_id).count()

    # Checks for valid number of players
    if num_players < 4:
        join_timer, pass_timer, money_mode = session.\
            query(GroupSetting.join_timer, GroupSetting.pass_timer, GroupSetting.money_mode).\
            filter(GroupSetting.tele_id == group_tele_id).first()

        if money_mode:
            player_money = session.query(PlayerStat.money).filter(PlayerStat.tele_id == player_tele_id).first()
            if player_money <= 0:
                bot.send_message(player_tele_id, "You don't have any money left to join the game.")
                return

        player = Player(group_tele_id=group_tele_id, player_tele_id=player_tele_id, player_name=player_name,
                        player_id=num_players, cards=pydealer.Stack(), num_cards=13)
        session.add(player)
        session.commit()
        num_players += 1

        install_lang(group_tele_id)
        text = (_("[%s] has joined.\nThere are now %d/4 Players\n") % (player_name, num_players))

        if group_tele_id in queued_jobs:
            queued_jobs[group_tele_id].schedule_removal()

        if num_players != 4:
            job = job_queue.run_once(stop_empty_game, join_timer, context=group_tele_id)
            queued_jobs[group_tele_id] = job
            text += _("%ss left to join") % join_timer

        bot.send_message(chat_id=group_tele_id, text=text, disable_notification=True)

        install_lang(player_tele_id)
        bot.send_message(player_tele_id, _("You have joined the game in the group [%s]") % group_name)

        if num_players == 4:
            install_lang(group_tele_id)
            text = _("Enough players, game start. I will PM your deck of cards when it is your turn. ")
            text += _("Each player has %ss to pick your cards") % pass_timer
            bot.send_message(chat_id=group_tele_id, text=text, disable_notification=True)

            setup_game(group_tele_id)
            game_message(bot, group_tele_id)
            player_message(bot, group_tele_id, job_queue)


# Stops a game without enough players
def stop_empty_game(bot, job):
    group_tele_id = job.context
    install_lang(group_tele_id)
    bot.send_message(group_tele_id, _("Game has been stopped by me since there is no enough players."))

    delete_game_data(group_tele_id)


# Deletes game data with the given group telegram ID
def delete_game_data(group_tele_id):
    if group_tele_id in queued_jobs:
        queued_jobs[group_tele_id].schedule_removal()

    game = session.query(Game).filter(Game.group_tele_id == group_tele_id).first()
    session.delete(game)
    session.commit()


# Sets up a game
def setup_game(group_tele_id):
    player_tele_ids = session.query(Player.player_tele_id).filter(Player.group_tele_id == group_tele_id).all()
    random.shuffle(player_tele_ids)

    # Creates a deck of cards in random order
    deck = pydealer.Deck(ranks=pydealer.BIG2_RANKS)
    deck.shuffle()

    # Sets up players
    curr_player = -1

    for i, player_tele_id in enumerate(player_tele_ids):
        player_cards = pydealer.Stack(cards=deck.deal(13))
        player_cards.sort(ranks=pydealer.BIG2_RANKS)

        # Player with ♦3 starts first
        if player_cards.find("3D"):
            curr_player = i

        player = session.query(Player).filter(Player.player_tele_id == player_tele_id).first()
        player.player_id = i
        player.cards = player_cards
        session.commit()

    game = session.query(Game).filter(Game.group_tele_id == group_tele_id).first()
    game.curr_player = game.biggest_player = curr_player
    session.commit()


# Sends message to game group
def game_message(bot, group_tele_id):
    install_lang(group_tele_id)
    text = ""

    game_round, curr_player, biggest_player, curr_player_name = session. \
        query(Game.game_round, Game.curr_player, Game.biggest_player, Player.player_name). \
        filter(Game.group_tele_id == group_tele_id, Player.player_id == Game.curr_player).first()

    if game_round > 1 and curr_player != (biggest_player + 1) % 4:
        prev_player_id = (curr_player - 1) % 4
        prev_player_name = session.query(Player.player_name). \
            filter(Player.group_tele_id == group_tele_id, Player.player_id == prev_player_id).first()

        text += "--------------------------------------\n"
        text += _("%s decided to PASS\n") % prev_player_name

    text += "--------------------------------------\n"
    text += _("%s's Turn\n") % curr_player_name
    text += "--------------------------------------\n"

    text += get_game_message(group_tele_id, game_round, curr_player, biggest_player)

    bot.send_message(group_tele_id, text, disable_notification=True)


# Sends message to player
def player_message(bot, group_tele_id, job_queue, is_sort_suit=False, is_edit=False, message_id=None):
    text = ""

    game, player = session.query(Game, Player). \
        filter(Game.group_tele_id == group_tele_id, Player.group_tele_id == group_tele_id,
               Player.player_id == Game.curr_player).first()
    game_round, curr_player, biggest_player, cards = \
        game.game_round, game.curr_player, game.biggest_player, game.curr_cards
    player_tele_id = player.player_tele_id

    install_lang(player_tele_id)
    text += get_game_message(group_tele_id, game_round, curr_player, biggest_player)

    # Checks if to display selected cards
    if cards:
        cards.sort(ranks=pydealer.BIG2_RANKS)
        text += _("Selected cards:\n")

        for card in cards:
            text += suit_unicode(card.suit)
            text += " "
            text += str(card.value)
            text += "\n"

        text += "--------------------------------------\n"

    cards = player.cards
    card_list = []

    if is_sort_suit:
        cards = sorted(cards.cards, key=lambda x: x.suit)
    else:
        cards.sort(ranks=pydealer.BIG2_RANKS)

    for card in cards:
        show_card = suit_unicode(card.suit)
        show_card += " "
        show_card += str(card.value)

        card_list.append(InlineKeyboardButton(text=show_card, callback_data=card.abbrev))

    keyboard = [card_list[i:i + 4] for i in range(0, len(card_list), 4)]
    keyboard.append([InlineKeyboardButton(text=_("Unselect"), callback_data="unselect"),
                     InlineKeyboardButton(text=_("Done"), callback_data="useCards")])

    if is_sort_suit:
        keyboard.append([InlineKeyboardButton(text=_("Sort by number"), callback_data="sortNum"),
                         InlineKeyboardButton(text=_("PASS"), callback_data="pass")])
    else:
        keyboard.append([InlineKeyboardButton(text=_("Sort by suit"), callback_data="sortSuit"),
                         InlineKeyboardButton(text=_("PASS"), callback_data="pass")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if is_edit:
        try:
            bot.editMessageText(text=text, chat_id=player_tele_id, message_id=message_id, reply_markup=reply_markup)
        except:
            pass
    else:
        bot_message = bot.send_message(chat_id=player_tele_id, text=text, reply_markup=reply_markup)
        message_id = bot_message.message_id

    job_context = "%d,%d,%d" % (group_tele_id, player_tele_id, message_id)
    pass_timer = session.query(GroupSetting.pass_timer).filter(GroupSetting.tele_id == group_tele_id).first()
    job = job_queue.run_once(pass_round, pass_timer, context=job_context)
    queued_jobs[group_tele_id] = job


# Returns a string a message that contains info of the game
def get_game_message(group_tele_id, game_round, curr_player, biggest_player):
    text = ""

    player_name = session.query(Player.player_name). \
        filter(Player.group_tele_id == group_tele_id, Player.player_id == curr_player).first()
    biggest_player_name = session.query(Player.player_name). \
        filter(Player.group_tele_id == group_tele_id, Player.player_id == biggest_player).first()

    # Stores the number of cards that each player has
    playes_info = {}
    players = session.query(Player).filter(Player.group_tele_id == group_tele_id).all()
    for player in players:
        player_id, player_name, num_cards = player.player_id, player.player_name, player.num_cards
        player = "%d. %s" % (player_id, player_name)
        playes_info[player] = num_cards

    # Displays the number of cards that each player has
    for player in sorted(playes_info.keys()):
        text += _("%s has %d cards\n") % (player, playes_info[player])
    text += "--------------------------------------\n"

    # Checks if player is in control
    if game_round > 1 and curr_player == biggest_player:
        text += _("%s is in control now\n") % player_name
        text += "--------------------------------------\n"
    elif game_round > 1:
        text += _("%s used:\n") % biggest_player_name
        game = session.query(Game).filter(Game.group_tele_id == group_tele_id).first()
        cards = game.prev_cards

        for card in cards:
            text += suit_unicode(card.suit)
            text += " "
            text += str(card.value)
            text += "\n"

        text += "--------------------------------------\n"

    return text


# Forces to stop a game (admin only)
@run_async
def force_stop(bot, update):
    group_tele_id = update.message.chat.id
    player_tele_id = update.message.from_user.id
    install_lang(player_tele_id)

    if update.message.chat.type not in (Chat.GROUP, Chat.SUPERGROUP):
        bot.send_message(player_tele_id, _("You can only use this command in a group"))
        return

    member = bot.get_chat_member(group_tele_id, player_tele_id)
    if member.status not in (ChatMember.ADMINISTRATOR, ChatMember.CREATOR):
        bot.send_message(player_tele_id, _("You are not a group admin"))
        return

    if not session.query(Game).filter(Game.group_tele_id == group_tele_id).first():
        bot.send_message(player_tele_id, _("No game is running at the moment"))
        return

    install_lang(group_tele_id)
    message = (_("Game has been stopped by [%s]") %
               update.message.from_user.first_name)
    bot.send_message(group_tele_id, message)

    delete_game_data(group_tele_id)


# Shows the deck of cards of the player
@run_async
def show_deck(bot, update):
    player_tele_id = update.message.from_user.id
    install_lang(player_tele_id)
    cards = session.query(Player.cards).filter(Player.player_tele_id == player_tele_id).first()[0]

    if not cards:
        bot.send_message(player_tele_id, _("You are not in a game"))
        return

    if cards.size == 0:
        bot.send_message(player_tele_id, _("Game has not started yet"))
        return

    text = _("Your deck of cards:\n")
    for card in cards:
        text += suit_unicode(card.suit)
        text += " "
        text += str(card.value)
        text += "\n"

    bot.send_message(player_tele_id, text)


# Shows stats
@run_async
def show_stat(bot, update):
    if update.message.chat.type in (Chat.PRIVATE, Chat.GROUP, Chat.SUPERGROUP):
        num_games = session.query(sql.func.sum(GroupStat.num_games)).first()[0]
        num_games = num_games if num_games else 0
        num_players = session.query(Language).filter(Language.tele_id > 0).count()
        num_groups = session.query(Language).filter(Language.tele_id < 0).count()

        text = "Global stats:\n"
        text += "Total number of games played: %d\n" % num_games
        text += "Total number of players: %d\n" % num_players
        text += "Total number of groups: %d\n\n" % num_groups

        if update.message.chat.type == Chat.PRIVATE:
            show_player_stat(bot, update.message.chat.id, text)
        else:
            player_callback_data = "playerStat,%d" % update.message.from_user.id
            keyboard = [[InlineKeyboardButton(text="Group Stats", callback_data="groupStat"),
                         InlineKeyboardButton(text="Player Stats", callback_data=player_callback_data)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            bot.send_message(update.message.chat.id, text, reply_markup=reply_markup)


# Sends the player's stats
def show_player_stat(bot, tele_id, text=""):
    player_stat = session.query(PlayerStat).filter(PlayerStat.tele_id == tele_id).first()

    if player_stat:
        num_games, num_cards, win_rate, money, money_earned = \
            player_stat.num_games, player_stat.num_cards, player_stat.win_rate, player_stat.money, \
            player_stat.money_earned

        text += "You have $%d\n" % money
        text += "You played %d games\n" % num_games
        text += "You used %d cards\n" % num_cards
        text += "Your win rate is %f%%\n" % win_rate
        text += "You earned $%d" % money_earned
    else:
        text += "I couldn't find any stats about you"

    try:
        bot.send_message(tele_id, text)
    except:
        pass


# Sends the group's stats
def show_group_stat(bot, tele_id):
    group_stat = session.query(GroupStat).filter(GroupStat.tele_id == tele_id).first()

    if group_stat:
        num_games, best_win_rate_player, best_win_rate, most_money_earned_player, most_money_earned = \
            group_stat.num_games, group_stat.best_win_rate_player, group_stat.best_win_rate, \
            group_stat.most_money_earned_player, group_stat.most_money_earned

        text = "Group's stats:\n"
        text += "Total number of games played: %d\n" % num_games
        text += "Highest win rate player: %s (%f%%)\n" % (best_win_rate_player, best_win_rate)
        text += "Most money earned player: %s ($%d)\n" % (most_money_earned_player, most_money_earned)
    else:
        text = "I couldn't find any stats about the group"

    bot.send_message(tele_id, text)


# Handles inline buttons
def in_line_button(bot, update, job_queue):
    query = update.callback_query
    player_tele_id = query.message.chat.id
    message_id = query.message.message_id
    data = query.data

    if re.match("set_lang", data):
        change_lang(bot, player_tele_id, message_id, data)
        return
    elif data == "groupStat":
        show_group_stat(bot, player_tele_id)
        return
    elif re.match("playerStat", data):
        show_player_stat(bot, int(data.split(",")[1]))
        return

    player = session.query(Player).filter(Player.player_tele_id == player_tele_id).first()

    # Checks if player in game
    if not player:
        return

    group_tele_id = player.group_tele_id
    if not session.query(Game, Player). \
            filter(Game.group_tele_id == group_tele_id, Player.player_tele_id == player_tele_id,
                   Game.curr_player == Player.player_id).first():
        return

    queued_jobs[group_tele_id].schedule_removal()

    if re.match("([2-9JQKA]|10)[DCHS]", data):
        add_use_card(bot, group_tele_id, message_id, data, job_queue)
    elif data == "useCards":
        use_selected_cards(bot, player_tele_id, group_tele_id, message_id, job_queue)
    elif data == "unselect":
        return_cards_to_deck(group_tele_id)
        player_message(bot, group_tele_id, job_queue, is_edit=True, message_id=message_id)
    elif data == "pass":
        game = session.query(Game).filter(Game.group_tele_id == group_tele_id).first()
        game.count_pass = 0
        session.commit()
        job_context = "%d,%d,%d" % (group_tele_id, player_tele_id, message_id)
        job_queue.run_once(pass_round, 0, context=job_context)
    elif data == "sortSuit":
        player_message(bot, group_tele_id, job_queue, is_sort_suit=True, is_edit=True, message_id=message_id)
    elif data == "sortNum":
        player_message(bot, group_tele_id, job_queue, is_edit=True, message_id=message_id)


# Changes the default language of a player/group
def change_lang(bot, tele_id, message_id, data):
    new_language = data.split(",")[1]
    language = session.query(Language).filter(Language.tele_id == tele_id).first()

    if language:
        language.language = new_language
    else:
        language = Language(tele_id=tele_id, language=language)
        session.add(language)

    session.commit()
    install_lang(tele_id)
    bot.editMessageText(text=_("Default language has been set"), chat_id=tele_id, message_id=message_id)


# Adds a selected card
def add_use_card(bot, group_tele_id, message_id, card_abbrev, job_queue):
    game, player = session.query(Game, Player). \
        filter(Game.group_tele_id == group_tele_id, Player.group_tele_id == group_tele_id,
               Player.player_id == Game.curr_player).first()

    curr_cards = pydealer.Stack(cards=game.curr_cards)
    player_cards = pydealer.Stack(cards=player.cards)
    curr_cards.add(player_cards.get(card_abbrev)[0])
    game.curr_cards, player.cards = curr_cards, player_cards
    session.commit()

    player_message(bot, group_tele_id, job_queue, is_edit=True, message_id=message_id)


# Uses the selected cards
def use_selected_cards(bot, player_tele_id, group_tele_id, message_id, job_queue):
    install_lang(player_tele_id)
    valid = True
    bigger = True

    game, player = session.query(Game, Player). \
        filter(Game.group_tele_id == group_tele_id, Player.group_tele_id == group_tele_id,
               Player.player_id == Game.curr_player).first()
    game_round, curr_player, biggest_player, curr_cards, prev_cards = \
        game.game_round, game.curr_player, game.biggest_player, game.curr_cards, game.prev_cards
    player_name, num_cards = player.player_name, player.num_cards

    if curr_cards.size == 0:
        return

    if get_cards_type(curr_cards) == -1 or (game_round == 1 and not curr_cards.find("3D")) or \
            (curr_player != biggest_player and prev_cards.size != 0 and prev_cards.size != curr_cards.size):
        valid = False

    if valid and curr_player != biggest_player and not are_cards_bigger(prev_cards, curr_cards):
        bigger = False

    if not valid:
        message = _("Invalid cards. Please try again\n")
        return_cards_to_deck(group_tele_id)
    elif not bigger:
        message = _("You cards are not bigger than the previous cards. ")
        message += _("Please try again\n")
        return_cards_to_deck(group_tele_id)
    else:
        message = _("These cards have been used:\n")
        for card in curr_cards:
            message += suit_unicode(card.suit)
            message += " "
            message += str(card.value)
            message += "\n"
        bot.editMessageText(message, player_tele_id, message_id)

        new_num_cards = num_cards - curr_cards.size
        if new_num_cards == 0:
            finish_game(bot, group_tele_id, player_tele_id, curr_player, player_name, curr_cards)
            return

        game.curr_cards = pydealer.Stack()
        game.prev_cards = curr_cards
        player.num_cards = new_num_cards
        session.commit()
        advance_game(bot, group_tele_id, curr_player, player_name, curr_cards)

    if valid and bigger:
        player_message(bot, group_tele_id, job_queue)
    else:
        player_message(bot, group_tele_id, job_queue, is_edit=True, message_id=message_id)
        bot.send_message(player_tele_id, message)


# Retruns curr_cards to the player's deck
def return_cards_to_deck(group_tele_id):
    game, player = session.query(Game, Player). \
        filter(Game.group_tele_id == group_tele_id, Player.group_tele_id == group_tele_id,
               Player.player_id == Game.curr_player).first()

    curr_cards = game.curr_cards
    player_cards = pydealer.Stack(cards=player.cards)
    player_cards.add(curr_cards)
    game.curr_cards = pydealer.Stack()
    player.cards = player_cards
    session.commit()


# Advances the game
def advance_game(bot, group_tele_id, curr_player, player_name, curr_cards):
    game = session.query(Game).filter(Game.group_tele_id == group_tele_id).first()
    game.game_round += 1
    game.curr_player = (curr_player + 1) % 4
    game.biggest_player = curr_player
    session.commit()

    game_message(bot, group_tele_id)

    if curr_cards.size == 1 and curr_cards.find("2S"):
        game.curr_player = curr_player
        game.biggest_player = curr_player
        session.commit()

        message = (_("I have passed all players since %s has used ♠ 2\n") % player_name)
        message += "--------------------------------------\n"
        message += _("%s's Turn\n") % player_name

        bot.send_message(group_tele_id, message, disable_notification=True)


# Game over
def finish_game(bot, group_tele_id, player_tele_id, curr_player, player_name, curr_cards):
    bot.send_message(player_tele_id, _("You won!"))

    players = session.query(Player).filter(Player.group_tele_id == group_tele_id, Player.player_id != curr_player)
    for player in players:
        install_lang(player.player_tele_id)
        bot.send_message(player.player_tele_id, _("You lost!"))

    install_lang(group_tele_id)
    message = _("These cards have been used:\n")
    for card in curr_cards.cards:
        message += suit_unicode(card.suit)
        message += " "
        message += str(card.value)
        message += "\n"
    message += "--------------------------------------\n"
    message += _("%s won!") % player_name

    bot.send_message(group_tele_id, message, disable_notification=True)

    update_stats(group_tele_id, curr_player)
    delete_game_data(group_tele_id)


# Updates group and player stats
def update_stats(group_tele_id, won_player):
    money_mode = session.query(GroupSetting.money_mode).filter(GroupSetting.tele_id == group_tele_id).first()
    players = session.query(Player).filter(Player.group_tele_id == group_tele_id).all()
    group_stat = session.query(GroupStat).filter(GroupStat.tele_id == group_tele_id).first()
    num_cards_left = sum([player.cards.size for player in players])
    money_earned = 0

    if group_stat:
        group_stat.num_games += 1
    else:
        group_stat = GroupStat(tele_id=group_tele_id, num_games=1, best_win_rate=0, most_money_earned=0)
        session.add(group_stat)

    for player in players:
        player_stat = session.query(PlayerStat).filter(PlayerStat.tele_id == player.player_tele_id).first()

        if player_stat:
            player_stat.num_games += 1
            player_stat.num_cards += 13 - player.cards.size
            player_stat.num_games_won += 1 if player.player_id == won_player else 0
            player_stat.win_rate = player_stat.num_games_won / player_stat.num_games
        else:
            player_stat = PlayerStat(tele_id=player.player_tele_id, player_name=player.player_name, num_games=1,
                                     num_cards=13 - player.cards.size, money=init_money, money_earned=0)
            player_stat.num_games_won = 1 if player.player_id == won_player else 0
            player_stat.win_rate = player_stat.num_games_won / player_stat.num_games
            session.add(player_stat)

        if money_mode and player.player_id != won_player:
            money_lost = get_money_lost(player.cards, card_money, num_cards_left)
            player_stat.money -= money_lost
            player_stat.money_earned -= money_lost
            money_earned += money_lost

        if player_stat.win_rate > group_stat.best_win_rate:
            group_stat.best_win_rate = player_stat.win_rate
            group_stat.best_win_rate_player = player.player_name

        if player_stat.money_earned > group_stat.most_money_earned:
            group_stat.most_money_earned = player_stat.money_earned
            group_stat.most_money_earned_player = player.player_name

    if money_mode:
        player_stat = session.query(PlayerStat).\
            filter(PlayerStat.tele_id == Player.player_tele_id, Player.group_tele_id == group_tele_id,
                   Player.player_id == won_player).first()
        player_stat.money += money_earned
        player_stat.money_earned += money_earned

    session.commit()


# Passes player's turn
def pass_round(bot, job):
    group_tele_id, player_tele_id, message_id = map(int, job.context.split(","))
    install_lang(player_tele_id)
    game = session.query(Game).filter(Game.group_tele_id == group_tele_id).first()

    try:
        bot.editMessageText(text=_("You Passed"), chat_id=player_tele_id, message_id=message_id)
    except:
        return

    if game.count_pass + 1 > 4:
        stop_idle_game(bot, group_tele_id)
        return

    return_cards_to_deck(group_tele_id)

    game.game_round += 1
    game.curr_player = (game.curr_player + 1) % 4
    game.count_pass += 1

    if game.game_round > 1 and game.curr_player == game.biggest_player:
        game.prev_cards = pydealer.Stack()
    session.commit()

    game_message(bot, group_tele_id)
    player_message(bot, group_tele_id, job.job_queue)


# Stops an idle game
def stop_idle_game(bot, group_tele_id):
    install_lang(group_tele_id)
    message = _("Game has been stopped by me since no one is playing")
    bot.send_message(group_tele_id, message)

    delete_game_data(group_tele_id)


# Installs the language
def install_lang(tele_id):
    language = session.query(Language).filter(Language.tele_id == tele_id).first()
    if language:
        es = gettext.translation("big_two_text", localedir="locale", languages=[language.language])
    else:
        language = Language(tele_id=tele_id, language="en")
        session.add(language)
        session.commit()
        es = gettext.translation("big_two_text", localedir="locale", languages=["en"])
    es.install()


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
        num_users = session.query(Language).filter(Language.tele_id > 0).count()
        num_groups = session.query(Language).filter(Language.tele_id < 0).count()
        num_games = session.query(Game).count()

        text = "Number of users: %d\nNumber of groups: %d\nNumber of games: %d" % (num_users, num_groups, num_games)
        bot.send_message(dev_tele_id, text)


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"' % (update, error))


if __name__ == '__main__':
    main()

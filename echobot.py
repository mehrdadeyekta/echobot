#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import telegram
from telegram.error import NetworkError, Unauthorized
from time import sleep
import psycopg2 as db
import sys
import random
import configparser
import static_messages


update_id = None

config = configparser.RawConfigParser()
configFilePath = 'config.txt'
config.read(configFilePath)

DB_HOST = '127.0.0.1'
DB_DATABASE = config.get("CONFIG", "DB_DATABASE")
DB_USERNAME = config.get("CONFIG", "DB_USERNAME")
DB_PASSWORD = config.get("CONFIG", "DB_PASSWORD")
BOT_TOKEN = config.get("CONFIG", "BOT_TOKEN")
ADMIN_USER_ID = config.get("CONFIG", "ADMIN_USER_ID")

conn = db.connect(host=DB_HOST, database=DB_DATABASE, user=DB_USERNAME, password=DB_PASSWORD)
cursor = conn.cursor()

WELCOME_MSG_PART_1 = static_messages.MESSAGE["WELCOME_MSG_PART_1"]
WELCOME_MSG_PART_2 = static_messages.MESSAGE["WELCOME_MSG_PART_2"]
HELP_MSG = static_messages.MESSAGE["HELP_MSG"]
CHANGE_ID_MSG = static_messages.MESSAGE["CHANGE_ID_MSG"]
NEW_TYPE_1_MSG = static_messages.MESSAGE["NEW_TYPE_1_MSG"]
NEW_TYPE_2_MSG_PART_1 = static_messages.MESSAGE["NEW_TYPE_2_MSG_PART_1"]
NEW_TYPE_2_MSG_PART_2 = static_messages.MESSAGE["NEW_TYPE_2_MSG_PART_2"]
AFTER_GETTING_TARGET_ANON_ID_MSG = static_messages.MESSAGE["AFTER_GETTING_TARGET_ANON_ID_MSG"]
UNAVAILABLE_TARGET_ANON_ID_MSG = static_messages.MESSAGE["UNAVAILABLE_TARGET_ANON_ID_MSG"]
TARGET_IS_NOT_SELECTED_MSG = static_messages.MESSAGE["TARGET_IS_NOT_SELECTED_MSG"]

def handle_msg(bot):
    """Echo the message the user sent."""
    global update_id
    # Request updates after the last update_id
    for update in bot.get_updates(offset=update_id, timeout=10):

        update_id = update.update_id + 1

        if update.message:  # your bot can receive updates without messages
            cursor.execute("select  user_id from users where user_id='" + str(update.message.from_user['id']) + "';")
            if cursor.rowcount == 0:
                rand_id = 0
                while True:
                    rand_id = str(random.randint(1000,9999))
                    cursor.execute("select  * from users where user_anon_id='" + rand_id + "';")
                    if cursor.rowcount == 0:
                        break
                fname = str(update.message.from_user['first_name'].encode("utf-8")) if update.message.from_user['first_name'] else 'None'
                lname = str(update.message.from_user['last_name'].encode("utf-8")) if update.message.from_user['last_name'] else 'None'
                username = str(update.message.from_user['username'])
                user_id =  str(update.message.from_user['id'])
                cursor.execute("insert into users (username, user_id, first_name, last_name, user_anon_id) values (" +\
                                                                                             "'" + username + "', " +\
                                                                                             "'" + user_id + "', " +\
                                                                                             "'" + fname + "', " +\
                                                                                             "'" + lname + "', " +\
                                                                                             "'" + rand_id + "');")
                cursor.execute("commit;")
                update.message.reply_text(WELCOME_MSG_PART_1 + rand_id + WELCOME_MSG_PART_2)
                bot.forwardMessage(ADMIN_USER_ID,update.message.chat.id, update.message.message_id)
            else:
                pass

            # Reply to the message
            if update.message.text:
                text = str(update.message.text.encode("utf-8"))
                if text == "/help":
                    update.message.reply_text(HELP_MSG)

                elif text == "/change_id":
                    while True:
                        rand_id = str(random.randint(1000,9999))
                        cursor.execute("select  * from users where user_anon_id='" + rand_id + "';")
                        if cursor.rowcount == 0:
                            cursor.execute("update users set user_anon_id='" + rand_id + "' where user_id='" + str(update.message.from_user['id']) + "';")
                            cursor.execute("commit;")
                            update.message.reply_text(CHANGE_ID_MSG + rand_id)
                            break

                elif text == "/get_id":
                    cursor.execute("select user_anon_id from users where user_id='" + str(update.message.from_user['id']) + "';")
                    update.message.reply_text(cursor.fetchall()[0][0])

                elif text == "/new":
                    cursor.execute("select last_chat from users where user_id='" + str(update.message.from_user['id']) + "';")
                    current_target = cursor.fetchall()[0][0]
                    if current_target == None:
                        update.message.reply_text(NEW_TYPE_1_MSG)
                    else:
                        update.message.reply_text(NEW_TYPE_2_MSG_PART_1 + str(current_target) + NEW_TYPE_2_MSG_PART_2)

                elif text.replace("/","").isdigit() and len(text.replace("/","")) == 4:
                    cursor.execute("update users set last_chat='" + text.replace("/","") + "' where user_id='" + str(update.message.from_user['id']) + "';")
                    cursor.execute("commit;")
                    update.message.reply_text(AFTER_GETTING_TARGET_ANON_ID_MSG)
                else:
                    cursor.execute("select user_anon_id from users where user_id='" + str(update.message.from_user['id']) + "';")
                    uid = cursor.fetchall()[0][0]
                    cursor.execute("select last_chat from users where user_id='" + str(update.message.from_user['id']) + "';")
                    target = cursor.fetchall()[0][0]
                    if target:
                        cursor.execute("select user_id from users where user_anon_id='" + str(target) + "';")
                        if cursor.rowcount == 0:
                            update.message.reply_text(UNAVAILABLE_TARGET_ANON_ID_MSG)
                        else:
                            target_id = cursor.fetchall()[0][0]
                            msg = "From /" + str(uid) + ":\n\n" + str(text)
                            bot.sendMessage(target_id, msg)
                            bot.sendMessage(ADMIN_USER_ID, str(update.message.from_user['id']) + "==>" + str(target_id) + " :: " + str(text))
                    else:
                        update.message.reply_text(TARGET_IS_NOT_SELECTED_MSG)


def main():
    """Run the bot."""
    global update_id

    # Telegram Bot Authorization Token
    bot = telegram.Bot(BOT_TOKEN)

    # get the first pending update_id, this is so we can skip over it in case
    # we get an "Unauthorized" exception.
    try:
        update_id = bot.get_updates()[0].update_id
    except IndexError:
        update_id = None

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    while True:
        try:
            handle_msg(bot)
        except NetworkError:
            sleep(1)
        except Unauthorized:
            # The user has removed or blocked the bot.
            update_id += 1


if __name__ == '__main__':
    main()

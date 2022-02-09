from __future__ import annotations

import json
import os

import apiclient
import django.db.models
import googleapiclient
import httplib2
import requests
from django.http import JsonResponse
from django.views import View
from oauth2client.service_account import ServiceAccountCredentials
from telegram import ReplyKeyboardMarkup, KeyboardButton

from .models import *
import telegram
from ke.settings.base import *
from datetime import date



from aiogram import Bot
from aiogram.dispatcher import Dispatcher
import os
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from enum import Enum, auto
from abc import ABC, abstractmethod

TELEGRAM_URL = "https://api.telegram.org/bot"
bot = telegram.Bot(token=BOT_TOKEN)


class GoogleSheetApi(object):
    service = None
    sheet_id = None
    def __init__(self, sheet_id):
        self.sheet_id = sheet_id

        CREDENTIALS_FILE = 'bot/creds.json'
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            CREDENTIALS_FILE,
            ['https://www.googleapis.com/auth/spreadsheets',
             'https://www.googleapis.com/auth/drive'])
        httpAuth = credentials.authorize(httplib2.Http())
        self.service = apiclient.discovery.build('sheets', 'v4', http=httpAuth)

    def create(self, title):
        service = self.service
        # [START sheets_create]
        spreadsheet = {
            'properties': {
                'title': title
            }
        }
        spreadsheet = service.spreadsheets().create(body=spreadsheet,
                                                    fields='spreadsheetId').execute()
        print('Spreadsheet ID: {0}'.format(spreadsheet.get('spreadsheetId')))
        # [END sheets_create]
        return spreadsheet.get('spreadsheetId')

    def batch_update(self, spreadsheet_id, title, find, replacement):
        service = self.service
        # [START sheets_batch_update]
        requests = []
        # Change the spreadsheet's title.
        requests.append({
            'updateSpreadsheetProperties': {
                'properties': {
                    'title': title
                },
                'fields': 'title'
            }
        })
        # Find and replace text
        requests.append({
            'findReplace': {
                'find': find,
                'replacement': replacement,
                'allSheets': True
            }
        })
        # Add additional requests (operations) ...

        body = {
            'requests': requests
        }
        response = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body).execute()
        find_replace_response = response.get('replies')[1].get('findReplace')
        print('{0} replacements made.'.format(
            find_replace_response.get('occurrencesChanged')))
        # [END sheets_batch_update]
        return response

    def get_values(self, range_name):
        service = self.service
        # [START sheets_get_values]
        result = service.spreadsheets().values().get(
            spreadsheetId=self.sheet_id, range=range_name).execute()
        rows = result.get('values', [])
        print('{0} rows retrieved.'.format(len(rows)))
        # [END sheets_get_values]
        return result

    def update_values(self, range_name, value_input_option,
                      _values):
        service = self.service
        # [START sheets_update_values]

        values = _values
        # [END_EXCLUDE]
        body = {
            'values': values
        }
        result = service.spreadsheets().values().update(
            spreadsheetId=self.sheet_id, range=range_name,
            valueInputOption=value_input_option, body=body).execute()
        print('{0} cells updated.'.format(result.get('updatedCells')))
        # [END sheets_update_values]
        return result

    def append_list(self, li, cell_range):
        resource = {
            "majorDimension": "ROWS",
            "values": [li]
        }

        self.service.spreadsheets().values().append(
            spreadsheetId=self.sheet_id,
            range=cell_range,
            body=resource,
            valueInputOption="USER_ENTERED"
        ).execute()


class State(ABC):

    @property
    def context(self) -> BotContext:
        return self._bot_context

    @context.setter
    def context(self, context: BotContext) -> None:
        self._bot_context = context

    @abstractmethod
    def step(self, msg) -> None:
        pass

    @abstractmethod
    def show_markup(self, msg) -> None:
        pass


class BotContext:

    _state = None
    shop = None
    item_type = None
    value = None
    comment = None

    income_types = [
        'Доход. Выручка с КЕ'
    ]
    expense_types = [
        'Расход. ЦПТ',
        'Расход. Закуп товара Китай',
        'Расход. Вывод средств себе',
        'Расход. Налоги',
        'Расход. Взносы',
        'Расход. Поклейка Аня',
        'Расход. Помощник',
        'Расход. Поклейка Бабуля',
        'Расход. Доставка Китай',
        'Расход. Оплата ТК',
        'Расход. Доставка Казань Челны',
        'Расход. ГСМ',
    ]
    item_types = None
    # msg_text = None


    def __init__(self, state: State) -> None:
        self.transition_to(state)

    def transition_to(self, state: State):

        print(f"Context: Transition to {type(state).__name__}")
        self._state = state
        self._state.context = self

    # def save_income(self):

    def step(self, msg):
        # self.msg_text = msg['text']
        if msg['text'] == 'Отмена':
            self.transition_to(Menu())
        self._state.step(msg)

    def show_markup(self, msg):
        self._state.show_markup(msg)


class GoogleSheetSettings(State):
    def step(self, msg) -> None:
        google_sheet_id = msg['text']
        google_api = GoogleSheetApi(google_sheet_id)

        try:
            res = google_api.get_values("A1:A2")
            print(res)
        except googleapiclient.errors.HttpError:
            bot.send_message(msg['chat']['id'], 'Что-то пошло не так, не могу прочитать данные с таблицы')
            return

        try:
            values = res['values']
            res = google_api.update_values("A1:A2", 'RAW', values)
        except googleapiclient.errors.HttpError:
            bot.send_message(msg['chat']['id'], 'Что-то пошло не так, не могу вписать данные в таблицу')
            return

        user_chat = UserChat.objects.filter(chat_id=msg['chat']['id']).first()
        if user_chat is None:
            user_chat = UserChat()
        user_chat.google_sheet = msg['text']
        user_chat.chat_id = msg['chat']['id']
        user_chat.save()

        bot.send_message(msg['chat']['id'], 'Поздравляю! Мы все настроили')
        self.context.transition_to(Menu())

    def show_markup(self, msg) -> None:
        keyboard = [[KeyboardButton('Отмена')]]
        reply_markup = ReplyKeyboardMarkup(keyboard)
        bot.send_message(msg['chat']['id'], 'ke-analytics@ke-analytics-339914.iam.gserviceaccount.com')
        bot.send_message(msg['chat']['id'],
                         '1) Предоставь на этот email права редактора таблицы, в которую хочешь записывать данные\n'
                         '2) После этого отправь id этой таблицы (id можно взять из ссылки на таблицу)', reply_markup=reply_markup)


class Start(State):
    def step(self, msg) -> None:
        print("Start")
        if msg['text'] == '/start':
            self.context.transition_to(Menu())
        else:
            bot.send_message(msg['chat']['id'], 'Напиши команду /start для начала работы')

    def show_markup(self, msg) -> None:
        pass


class ShopsSettings(State):
    actions = ['Отмена']

    def step(self, msg) -> None:

        name = msg['text']
        user_chat = UserChat.objects.filter(chat_id=msg['chat']['id']).first()
        shop = Shop(user_chat=user_chat, name=name)
        shop.save()
        bot.send_message(msg['chat']['id'], f'Магазин "{name}" добавлен')
        self.context.transition_to(Menu())


    def show_markup(self, msg) -> None:
        keyboard = [[KeyboardButton(action) for action in self.actions]]
        reply_markup = ReplyKeyboardMarkup(keyboard)
        bot.send_message(msg['chat']['id'], 'Введи название магазина', reply_markup=reply_markup)


class Menu(State):

    def step(self, msg) -> None:
        db = DBapi(msg['chat']['id'])
        user_chat = db.get_user_chat()
        if user_chat is None or user_chat.google_sheet is None:
            bot.send_message(msg['chat']['id'],
                             'Друг, похоже ты тут новенький!\n'
                             'Прежде чем начнем работать, нужно кое-что настпроить')
            self.context.transition_to(GoogleSheetSettings())
            return

        shops = db.get_shops_name_list()
        print('SHOPS', shops)
        if len(shops) == 0:
            self.context.transition_to(ShopsSettings())
            return


        if msg['text'] == 'Доходы':
            self.context.item_types = self.context.income_types
            self.context.transition_to(ItemTypeChoosing())
        elif msg['text'] == 'Расходы':
            self.context.item_types = self.context.expense_types
            self.context.transition_to(ItemTypeChoosing())
        elif msg['text'] == 'Настройки':
            self.context.transition_to(Settings())

    def show_markup(self, msg) -> None:
        keyboard = [
            [
                KeyboardButton("Расходы"),
                KeyboardButton("Доходы"),
            ],
            [KeyboardButton("Настройки")],
        ]

        reply_markup = ReplyKeyboardMarkup(keyboard)
        bot.send_message(msg['chat']['id'], 'Выбери пункт из меню', reply_markup=reply_markup)


class Settings(State):
    actions = ['Поменять google таблицу', 'Добавить магазин', 'Отмена']

    def step(self, msg) -> None:
        if msg['text'] == 'Поменять google таблицу':
            self.context.transition_to(GoogleSheetSettings())
            return
        if msg['text'] == 'Добавить магазин':
            self.context.transition_to(ShopsSettings())
            return
        self.context.transition_to(Menu())

    def show_markup(self, msg) -> None:
        keyboard = [[KeyboardButton(action) for action in self.actions]]
        reply_markup = ReplyKeyboardMarkup(keyboard)
        bot.send_message(msg['chat']['id'], 'Введи сумму дохода', reply_markup=reply_markup)


class DBapi:
    chat_id = None

    def __init__(self, chat_id):
        self.chat_id = chat_id

    def get_user_chat(self):
        return UserChat.objects.filter(chat_id=self.chat_id).first()

    def get_shops(self) -> django.db.models.QuerySet:
        return Shop.objects.filter(user_chat=self.get_user_chat()).all()

    def get_shops_name_list(self) -> list:
        shops_query = Shop.objects.filter(user_chat=self.get_user_chat()).all()
        shops_names_list = [shop.name for shop in shops_query]
        return shops_names_list

    def get_sheet_id(self):
        user_chat = self.get_user_chat()
        sheet_id = user_chat.google_sheet
        return sheet_id


class ShopChoosing(State):
    def step(self, msg) -> None:
        db = DBapi(msg['chat']['id'])
        shops = db.get_shops_name_list()
        if msg['text'] not in shops:
            bot.send_message(msg['chat']['id'], 'Похоже, название магазина неправильное\n'
                                                'Выбери магазин из списка меню')
            return
        self.context.shop = msg['text']
        self.context.transition_to(NumberInput())

    def show_markup(self, msg) -> None:
        db = DBapi(msg['chat']['id'])
        actions = db.get_shops_name_list()
        keyboard = [[KeyboardButton(action) for action in actions]]
        reply_markup = ReplyKeyboardMarkup(keyboard)
        bot.send_message(msg['chat']['id'], 'В какой магазин вписать данные?', reply_markup=reply_markup)


class ItemTypeChoosing(State):


    def step(self, msg) -> None:
        self.context.item_type = msg['text']
        print("income choosing")
        db = DBapi(msg['chat']['id'])
        if len(db.get_shops()) > 1:
            self.context.transition_to(ShopChoosing())
            return

        self.context.shop = db.get_shops_name_list()[0]
        self.context.transition_to(NumberInput())

    def show_markup(self, msg) -> None:
        actions = self.context.item_types.copy()
        actions.append('Отмена')
        keyboard = [[KeyboardButton(action)] for action in actions]
        reply_markup = ReplyKeyboardMarkup(keyboard)
        bot.send_message(msg['chat']['id'], 'Какой доход хочешь добавить?', reply_markup=reply_markup)


class CommentInput(State):
    def step(self, msg) -> None:

        if msg['text'] == 'Пропустить':
            self.context.comment = ''
        else:
            self.context.comment = msg['text']

        db = DBapi(msg['chat']['id'])
        google_sheet_id = db.get_sheet_id()
        google_api = GoogleSheetApi(google_sheet_id)

        today = date.today()
        today_str = today.strftime("%d.%m.%Y")

        li = [
            today_str,
            self.context.shop,
            self.context.item_type,
            self.context.value,
            self.context.comment
        ]

        google_api.append_list(li, "A:E")

        self.context.transition_to(Menu())
        bot.send_message(msg['chat']['id'], 'Ок, все готово!')

    def show_markup(self, msg) -> None:
        keyboard = [[KeyboardButton('Пропустить'), KeyboardButton('Отмена')]]
        reply_markup = ReplyKeyboardMarkup(keyboard)
        bot.send_message(msg['chat']['id'], 'Введи комментарий', reply_markup=reply_markup)


class NumberInput(State):
    def step(self, msg) -> None:
        income_str = msg['text'].replace(',', '.')

        try:
            income = float(income_str)
        except ValueError:
            answer_text = "Похоже, что-то не так с числом. Попробуй еще раз"
            bot.send_message(msg['chat']['id'], answer_text)
            return

        self.context.value = income
        self.context.transition_to(CommentInput())

    def show_markup(self, msg) -> None:
        keyboard = [[KeyboardButton('Отмена')]]
        reply_markup = ReplyKeyboardMarkup(keyboard)
        bot.send_message(msg['chat']['id'], 'Введи сумму дохода', reply_markup=reply_markup)


class ExpenseChoosing(State):
    def step(self, msg) -> None:
        print("expense choosing")
        self.context.transition_to(Menu())

    def show_markup(self, msg) -> None:
        KeyboardButton("Расход", callback_data="expense")



# https://api.telegram.org/bot<token>/setWebhook?url=<url>/webhooks/tutorial/
context = BotContext(Start())

class TutorialBotView(View):
    state = None
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        try:
            message = data["message"]
        except KeyError:
            print(data)
            return JsonResponse({"ok": "POST request processed"})
        chat = message["chat"]

        context.step(message)
        context.show_markup(message)

        # chat = ChatCounter.objects.filter(chat_id=t_chat["id"]).first()
        # print('CHAT', t_chat["id"])
        # if not chat:
        #     chat = ChatCounter(
        #         chat_id=t_chat["id"],
        #         counter=0
        #     )
        #     chat.save()
        #
        #
        # if text == "+":
        #     print('+++')
        #     chat.counter += 1
        #     chat.save()
        #     msg = f"Number of '+' messages that were parsed: {chat.counter}"
        #     bot.send_message(t_chat["id"], msg)
        # elif text == "restart":
        #     # blank_data = {"counter": 0}
        #     # chat.update(blank_data)
        #     chat.counter = 0
        #     chat.save()
        #     msg = "The Tutorial bot was restarted"
        #     bot.send_message(t_chat["id"], msg)
        # else:
        #     msg = "Unknown command"
        #     bot.send_message(t_chat["id"], msg)
        #
        return JsonResponse({"ok": "POST request processed"})

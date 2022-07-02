import logging
import os
from decimal import Decimal
from typing import Tuple, Dict, List

import datetime
import json
import requests

from django.conf import settings
from django.core import serializers

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from test_app.models import Orders
from test_app.utils import is_date, get_set

main_logger = logging.getLogger('main')
data_logger = logging.getLogger('data_logger')


def get_credential(path_creds_file: str):
    """
    Get the access to Shhets API
    """
    creds = None
    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    token_path = os.path.join(str(settings.BASE_DIR), 'creds', 'token.json')
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                path_creds_file, scopes)
            flow.redirect_uri = 'https://docs.google.com/spreadsheets/'
            creds = flow.run_local_server(host='127.0.0.1', port=5000)
        # Save the credentials for the next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('sheets', 'v4', credentials=creds)
        return service
    except HttpError as err:
        main_logger.error('Failed connect to googlesheets', exc_info=err)


def send_telegram(text: str, token, channel_id) -> None:
    """
    Function for sending the messages to telegram. Need to specify BOT_TOKEN and CHANNEL_ID in settings.py
    See more in ReadMe.md
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    response = requests.post(url, data={
         "chat_id": channel_id,
         "text": text
          })
    if response.status_code != 200:
        main_logger.error('Failed connect to telegrambot')


class GoogleSheetConnect:
    """
    Create connection wth google sheets api and get datat from sheets and list, specifying in django admin options
    """
    def __init__(self, cred_json: str, sheet_id: str, sheet_list: str, cur_value: Decimal) -> None:
        self.credential = get_credential(cred_json)
        self.currency = cur_value
        self.sheet_id = sheet_id
        self.sheet_list = sheet_list

    def pull_sheet_data(self) -> List:
        """
        Method for getting data from googlesheet
        :return: List[List]
        """
        sheet = self.credential.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=self.sheet_id,
            range=self.sheet_list).execute()
        values = result.get('values', [])
        if not values:
            main_logger.debug('sheet is empty')
            raise
        return values[1:]

    def get_sheet_data(self) -> Dict:
        """
        Method for processing data from Google. In particular, the data is sorted into valid and invalid, the currency is calculated for valid data.
        :return: Dict[List[List]]
        """
        sheet_dict = {
            'clean_data': [],
            'invalid_exist_data': [],
        }
        unique = []
        data_logger.debug(f'--------start_task----------')
        for item in self.pull_sheet_data():
            if len(item) > 3:
                try:
                    pk = int(item[0])
                    if pk not in unique:
                        unique.append(pk)
                        if item[2].isdigit() and is_date(item[3]):
                            item[3] = datetime.datetime.strptime(item[3], "%d.%m.%Y").strftime("%Y-%m-%d")
                            try:
                                item.append(round(Decimal(item[2]) * self.currency, 2))
                            except TypeError:
                                main_logger.error(
                                    'Error currency value. Possible problem when connecting to https://www.cbr.ru')
                                item.append(0)
                            sheet_dict['clean_data'].append(item)
                        else:
                            if Orders.objects.filter(id=pk).exists():
                                sheet_dict['invalid_exist_data'].append(item)
                                data_logger.debug(
                                    f'Error updating data in sheets: #: {item[0]}, order {item[1]}, '
                                    f'price: {item[2]}, date: {item[3]}.'
                                    f'this order will not updating.')
                            else:
                                data_logger.debug(
                                    f'Wrong data in sheets: #: {item[0]}, order {item[1]}, '
                                    f'price: {item[2]}, date: {item[3]}')
                    else:
                        sheet_dict['invalid_exist_data'].append(item)
                        data_logger.debug(
                            f'The order with id {item[0]} is already exist! It will not to rewrite. '
                            f'Data: order {item[1]}, price: {item[2]}, date: {item[3]}')
                except ValueError:
                    data_logger.debug(f'Wrong id data in sheets: #: {item[0]}, order {item[1]}, '
                                      f'price: {item[2]}, date: {item[3]}')
            else:
                data_logger.debug(f'Wrong data in sheets: {item}')
        data_logger.debug(f'--------end_task----------')
        return sheet_dict

    @classmethod
    def get_data_db(cls) -> Tuple:
        """
        Get the data form Database in tuple-format
        :return: Tuple[List]
        """
        data_db = json.loads(serializers.serialize('json', Orders.objects.all()))
        res = tuple(list(item['fields'].values()) for item in data_db)
        for item in zip(res, data_db):
            item[0].insert(0, item[1]['pk'])
        return res

    @classmethod
    def get_changed_data(cls, data_sheet: Dict, data_db: Tuple) -> List:
        """
        Retrieving changed data from a table relative to a database. Proccessing data only cleaned_data from googlesheets
        :return: List[Dict]
        """
        changed_data = []
        set_sheet = get_set(data_sheet['clean_data'], depth_end=5)
        set_db = get_set(data_db, depth_end=5)
        changes = set.difference(set_sheet, set_db)
        if changes:
            fields = ['pk', 'order', 'price', 'delivery_date', 'rub_price']
            values = [item.split('~') for item in changes]
            for value in values:
                changed_data.append(dict(zip(fields, value)))
        return changed_data

    @classmethod
    def get_deletion_orders(cls, data_sheet: Dict, data_db: Tuple) -> Tuple:
        """
        Get the tuple with id for deletion from Database
        "return: Tuple
        """
        set_sheet = set(int(item[0]) for item in data_sheet['clean_data'])
        set_db = set(int(item[0]) for item in data_db)
        set_exist = set([int(item[0]) for item in data_sheet['invalid_exist_data']])
        deletion_orders = set.difference(set.difference(set_db, set_sheet), set_exist)
        return tuple(deletion_orders)

    @classmethod
    def create_in_db(cls, data: List) -> None:
        """
        Create new instances in Database
        """
        Orders.objects.bulk_create(Orders(
            id=int(item['pk']),
            order=item['order'],
            price=Decimal(item['price']),
            delivery_date=datetime.datetime.strptime(item['delivery_date'], "%Y-%m-%d"),
            rub_price=Decimal(item['rub_price']))
                                   for item in data)

    @classmethod
    def update_db(cls, objs: Dict, data: List) -> None:
        """
        Update instances in Database
        """
        for item in zip(list(objs.values()), data):
            item[0].order = item[1]['order']
            item[0].price = int(item[1]['price'])
            item[0].delivery_date = item[1]['delivery_date']
            item[0].rub_price = Decimal(item[1]['rub_price'])
        Orders.objects.bulk_update(list(objs.values()), ['order', 'price', 'delivery_date', 'rub_price'])

    @classmethod
    def delete_from_db(cls, deletion_orders: Tuple[Dict]) -> None:
        """
        Delete instances from Database
        """
        Orders.objects.filter(order__in=deletion_orders).delete()

import logging
import os
from decimal import Decimal
from pprint import pprint
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

from creds.config import token, channel_id
from test_app.models import Orders
from test_app.utils import is_date, get_set

logger = logging.getLogger('logger')


def get_credential(path_creds_file: str):
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
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
        # add logger
        pass


def send_telegram(text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, data={
         "chat_id": channel_id,
         "text": text
          })
    try:
        if r.status_code != 200:
            raise ValueError
    except ValueError:
        # add logger
        raise


class GoogleSheetConnect:
    def __init__(self, cred_json: str, sheet_id: str, sheet_list: str, cur_value: Decimal) -> None:
        self.credential = get_credential(cred_json)
        self.currency = cur_value
        self.sheet_id = sheet_id
        self.sheet_list = sheet_list

    def pull_sheet_data(self) -> List:
        sheet = self.credential.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=self.sheet_id,
            range=self.sheet_list).execute()
        values = result.get('values', [])
        if not values:
            # add logger
            raise
        return values[1:]

    def get_sheet_data(self) -> Dict:
        sheet_dict = {
            'clean_data': [],
            'invalid_exist_data': [],
            'duplicates': []
        }
        invalid_not_exist_data = []
        invalid_data = []
        unique = []
        for item in self.pull_sheet_data():
            if len(item) > 3:
                try:
                    pk = int(item[0])
                    if pk not in unique:
                        unique.append(pk)
                        if item[2].isdigit() and is_date(item[3]):
                            item[3] = datetime.datetime.strptime(item[3], "%d.%m.%Y").strftime("%Y-%m-%d")
                            item.append(round(Decimal(item[2]) * self.currency, 2))
                            sheet_dict['clean_data'].append(item)
                        else:
                            if Orders.objects.filter(id=pk).exists():
                                sheet_dict['invalid_exist_data'].append(item)
                                # add logger (Сообщение о попытке обновления существующих данных неверными данными)
                            else:
                                # add logger (Сообщение о вводе неверных данных при попытке создания записи)
                                invalid_not_exist_data.append(item)

                    else:
                        sheet_dict['duplicates'].append(item)
                        # add logger (Сообщение о попытке создания дубликата)
                except ValueError:
                    # add logger (Сообщение о неверных данных при попытке создания записи)
                    invalid_data.append(item)
            else:
                # add logger (Сообщение о неверных данных при попытке создания записи)
                invalid_data.append(item)
        pprint(sheet_dict)
        return sheet_dict

    def get_data_db(self) -> Tuple:
        data_db = json.loads(serializers.serialize('json', Orders.objects.all()))
        res = tuple(list(item['fields'].values()) for item in data_db)
        for item in zip(res, data_db):
            item[0].insert(0, item[1]['pk'])
        return res

    def get_changed_data(self, data_sheet: Dict, data_db: Tuple) -> List:
        changed_data = []
        set_sheet = get_set(data_sheet['clean_data'], depth_end=5)
        print(sorted(set_sheet, key=lambda x: int(x[:x.index('~')])))
        set_db = get_set(data_db, depth_end=5)
        print(sorted(set_db, key=lambda x: int(x[:x.index('~')])))
        changes = set.difference(set_sheet, set_db)
        print(changes)
        if changes:
            fields = ['pk', 'order', 'price', 'delivery_date', 'rub_price']
            values = [item.split('~') for item in changes]
            for value in values:
                changed_data.append(dict(zip(fields, value)))
        return changed_data

    def get_deletion_orders(self, data_sheet: Dict, data_db: Tuple) -> Tuple:
        set_sheet = set(int(item[0]) for item in data_sheet['clean_data'])
        set_db = set(int(item[0]) for item in data_db)
        set_exist = set([int(item[0]) for item in data_sheet['duplicates']] +
                        [int(item[0]) for item in data_sheet['invalid_exist_data']])
        deletion_orders = set.difference(set.difference(set_db, set_sheet), set_exist)
        return tuple(deletion_orders)

    def create_in_db(self, data: List) -> None:
        Orders.objects.bulk_create(Orders(
            id=int(item['pk']),
            order=item['order'],
            price=Decimal(item['price']),
            delivery_date=datetime.datetime.strptime(item['delivery_date'], "%Y-%m-%d"),
            rub_price=Decimal(item['rub_price']))
                                   for item in data)

    def update_db(self, objs: Dict, data: List) -> None:
        for item in zip(list(objs.values()), data):
            item[0].order = item[1]['order']
            item[0].price = int(item[1]['price'])
            item[0].delivery_date = item[1]['delivery_date']
            item[0].rub_price = Decimal(item[1]['rub_price'])
        Orders.objects.bulk_update(list(objs.values()), ['order', 'price', 'delivery_date', 'rub_price'])

    def delete_from_db(self, deletion_orders: Tuple[Dict]) -> None:
        Orders.objects.filter(order__in=deletion_orders).delete()

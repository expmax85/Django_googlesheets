from decimal import Decimal
from typing import Tuple, Dict, List, Any

import datetime
import json
import httplib2
import requests

from django.core import serializers
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

from creds.config import token, channel_id
from test_app.models import Orders


def get_service_acc(creds_json: str) -> Any:

    scopes = ['https://www.googleapis.com/auth/spreadsheets']

    creds_service = ServiceAccountCredentials.from_json_keyfile_name(creds_json, scopes).authorize(httplib2.Http())
    return build('sheets', 'v4', http=creds_service)


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
        raise


class GoogleSheetConnect:
    def __init__(self, cred_json: str, sheet_id: str, sheet_list: str, cur_value: Decimal) -> None:
        self.account = get_service_acc(cred_json)
        self.currency = cur_value
        self.sheet_id = sheet_id
        self.sheet_list = sheet_list

    def pull_sheet_data(self) -> List:
        sheet = self.account.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=self.sheet_id,
            range=self.sheet_list).execute()
        values = result.get('values', [])
        if not values:
            raise
        return values[1:]

    def get_sheet_data(self) -> Tuple:
        sheet_data = tuple(item[1:] for item in self.pull_sheet_data())
        try:
            data_rub = tuple(round(Decimal(item[1]) * self.currency, 2) for item in sheet_data)
        except IndexError:
            raise
        for i in range(len(sheet_data)):
            sheet_data[i][2] = datetime.datetime.strptime(sheet_data[i][2], "%d.%m.%Y").strftime("%Y-%m-%d")
            sheet_data[i].append(data_rub[i])
        return sheet_data

    def get_data_db(self) -> Tuple:
        data_db = json.loads(serializers.serialize('json', Orders.objects.all()))
        return tuple(tuple(item['fields'].values()) for item in data_db)

    def get_changed_data(self, data_sheet: Tuple, data_db: Tuple) -> List:
        changed_data = []
        set_sheet = set(tuple('~'.join([str(item) for item in elem]) for elem in data_sheet))
        set_db = set(tuple('~'.join([str(value) for value in item]) for item in data_db))
        changes = set.difference(set_sheet, set_db)
        if changes:
            fields = ['order', 'price', 'delivery_date', 'rub_price']
            values = [item.split('~') for item in changes]
            for value in values:
                changed_data.append(dict(zip(fields, value)))
        return changed_data

    def get_deletion_orders(self, data_sheet: Tuple, data_db: Tuple) -> List:
        set_sheet = set(tuple(int(item[0]) for item in data_sheet))
        set_db = set(tuple(int(item[0]) for item in data_db))
        deletion_orders = set.difference(set_db, set_sheet)
        return list(deletion_orders)

    def create_in_db(self, data: List) -> None:
        Orders.objects.bulk_create(Orders(
            order=int(item['order']),
            price=Decimal(item['price']),
            delivery_date=datetime.datetime.strptime(item['delivery_date'], "%Y-%m-%d"),
            rub_price=Decimal(item['rub_price']))
                                   for item in data)

    def update_db(self, objs: Dict, data: List) -> None:
        for item in zip(list(objs.values()), data):
            item[0].price = item[1]['price']
            item[0].delivery_date = item[1]['delivery_date']
            item[0].rub_price = item[1]['rub_price']
        Orders.objects.bulk_update(list(objs.values()), ['price', 'delivery_date', 'rub_price'])

    def delete_from_db(self, deletion_orders: List) -> None:
        Orders.objects.filter(order__in=deletion_orders).delete()

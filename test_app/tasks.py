import datetime
from decimal import Decimal
from xml.etree import ElementTree

import requests
from celery.schedules import crontab

from django_sheets.celery import app
from test_app.models import Orders

CURRENCY = 'USD'
CURRENCY_VALUE = 0


class TimeoutException(Exception):
    pass


@app.on_after_configure.connect
def set_periodic(sender, **kwrags) -> None:
    """
    Функция запуска периодической задачи
    :param sender:
    :param kwrags:
    """
    sender.add_periodic_task(
        crontab(hour="23", minute='50'),
        send_message_to_tm.s()
    )

    # sender.add_periodic_task(
    #     crontab(hour="23", minute='55'),
    #     get_valute_currency.s(CURRENCY)
    # )

    sender.add_periodic_task(
        crontab(minute="*/1"),
        poll_update.s()
    )

    sender.add_periodic_task(
        30.0,
        send_ok.s()
    )


# @app.task
# def get_valute_currency(cur):
#
#     url = 'https://www.cbr.ru/scripts/XML_daily.asp'
#     response = requests.get(url, timeout=3)
#     if not response:
#         raise TimeoutException
#     tree = ElementTree.fromstring(response.content)
#     value = 0
#     global CURRENCY_VALUE
#     for elem in tree.iter('Valute'):
#         if elem.find('CharCode').text == cur:
#             value = Decimal(elem.find('Value').text.replace(',', '.'))
#             CURRENCY_VALUE = value
#     if not value:
#         raise


@app.task
def poll_update() -> None:
    from test_app.models import Orders
    from test_app.services import GoogleSheetConnect, CREDS_FILE, SHEET_ID, NAME_LIST
    GOOGLE_SHEETS = GoogleSheetConnect(cred_json=CREDS_FILE, sheet_id=SHEET_ID, sheet_list=NAME_LIST)
    data_sheet = GOOGLE_SHEETS.get_sheet_data()
    data_db = GOOGLE_SHEETS.get_data_db()
    deletion_orders = GOOGLE_SHEETS.get_deletion_orders(data_sheet, data_db)
    if deletion_orders:
        GOOGLE_SHEETS.delete_from_db(deletion_orders)
    changed_data = GOOGLE_SHEETS.get_changed_data(data_sheet, data_db)
    if changed_data:
        update_objs = Orders.objects.in_bulk([int(item['order']) for item in changed_data], field_name='order')
        if update_objs:
            update_data = [item for item in changed_data if int(item['order']) in set(update_objs.keys())]
            create_data = [item for item in changed_data if int(item['order']) not in set(update_objs.keys())]
            GOOGLE_SHEETS.update_db(update_objs, update_data)
            if create_data:
                GOOGLE_SHEETS.create_in_db(create_data)
        else:
            GOOGLE_SHEETS.create_in_db(changed_data)


@app.task
def send_message_to_tm():
    from bot import send_telegram
    today = datetime.date.today()
    delivered = Orders.objects.filter(delivery_date=today)
    for order in delivered:
        message = f'Order #{order.order} was delivered.'
        send_telegram(message)


@app.task
def send_ok():
    print('ok')

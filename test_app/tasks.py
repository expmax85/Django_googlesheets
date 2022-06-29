import datetime
import requests
from decimal import Decimal
from xml.etree import ElementTree

from django_sheets.celery import app
from test_app.models import Orders
from test_app.services import send_telegram


@app.task(name='get_valute_currency')
def get_valute_currency() -> Decimal:
    from dynamic_preferences.registries import global_preferences_registry

    currency = global_preferences_registry.manager().by_name()['currency']
    url = 'https://www.cbr.ru/scripts/XML_daily.asp'
    response = requests.get(url, timeout=3)
    if not response:
        raise
    tree = ElementTree.fromstring(response.content)
    value = 0
    for elem in tree.iter('Valute'):
        if elem.find('CharCode').text == currency:
            value = Decimal(elem.find('Value').text.replace(',', '.'))
            global_preferences_registry.manager().by_name()['cur_value'] = value
            return value
    if not value:
        raise


@app.task(name='poll_update')
def poll_update() -> None:
    from test_app.models import Orders
    from creds.config import CREDS_FILE, SHEET_ID, NAME_LIST
    from test_app.services import GoogleSheetConnect
    from dynamic_preferences.registries import global_preferences_registry

    cur_value = global_preferences_registry.manager().by_name()['cur_value']
    if not cur_value:
        cur_value = get_valute_currency()
    google_sheets = GoogleSheetConnect(cred_json=CREDS_FILE, sheet_id=SHEET_ID,
                                       sheet_list=NAME_LIST, cur_value=cur_value)
    data_sheet = google_sheets.get_sheet_data()
    data_db = google_sheets.get_data_db()
    deletion_orders = google_sheets.get_deletion_orders(data_sheet, data_db)
    if deletion_orders:
        google_sheets.delete_from_db(deletion_orders)
    changed_data = google_sheets.get_changed_data(data_sheet, data_db)
    if changed_data:
        update_objs = Orders.objects.in_bulk([int(item['order']) for item in changed_data], field_name='order')
        if update_objs:
            update_data = [item for item in changed_data if int(item['order']) in set(update_objs.keys())]
            create_data = [item for item in changed_data if int(item['order']) not in set(update_objs.keys())]
            google_sheets.update_db(update_objs, update_data)
            if create_data:
                google_sheets.create_in_db(create_data)
        else:
            google_sheets.create_in_db(changed_data)


@app.task(name='send_message_to_tm')
def send_message_to_tm() -> None:
    today = datetime.date.today()
    delivered = Orders.objects.filter(delivery_date=today)
    if delivered:
        for order in delivered:
            message = f'Order #{order.order} was delivered.'
            send_telegram(message)

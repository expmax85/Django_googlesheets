from decimal import Decimal

from django_sheets.celery import app


@app.task(name='get_valute_currency')
def get_valute_currency() -> Decimal:
    from dynamic_preferences.registries import global_preferences_registry
    from xml.etree import ElementTree
    from test_app.services import main_logger
    import requests

    currency = global_preferences_registry.manager().by_name()['currency']
    value = 0
    url = 'https://www.cbr.ru/scripts/XML_daily.asp'
    response = requests.get(url, timeout=3)
    if response.status_code != 200:
        main_logger.error('Failed to connect https://www.cbr.ru')
        return value
    tree = ElementTree.fromstring(response.content)
    for elem in tree.iter('Valute'):
        if elem.find('CharCode').text == currency:
            value = Decimal(elem.find('Value').text.replace(',', '.'))
            global_preferences_registry.manager().by_name()['cur_value'] = value
            return value
    else:
        main_logger.error('Uncorrect code valute corrency')
        return value


@app.task(name='poll_update')
def poll_update() -> None:
    import os
    from test_app.models import Orders
    from test_app.services import GoogleSheetConnect
    from dynamic_preferences.registries import global_preferences_registry
    from django.conf import settings

    creds_file = os.path.join(str(settings.BASE_DIR), "creds", "credentials.json")
    sheet_id = global_preferences_registry.manager().by_name()['sheet_id']
    sheet_list = global_preferences_registry.manager().by_name()['sheet_list']
    cur_value = global_preferences_registry.manager().by_name()['cur_value']
    if not cur_value:
        cur_value = get_valute_currency()
    google_sheets = GoogleSheetConnect(cred_json=creds_file, sheet_id=sheet_id,
                                       sheet_list=sheet_list, cur_value=cur_value)

    data_sheet = google_sheets.get_sheet_data()
    data_db = google_sheets.get_data_db()
    deletion_orders = google_sheets.get_deletion_orders(data_sheet, data_db)
    if deletion_orders:
        google_sheets.delete_from_db(deletion_orders)
    changed_data = google_sheets.get_changed_data(data_sheet, data_db)
    if changed_data:
        update_objs = Orders.objects.in_bulk([int(item['pk']) for item in changed_data], field_name='id')
        if update_objs:
            update_data = [item for item in changed_data if int(item['pk']) in set(update_objs.keys())]
            create_data = [item for item in changed_data if int(item['pk']) not in set(update_objs.keys())]
            google_sheets.update_db(update_objs, update_data)
            if create_data:
                google_sheets.create_in_db(create_data)
        else:
            google_sheets.create_in_db(changed_data)


@app.task(name='send_message_to_tm')
def send_message_to_tm() -> None:
    import datetime
    from django.conf import settings
    from test_app.models import Orders
    from test_app.services import send_telegram
    from test_app.services import main_logger

    today = datetime.date.today()
    delivered = Orders.objects.filter(delivery_date=today)
    if delivered:
        if settings.BOT_TOKEN and settings.CHANNEL_ID:
            for order in delivered:
                message = f'Order #{order.order} was delivered.'
                send_telegram(message)
        else:
            main_logger.error('You need to enter bot_token and channel_id to sending the messages.')


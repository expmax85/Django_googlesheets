import logging
import requests
import telebot

from creds.config import token, channel_id

logger = logging.getLogger(__name__)
bot = telebot.TeleBot(token)


def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, data={
         "chat_id": channel_id,
         "text": text
          })
    try:
        if r.status_code != 200:
            raise ValueError
    except ValueError as err:
        logger.error(f"{err}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s',
                        filemode='a', filename='logs.log')
    while True:
        try:
            bot.polling(none_stop=True, interval=3)
        except Exception as err:
            logger.error(f'{err}')

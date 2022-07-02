# Скрипт-приложение для импорта в реальном времени данных из google sheets в БД

## Описание
Это тестовое задание по реализации импорта данных из заданного листа/диапазона сервиса google sheets в БД. 
Подключение к api сервисам google осуществляется через oauth2 - двухэтапную аутентификацию, через api-приложение в системе google.

## Установка

### Клонирование репозитория
```console
git clone https://github.com/expmax85/django_sheets.git
cd django_sheets/
python -m pip install -r requirements.txt
```

### Создание api-приложения в системе google
Для работы проекта необходимо предоставить json-файл подключения к сервисам google.Для этого:
 - создайте проект: [инструкция](https://cloud.google.com/resource-manager/docs/creating-managing-projects?hl=ru#creating_a_project)
 - создайте учетные данные и получите файл `client_secret.json`: [инструкция](https://developers.google.com/identity/protocols/oauth2/web-server#creatingcred). При создании учетных данных, необходимо добавить в Authorized redirect URIs адрес: http://127.0.0.1:5000 для вашей последующей авторизации
 - Переименуйте файл `client_secret.json `в `credentials.json` и поместите его в папку `creds`, которую необходимо создать в корневой директории проекта.

Получить `token` для вашего телеграм-бота, который будет отправлять сообщение:
[инструкция](https://core.telegram.org/bots#6-botfather)

Узнать id вашего профиля в телеграмме:
[инструкция](https://perfluence.net/blog/article/kak-uznat-id-telegram#h-article-61a651fb18fdb)

Cоздать файл `.env` и заполнить его по шаблону файла `.env.template`.
Установить и создать БД, заполнить все поля файла `.env`.
```console
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```
## Запуск ассинхронных задач
```
redis-server
celery -A django_sheets worker -l info
celery -A django_sheets beat -l info
```

## Docker
Чтобы запустить проект через docker-compose, необходимо переименовать файл `.env.template` в `.env`, внести правки при необходимости в нем и в файле `docker-compose.yml`.
В контейнере используются python3.8 и postgres последней версии.
И выполнить поочередно следующие команды:
```console
sudo docker-compose build
sudo docker-compose up
```


## Админ панель

Через административную панель осуществляется настройка таких параметров, как id книги из google sheets, с которого считывается информация, 
название и диапазон листа, валюта, из которой нужно осуществить перевод, курс рубля, который обновляется автоматически в планировщике задач celery. 
А также id профиля в телеграмме, которому будет отправляться сообщение о доставленных ордерах.

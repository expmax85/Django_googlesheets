```
redis-server
celery -A django_sheets worker -l info
celery -A django_sheets beat -l info
celery -A django_sheets flower
```
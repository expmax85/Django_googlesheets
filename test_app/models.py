from django.db import models


class Orders(models.Model):
    order = models.PositiveBigIntegerField(unique=True)
    price = models.DecimalField(max_digits=8, decimal_places=0)
    delivery_date = models.DateField()
    rub_price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return str(self.order)

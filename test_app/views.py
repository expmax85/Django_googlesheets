from django.views.generic import ListView

from bot import send_telegram
from test_app.models import Orders
from test_app.services import GOOGLE_SHEETS


class IndexView(ListView):
    model = Orders
    template_name = 'index.html'
    context_object_name = 'orders'

    def get_context_data(self, *args, **kwargs):
        context = super(IndexView, self).get_context_data(*args, **kwargs)
        # GOOGLE_SHEETS.poll_update()
        # send_telegram('jnghfdktyj')
        # # googsh.create_db()
        return context

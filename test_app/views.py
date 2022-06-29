from django.views.generic import ListView

from test_app.models import Orders
from test_app.tasks import poll_update


class IndexView(ListView):
    model = Orders
    template_name = 'index.html'
    context_object_name = 'orders'

    def get_context_data(self, *args, **kwargs):
        context = super(IndexView, self).get_context_data(*args, **kwargs)
        poll_update()
        return context

from django.urls import path

from test_app.views import IndexView


urlpatterns = [
    path('', IndexView.as_view())
]

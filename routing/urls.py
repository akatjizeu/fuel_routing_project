from django.urls import path
from routing.views import route_view

urlpatterns = [
    path('route/', route_view, name='route'),
]

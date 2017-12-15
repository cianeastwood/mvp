from django.conf.urls import url
from . import views

app_name = 'vola'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^performance/$', views.performance, name='performance'),
    url(r'^custom/', views.custom, name='custom'),
    url(r'^about/', views.about, name='about'),
]
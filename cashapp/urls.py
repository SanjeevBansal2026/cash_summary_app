from django.urls import path
from . import views
urlpatterns=[
 path('',views.dashboard,name='dashboard'), path('login/',views.login_view,name='login'), path('logout/',views.logout_view,name='logout'),
 path('entries/',views.entry_list,name='entry_list'), path('entries/new/',views.entry_create,name='entry_create'), path('entries/<int:pk>/',views.entry_detail,name='entry_detail'), path('entries/<int:pk>/edit/',views.entry_edit,name='entry_edit'), path('entries/<int:pk>/review/',views.entry_review,name='entry_review'),
]

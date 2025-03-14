# cafe/urls.py
from django.urls import path
from . import views

app_name = 'cafe'
urlpatterns = [
    path('', views.home, name='home'),  # Root URL goes to home
    path('signup/', views.signup, name='signup'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout, name='logout'),
    path('reserve_table/', views.reserve_table, name='reserve_table'),
    path('reserve_ps_room/', views.reserve_ps_room, name='reserve_ps_room'),
    path('place_order/', views.place_order, name='place_order'),
    path('admin/', views.admin_page, name='admin_page'),
    path('admin/get_new_orders/', views.get_new_orders, name='get_new_orders'),
    path('admin/items/', views.items_page, name='items_page'),
    path('admin/tables_rooms/', views.tables_rooms_page, name='tables_rooms_page'),
    path('admin/orders/', views.orders_page, name='orders_page'),
    path('admin/get_orders/', views.get_orders, name='get_orders'),
    path('admin/add_table/', views.add_table, name='add_table'),
    path('admin/edit_table/<int:table_id>/', views.edit_table, name='edit_table'),
    path('admin/delete_table/<int:table_id>/', views.delete_table, name='delete_table'),
    path('admin/add_room/', views.add_room, name='add_room'),
    path('admin/edit_room/<int:room_id>/', views.edit_room, name='edit_room'),
    path('admin/delete_room/<int:room_id>/', views.delete_room, name='delete_room'),
    path('admin/add_item/', views.add_item, name='add_item'),
    path('admin/edit_item/<int:item_id>/', views.edit_item, name='edit_item'),
    path('admin/delete_item/<int:item_id>/', views.delete_item, name='delete_item'),
    path('submit-feedback/', views.submit_feedback, name='submit_feedback'),
    path('admin/update_order_status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('admin/table_reservations/', views.table_reservations_page, name='table_reservations_page'),
    path('get_table_reservations/', views.get_table_reservations, name='get_table_reservations'),
    path('admin/get_new_table_reservations/', views.get_new_table_reservations, name='get_new_table_reservations'),
    path('admin/room_reservations/', views.room_reservations_page, name='room_reservations_page'),
    path('get_room_reservations/', views.get_room_reservations, name='get_room_reservations'),
    path('admin/get_new_room_reservations/', views.get_new_room_reservations, name='get_new_room_reservations'),
    path('admin/update_reservation_attendance/<str:reservation_type>/<int:reservation_id>/', views.update_reservation_attendance, name='update_reservation_attendance'),
]
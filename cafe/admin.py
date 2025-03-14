from django.contrib import admin
from .models import Table, Room, Item, TableReservation, RoomReservation, Order, OrderItem,Testimonial
from django.utils.html import format_html

# Table Admin
@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('number', 'reservation_type', 'is_available')
    list_filter = ('is_available', 'reservation_type')
    search_fields = ('number',)
    ordering = ('number',)
    fields = ('number', 'reservation_type', 'is_available')  # Added reservation_type to fields

# Room Admin
@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('number', 'is_available')
    list_filter = ('is_available',)
    search_fields = ('number',)
    ordering = ('number',)

# Item Admin
@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'item_type', 'is_available', 'image_preview')  # Added item_type
    list_filter = ('is_available', 'item_type')  # Added item_type filter
    search_fields = ('name',)
    ordering = ('name',)
    fields = ('name', 'price', 'item_type', 'is_available', 'image')  # Added item_type to fields

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 50px;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Image'

# Table Reservation Admin
@admin.register(TableReservation)
class TableReservationAdmin(admin.ModelAdmin):
    list_display = ('user', 'table', 'date', 'start_time', 'duration', 'created_at')
    list_filter = ('date', 'duration')
    search_fields = ('user__username', 'table__number')
    ordering = ('-created_at',)
    date_hierarchy = 'date'

# Room Reservation Admin
@admin.register(RoomReservation)
class RoomReservationAdmin(admin.ModelAdmin):
    list_display = ('user', 'room', 'date', 'start_time', 'duration', 'created_at')
    list_filter = ('date', 'duration')
    search_fields = ('user__username', 'room__number')
    ordering = ('-created_at',)
    date_hierarchy = 'date'

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('user', 'table_number', 'created_at', 'status', 'total_items')  # Added table_number
    list_filter = ('status', 'created_at')
    search_fields = ('user__username',)
    ordering = ('-created_at',)
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'

    def total_items(self, obj):
        return obj.items.count()
    total_items.short_description = 'Total Items'

    def table_number(self, obj):
        return obj.table.number if obj.table else "No Table"  # Display table number
# OrderItem Admin (optional standalone registration)
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'item', 'quantity')
    search_fields = ('order__user__username', 'item__name')
    ordering = ('order__created_at',)

# Testimonial Admin
@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('author', 'content_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('author', 'content')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    def content_preview(self, obj):
        return obj.content[:50] + ('...' if len(obj.content) > 50 else '')
    content_preview.short_description = 'Content'    
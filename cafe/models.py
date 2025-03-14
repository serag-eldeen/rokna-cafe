from django.db import models
from django.contrib.auth.models import User

# Define ITEM_TYPES at the module level
ITEM_TYPES = [
    ('dessert', 'حلويات'),
    ('yogurt', 'زبادي'),
    ('fruit_salad', 'سلطة فواكه'),
    ('iced_coffee', 'قهوة مثلجة'),
    ('hot_drinks', 'مشروبات ساخنة'),
    ('herbs', 'أعشاب'),
    ('soda_cocktail', 'كوكتيل صودا'),
    ('milkshake', 'ميلك شيك'),
    ('coffee', 'قهوة'),
    ('espresso', 'إسبريسو'),
    ('fruit_cocktail', 'كوكتيل فواكه'),
    ('smoothie', 'سموذي'),
    ('waffle', 'وافل'),
    ('juices', 'عصائر'),
    ('tea', 'شاي'),
    ('iced_tea', 'شاي مثلج'),
]

RESERVATION_TYPES = [
    ('single', 'سنجل'),
    ('families', 'عائلات'),
    ('youth', 'شباب'),
    ('match', 'ماتش'),
]

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, unique=True)
    points = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} - {self.phone_number}"

class Table(models.Model):
    number = models.IntegerField(unique=True)
    is_available = models.BooleanField(default=True)
    reservation_type = models.CharField(max_length=20, choices=RESERVATION_TYPES, default='single')

    def __str__(self):
        return f"Table {self.number} ({self.get_reservation_type_display()})"

class Room(models.Model):
    number = models.IntegerField(unique=True)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"Room {self.number}"

class Item(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    is_available = models.BooleanField(default=True)
    image = models.ImageField(upload_to='items/', null=True, blank=True)
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES, default='dessert')

    def __str__(self):
        return f"{self.name} ({self.get_item_type_display()})"

class TableReservation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    duration = models.IntegerField(choices=[(30, '30 min'), (60, '1 hour'), (120, '2 hours')])
    created_at = models.DateTimeField(auto_now_add=True)
    attended = models.BooleanField(null=True, blank=True, default=None)  # New field: True (attended), False (no-show), None (not yet confirmed)

    def __str__(self):
        return f"{self.user.username} - Table {self.table.number} - {self.date}"

class RoomReservation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    duration = models.IntegerField(choices=[(30, '30 min'), (60, '1 hour'), (120, '2 hours')])
    created_at = models.DateTimeField(auto_now_add=True)
    attended = models.BooleanField(null=True, blank=True, default=None)  # New field: True (attended), False (no-show), None (not yet confirmed)

    def __str__(self):
        return f"{self.user.username} - Room {self.room.number} - {self.date}"

    def __str__(self):
        return f"{self.user.username} - Room {self.room.number} - {self.date}"

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    location = models.CharField(max_length=50)  # e.g., "table_1" or "room_1"
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='Pending')

    def __str__(self):
        return f"Order by {self.user.username} - {self.location} - {self.created_at}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

class Testimonial(models.Model):
    author = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.author} - {self.content[:50]}"
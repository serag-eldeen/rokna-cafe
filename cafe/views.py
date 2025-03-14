from django.shortcuts import render, redirect
from django.contrib.auth import logout as auth_logout, authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.utils import timezone
from django.conf import settings
from datetime import datetime, timedelta
import os
import logging
from django.db import models
from .models import (
    Table, Room, Item, TableReservation, RoomReservation, 
    Order, OrderItem, Testimonial, ITEM_TYPES, UserProfile,RESERVATION_TYPES
)
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)  # For debugging

# --- Utility Functions ---
def is_staff(user):
    """Check if a user is a staff member."""
    return user.is_staff

def signup(request):
    """Handle user signup with phone number."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        phone_number = request.POST.get('phone_number')

        # Check if all required fields are provided
        if not phone_number:
            return render(request, 'cafe/signup.html', {
                'form': form,
                'error': 'Phone number is required.'
            })

        # Check if the username already exists
        username = request.POST.get('username')
        if User.objects.filter(username=username).exists():
            return render(request, 'cafe/signup.html', {
                'form': form,
                'error': 'This username is already taken. Please choose a different one.'
            })

        # Check if the phone number already exists
        if UserProfile.objects.filter(phone_number=phone_number).exists():
            return render(request, 'cafe/signup.html', {
                'form': form,
                'error': 'This phone number is already registered. Please use a different one.'
            })

        # Validate the form and create the user if everything is valid
        if form.is_valid():
            try:
                user = form.save()  # Save the User object
                UserProfile.objects.create(user=user, phone_number=phone_number)  # Create UserProfile
                return redirect('login')
            except Exception as e:
                # Handle unexpected errors (e.g., database issues)
                return render(request, 'cafe/signup.html', {
                    'form': form,
                    'error': f'An error occurred while creating your account: {str(e)}'
                })
        else:
            # Form is invalid (e.g., password mismatch or invalid characters)
            return render(request, 'cafe/signup.html', {
                'form': form,
                'error': 'Please provide a valid username and password. Ensure passwords match.'
            })
    else:
        form = UserCreationForm()

    return render(request, 'cafe/signup.html', {'form': form})

class CustomLoginView(View):
    """Custom login view accepting username or phone number."""
    template_name = 'cafe/login.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        identifier = request.POST.get('username')  # Could be phone number or username
        password = request.POST.get('password')
        user = authenticate(request, username=identifier, password=password)
        if user is not None:
            login(request, user)
            return redirect('cafe:home')
        else:
            return render(request, self.template_name, {
                'error': 'Invalid phone number/username or password.'
            })

def logout(request):
    """Log out the user and redirect to home."""
    auth_logout(request)
    return redirect('cafe:home')

# --- Public Views ---
def home(request):
    """Render the home page with menu images, testimonials, and user points."""
    if request.method == 'POST':
        author = request.POST.get('author')
        content = request.POST.get('content')
        if author and content:
            Testimonial.objects.create(author=author, content=content)
        return redirect('cafe:home')

    menu_dir = os.path.join(settings.STATICFILES_DIRS[0], 'menu')
    image_files = [f for f in os.listdir(menu_dir) if f.endswith(('.jpg', '.png', '.jpeg', '.gif'))]
    testimonials = Testimonial.objects.all().order_by('-created_at')
    points = 0
    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            points = user_profile.points
        except UserProfile.DoesNotExist:
            points = 0

    return render(request, 'cafe/home.html', {
        'menu_images': image_files,
        'testimonials': testimonials,
        'points': points
    })

def submit_feedback(request):
    """Handle feedback submission."""
    if request.method == 'POST':
        author = request.POST.get('author')
        content = request.POST.get('content')
        if author and content:
            Testimonial.objects.create(author=author, content=content)
    return redirect('cafe:home')

# --- User Action Views ---
@login_required
def reserve_table(request):
    """Handle table reservation with reservation type filtering."""
    reservation_types = RESERVATION_TYPES
    selected_type = request.POST.get('reservation_type') or request.GET.get('reservation_type') or 'single'

    # Filter tables: Include tables of the selected type OR "match" type
    tables = Table.objects.filter(reservation_type__in=[selected_type, 'match'])
    context = {'tables': tables, 'reservation_types': reservation_types, 'selected_type': selected_type}

    if request.method == 'POST':
        reservation_type = request.POST.get('reservation_type')
        table_number = request.POST.get('table_number')
        date_str = request.POST.get('date')
        start_time_str = request.POST.get('start_time')
        duration = request.POST.get('duration')

        if not all([reservation_type, table_number, date_str, start_time_str, duration]):
            context['error'] = "All fields (reservation type, table, date, start time, duration) are required."
            return render(request, 'cafe/reserve_table.html', context)

        try:
            duration = int(duration)
            reservation_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            start_datetime = datetime.combine(reservation_date, start_time)
            end_datetime = start_datetime + timedelta(minutes=duration)

            # Validate table: Allow tables of the selected type OR "match" type
            table = Table.objects.get(
                number=table_number,
                reservation_type__in=[reservation_type, 'match']
            )

            existing_reservations = TableReservation.objects.filter(table=table, date=reservation_date)
            for res in existing_reservations:
                res_start = datetime.combine(res.date, res.start_time)
                res_end = res_start + timedelta(minutes=res.duration)
                if (start_datetime < res_end) and (end_datetime > res_start):
                    context['error'] = (
                        f"Table {table.number} ({table.get_reservation_type_display()}) is already reserved from "
                        f"{res.start_time.strftime('%I:%M %p')} to "
                        f"{res_end.strftime('%I:%M %p')} on {res.date}."
                    )
                    return render(request, 'cafe/reserve_table.html', context)

            reservation = TableReservation(
                user=request.user, table=table, date=reservation_date,
                start_time=start_time, duration=duration
            )
            reservation.save()
            context['message'] = (
                f"Table {table.number} ({table.get_reservation_type_display()}) reserved successfully for {duration} minutes "
                f"on {reservation_date} at {start_time.strftime('%I:%M %p')}."
            )
        except ValueError as e:
            context['error'] = f"Invalid input: {str(e)}. Use date as YYYY-MM-DD and time as HH:MM (e.g., 14:30)."
        except Table.DoesNotExist:
            context['error'] = "Selected table does not exist or is not available for this reservation type."

    return render(request, 'cafe/reserve_table.html', context)
@login_required
def reserve_ps_room(request):
    """Handle PS room reservation."""
    rooms = Room.objects.all()
    context = {'rooms': rooms}

    if request.method == 'POST':
        room_number = request.POST.get('room_number')
        date_str = request.POST.get('date')
        start_time_str = request.POST.get('start_time')  # Expected format: "HH:MM" (24-hour from input type="time")
        duration = request.POST.get('duration')

        # Validate all required fields
        if not all([room_number, date_str, start_time_str, duration]):
            context['error'] = "All fields (room, date, start time, duration) are required."
            return render(request, 'cafe/reserve_ps_room.html', context)

        try:
            duration = int(duration)
            reservation_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            # Parse 24-hour time from <input type="time">
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            start_datetime = datetime.combine(reservation_date, start_time)
            end_datetime = start_datetime + timedelta(minutes=duration)
            room = Room.objects.get(number=room_number)

            existing_reservations = RoomReservation.objects.filter(room=room, date=reservation_date)
            for res in existing_reservations:
                res_start = datetime.combine(res.date, res.start_time)
                res_end = res_start + timedelta(minutes=res.duration)
                if (start_datetime < res_end) and (end_datetime > res_start):
                    context['error'] = (
                        f"Room {room.number} is already reserved from "
                        f"{res.start_time.strftime('%I:%M %p')} to "
                        f"{res_end.strftime('%I:%M %p')} on {res.date}."
                    )
                    return render(request, 'cafe/reserve_ps_room.html', context)

            reservation = RoomReservation(
                user=request.user, room=room, date=reservation_date,
                start_time=start_time, duration=duration
            )
            reservation.save()
            context['message'] = (
                f"Room {room.number} reserved successfully for {duration} minutes "
                f"on {reservation_date} at {start_time.strftime('%I:%M %p')}."
            )
        except ValueError as e:
            context['error'] = f"Invalid input: {str(e)}. Use date as YYYY-MM-DD and time as HH:MM (e.g., 14:30)."
        except Room.DoesNotExist:
            context['error'] = "Selected room does not exist."

    return render(request, 'cafe/reserve_ps_room.html', context)

@login_required
def place_order(request):
    """Handle order placement."""
    tables = Table.objects.all()
    rooms = Room.objects.all()
    items = Item.objects.filter(is_available=True)
    item_types = ITEM_TYPES

    if request.method == 'POST':
        location = request.POST.get('location')
        item_type = request.POST.get('item_type')
        selected_items = []

        print("POST Data:", request.POST)
        if item_type:
            items = items.filter(item_type=item_type)

        for item in items:
            if f'item_{item.id}' in request.POST:
                quantity = request.POST.get(f'quantity_{item.id}', 1)
                print(f"Item {item.id} selected, raw quantity: {quantity}")
                try:
                    quantity = int(quantity)
                    if quantity < 1:
                        quantity = 1
                except (ValueError, TypeError):
                    quantity = 1
                print(f"Processed quantity for item {item.id}: {quantity}")
                selected_items.append((item, quantity))

        if not selected_items:
            return render(request, 'cafe/place_order.html', {
                'items': items, 'tables': tables, 'rooms': rooms,
                'item_types': item_types, 'selected_type': item_type,
                'error': 'No items selected'
            })

        if not location:
            return render(request, 'cafe/place_order.html', {
                'items': items, 'tables': tables, 'rooms': rooms,
                'item_types': item_types, 'selected_type': item_type,
                'error': 'Please select a location'
            })

        try:
            location_type, location_number = location.split('_')
            location_number = int(location_number)
            if location_type == 'table' and not Table.objects.filter(number=location_number).exists():
                raise ValueError("Invalid table number")
            elif location_type == 'room' and not Room.objects.filter(number=location_number).exists():
                raise ValueError("Invalid room number")
            elif location_type not in ['table', 'room']:
                raise ValueError("Invalid location type")
        except (ValueError, IndexError):
            return render(request, 'cafe/place_order.html', {
                'items': items, 'tables': tables, 'rooms': rooms,
                'item_types': item_types, 'selected_type': item_type,
                'error': 'Invalid location selected'
            })

        order = Order(user=request.user, location=location)
        order.save()
        for item, quantity in selected_items:
            if not item.is_available:
                order.delete()
                return render(request, 'cafe/place_order.html', {
                    'items': items, 'tables': tables, 'rooms': rooms,
                    'item_types': item_types, 'selected_type': item_type,
                    'error': f'{item.name} is out of stock'
                })
            OrderItem.objects.create(order=order, item=item, quantity=quantity)
            print(f"Saved OrderItem: {item.name} x{quantity}")

        location_display = f"{location_type.capitalize()} {location_number}"
        return render(request, 'cafe/place_order.html', {
            'items': items, 'tables': tables, 'rooms': rooms,
            'item_types': item_types, 'selected_type': item_type,
            'message': f'Order placed successfully for {location_display}!'
        })

    return render(request, 'cafe/place_order.html', {
        'items': items, 'tables': tables, 'rooms': rooms,
        'item_types': item_types, 'selected_type': None
    })

# --- Admin Views ---
@login_required
@user_passes_test(is_staff)
def admin_page(request):
    """Render the admin dashboard."""
    context = {}
    return render(request, 'cafe/admin_page.html', context)

@login_required
@user_passes_test(is_staff)
def tables_rooms_page(request):
    context = {
        'tables': Table.objects.all(),
        'rooms': Room.objects.all(),
        'reservation_types': RESERVATION_TYPES,  # Add this line
    }
    return render(request, 'cafe/tables_rooms_page.html', context)

@login_required
@user_passes_test(is_staff)
def items_page(request):
    """Display items management page."""
    context = {
        'items': Item.objects.all(),
        'item_types': ITEM_TYPES,
    }
    return render(request, 'cafe/items_page.html', context)

@login_required
@user_passes_test(is_staff)
def orders_page(request):
    """Display orders management page."""
    date_str = request.GET.get('date', '')
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
    except ValueError:
        selected_date = timezone.now().date()

    context = {
        'orders': Order.objects.filter(created_at__date=selected_date),
        'selected_date': selected_date,
    }
    return render(request, 'cafe/orders_page.html', context)

@login_required
@user_passes_test(is_staff)
def table_reservations_page(request):
    """Display table reservations management page."""
    date_str = request.GET.get('date', '')
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
    except ValueError:
        selected_date = timezone.now().date()

    context = {
        'table_reservations': TableReservation.objects.filter(date=selected_date).order_by('start_time'),
        'selected_date': selected_date,
    }
    return render(request, 'cafe/table_reservations_page.html', context)

@login_required
@user_passes_test(is_staff)
def room_reservations_page(request):
    """Display room reservations management page."""
    date_str = request.GET.get('date', '')
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
    except ValueError:
        selected_date = timezone.now().date()

    context = {
        'room_reservations': RoomReservation.objects.filter(date=selected_date),
        'selected_date': selected_date,
    }
    return render(request, 'cafe/room_reservations_page.html', context)

# --- Admin Management Views ---
@csrf_exempt
@login_required
@user_passes_test(is_staff)
def add_table(request):
    if request.method == 'POST':
        number = request.POST.get('number')
        reservation_type = request.POST.get('reservation_type')
        if Table.objects.filter(number=number).exists():
            return render(request, 'cafe/tables_rooms_page.html', {
                'tables': Table.objects.all(), 'rooms': Room.objects.all(),
                'reservation_types': RESERVATION_TYPES,
                'error': 'Table number already exists'
            })
        if reservation_type not in dict(RESERVATION_TYPES):
            return render(request, 'cafe/tables_rooms_page.html', {
                'tables': Table.objects.all(), 'rooms': Room.objects.all(),
                'reservation_types': RESERVATION_TYPES,
                'error': 'Invalid reservation type'
            })
        Table.objects.create(number=number, reservation_type=reservation_type)
        return redirect('cafe:tables_rooms_page')
    return redirect('cafe:tables_rooms_page')

@csrf_exempt
@login_required
@user_passes_test(is_staff)
def edit_table(request, table_id):
    try:
        table = Table.objects.get(id=table_id)
        if request.method == 'POST':
            new_number = request.POST.get('number')
            new_reservation_type = request.POST.get('reservation_type')
            if new_number != str(table.number) and Table.objects.filter(number=new_number).exists():
                return render(request, 'cafe/tables_rooms_page.html', {
                    'tables': Table.objects.all(), 'rooms': Room.objects.all(),
                    'reservation_types': RESERVATION_TYPES,
                    'error': 'Table number already exists'
                })
            if new_reservation_type not in dict(RESERVATION_TYPES):
                return render(request, 'cafe/tables_rooms_page.html', {
                    'tables': Table.objects.all(), 'rooms': Room.objects.all(),
                    'reservation_types': RESERVATION_TYPES,
                    'error': 'Invalid reservation type'
                })
            table.number = new_number
            table.reservation_type = new_reservation_type
            table.is_available = request.POST.get('is_available') == 'true'
            table.save()
            return redirect('cafe:tables_rooms_page')
        return redirect('cafe:tables_rooms_page')
    except Table.DoesNotExist:
        return render(request, 'cafe/tables_rooms_page.html', {
            'tables': Table.objects.all(), 'rooms': Room.objects.all(),
            'reservation_types': RESERVATION_TYPES,
            'error': 'Table not found'
        })

@csrf_exempt
@login_required
@user_passes_test(is_staff)
def delete_table(request, table_id):
    """Delete a table."""
    try:
        if request.method == 'POST':
            Table.objects.get(id=table_id).delete()
            return redirect('cafe:admin_page')
        return redirect('cafe:admin_page')
    except Table.DoesNotExist:
        return render(request, 'cafe/admin_page.html', {
            'tables': Table.objects.all(), 'rooms': Room.objects.all(),
            'items': Item.objects.all(), 'table_reservations': TableReservation.objects.all(),
            'room_reservations': RoomReservation.objects.all(), 'orders': Order.objects.all(),
            'error': 'Table not found'
        })

@csrf_exempt
@login_required
@user_passes_test(is_staff)
def add_room(request):
    """Add a new room."""
    if request.method == 'POST':
        number = request.POST.get('number')
        if Room.objects.filter(number=number).exists():
            return render(request, 'cafe/admin_page.html', {
                'tables': Table.objects.all(), 'rooms': Room.objects.all(),
                'items': Item.objects.all(), 'table_reservations': TableReservation.objects.all(),
                'room_reservations': RoomReservation.objects.all(), 'orders': Order.objects.all(),
                'error': 'Room number already exists'
            })
        Room.objects.create(number=number)
        return redirect('cafe:tables_rooms_page')
    return redirect('cafe:tables_rooms_page')

@csrf_exempt
@login_required
@user_passes_test(is_staff)
def edit_room(request, room_id):
    """Edit an existing room."""
    try:
        room = Room.objects.get(id=room_id)
        if request.method == 'POST':
            new_number = request.POST.get('number')
            if new_number != str(room.number) and Room.objects.filter(number=new_number).exists():
                return render(request, 'cafe/admin_page.html', {
                    'tables': Table.objects.all(), 'rooms': Room.objects.all(),
                    'items': Item.objects.all(), 'table_reservations': TableReservation.objects.all(),
                    'room_reservations': RoomReservation.objects.all(), 'orders': Order.objects.all(),
                    'error': 'Room number already exists'
                })
            room.number = new_number
            room.is_available = request.POST.get('is_available') == 'true'
            room.save()
            return redirect('cafe:admin_page')
        return redirect('cafe:admin_page')
    except Room.DoesNotExist:
        return render(request, 'cafe/admin_page.html', {
            'tables': Table.objects.all(), 'rooms': Room.objects.all(),
            'items': Item.objects.all(), 'table_reservations': TableReservation.objects.all(),
            'room_reservations': RoomReservation.objects.all(), 'orders': Order.objects.all(),
            'error': 'Room not found'
        })

@csrf_exempt
@login_required
@user_passes_test(is_staff)
def delete_room(request, room_id):
    """Delete a room."""
    try:
        if request.method == 'POST':
            Room.objects.get(id=room_id).delete()
            return redirect('cafe:admin_page')
        return redirect('cafe:admin_page')
    except Room.DoesNotExist:
        return render(request, 'cafe/admin_page.html', {
            'tables': Table.objects.all(), 'rooms': Room.objects.all(),
            'items': Item.objects.all(), 'table_reservations': TableReservation.objects.all(),
            'room_reservations': RoomReservation.objects.all(), 'orders': Order.objects.all(),
            'error': 'Room not found'
        })

@login_required
@user_passes_test(is_staff)
def add_item(request):
    """Handle adding a new item."""
    context = {'items': Item.objects.all(), 'item_types': ITEM_TYPES}

    if request.method == 'POST':
        name = request.POST.get('name')
        price = request.POST.get('price')
        item_type = request.POST.get('item_type')
        image = request.FILES.get('image')

        if not name or not price or not item_type:
            context['error'] = 'All fields (name, price, item type) are required.'
            return render(request, 'cafe/items_page.html', context)

        try:
            price = float(price)
            if item_type not in dict(ITEM_TYPES):
                raise ValueError("Invalid item type selected.")
            item = Item(name=name, price=price, item_type=item_type, image=image)
            item.save()
            context['message'] = f'Item "{name}" added successfully!'
            context['items'] = Item.objects.all()
            return render(request, 'cafe/items_page.html', context)
        except ValueError as e:
            context['error'] = str(e)
            return render(request, 'cafe/items_page.html', context)

    return render(request, 'cafe/items_page.html', context)

@csrf_exempt
@login_required
@user_passes_test(is_staff)
def edit_item(request, item_id):
    """Edit an existing item."""
    try:
        item = Item.objects.get(id=item_id)
        if request.method == 'POST':
            new_name = request.POST.get('name')
            new_price = request.POST.get('price')
            if new_name != item.name and Item.objects.filter(name=new_name).exists():
                return render(request, 'cafe/admin_page.html', {
                    'tables': Table.objects.all(), 'rooms': Room.objects.all(),
                    'items': Item.objects.all(), 'table_reservations': TableReservation.objects.all(),
                    'room_reservations': RoomReservation.objects.all(), 'orders': Order.objects.all(),
                    'error': 'Item name already exists'
                })
            try:
                item.name = new_name
                item.price = float(new_price)
                item.is_available = request.POST.get('is_available') == 'true'
                item.save()
                return redirect('cafe:admin_page')
            except ValueError:
                return render(request, 'cafe/admin_page.html', {
                    'tables': Table.objects.all(), 'rooms': Room.objects.all(),
                    'items': Item.objects.all(), 'table_reservations': TableReservation.objects.all(),
                    'room_reservations': RoomReservation.objects.all(), 'orders': Order.objects.all(),
                    'error': 'Invalid price'
                })
        return redirect('cafe:admin_page')
    except Item.DoesNotExist:
        return render(request, 'cafe/admin_page.html', {
            'tables': Table.objects.all(), 'rooms': Room.objects.all(),
            'items': Item.objects.all(), 'table_reservations': TableReservation.objects.all(),
            'room_reservations': RoomReservation.objects.all(), 'orders': Order.objects.all(),
            'error': 'Item not found'
        })

@csrf_exempt
@login_required
@user_passes_test(is_staff)
def delete_item(request, item_id):
    """Delete an item."""
    try:
        if request.method == 'POST':
            Item.objects.get(id=item_id).delete()
            return redirect('cafe:admin_page')
        return redirect('cafe:admin_page')
    except Item.DoesNotExist:
        return render(request, 'cafe/admin_page.html', {
            'tables': Table.objects.all(), 'rooms': Room.objects.all(),
            'items': Item.objects.all(), 'table_reservations': TableReservation.objects.all(),
            'room_reservations': RoomReservation.objects.all(), 'orders': Order.objects.all(),
            'error': 'Item not found'
        })

# --- API Endpoints ---
@login_required
def get_table_reservations(request):
    """Get all table reservations as JSON for a given date and reservation type."""
    date_str = request.GET.get('date', '')
    reservation_type = request.GET.get('reservation_type', '')  # جلب نوع الحجز من الطلب

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
    except ValueError:
        selected_date = timezone.now().date()

    # فلترة الحجوزات بناءً على التاريخ ونوع الحجز
    if reservation_type:
        reservations = TableReservation.objects.filter(
            date=selected_date,
            table__reservation_type=reservation_type  # فلترة بناءً على نوع الحجز الخاص بالترابيزة
        ).order_by('start_time')
    else:
        reservations = TableReservation.objects.filter(date=selected_date).order_by('start_time')

    data = {
        'table_reservations': [
            {
                'id': res.id,
                'user': res.user.username,
                'table': res.table.number,
                'table_reservation_type': res.table.reservation_type,
                'date': res.date.strftime('%Y-%m-%d'),
                'start_time': res.start_time.strftime('%H:%M'),  # استخدام 24 ساعة لتتطابق مع الـ input
                'duration': res.duration,
                'attended': res.attended
            } for res in reservations
        ]
    }
    return JsonResponse(data)
@login_required
@csrf_exempt
def get_new_table_reservations(request):
    """Get new table reservations since last ID."""
    last_reservation_id = int(request.GET.get('last_reservation_id', 0))
    date_str = request.GET.get('date', '')
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
    except ValueError:
        selected_date = timezone.now().date()

    new_reservations = TableReservation.objects.filter(id__gt=last_reservation_id, date=selected_date).order_by('start_time')
    reservations_data = [
        {
            'id': res.id,
            'user': res.user.username,
            'table': res.table.number,
            'table_reservation_type': res.table.reservation_type,
            'date': res.date.strftime('%Y-%m-%d'),
            'start_time': res.start_time.strftime('%I:%M %p')
        } for res in new_reservations
    ]
    return JsonResponse({'table_reservations': reservations_data})

@login_required
@csrf_exempt
def get_room_reservations(request):
    """Get room reservations as JSON."""
    date_str = request.GET.get('date', '')
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
    except ValueError:
        selected_date = timezone.now().date()

    reservations = RoomReservation.objects.filter(date=selected_date).order_by('start_time')
    data = {
        'room_reservations': [
            {
                'id': res.id, 'user': res.user.username, 'room': res.room.number,
                'date': res.date.strftime('%Y-%m-%d'), 
                'start_time': res.start_time.strftime('%I:%M %p'),  # 12-hour format with AM/PM
                'duration': res.duration, 'attended': res.attended
            } for res in reservations
        ]
    }
    return JsonResponse(data)

@login_required
@csrf_exempt
def get_new_room_reservations(request):
    """Get new room reservations since last ID."""
    last_reservation_id = int(request.GET.get('last_reservation_id', 0))
    date_str = request.GET.get('date', '')
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
    except ValueError:
        selected_date = timezone.now().date()

    new_reservations = RoomReservation.objects.filter(id__gt=last_reservation_id, date=selected_date).order_by('start_time')
    reservations_data = [
        {
            'id': res.id, 'user': res.user.username, 'room': res.room.number,
            'date': res.date.strftime('%Y-%m-%d'), 
            'start_time': res.start_time.strftime('%I:%M %p')  # 12-hour format with AM/PM
        } for res in new_reservations
    ]
    return JsonResponse({'room_reservations': reservations_data})

@login_required
@csrf_exempt
def get_orders(request):
    """Get orders as JSON."""
    date_str = request.GET.get('date', '')
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
    except ValueError:
        selected_date = timezone.now().date()

    orders = Order.objects.filter(created_at__date=selected_date).order_by('created_at')
    data = {
        'orders': [
            {
                'id': order.id, 'user': order.user.username, 'location': order.location,
                'created_at': timezone.localtime(order.created_at).strftime('%Y-%m-%d %I:%M:%S %p'),  # 12-hour format
                'status': order.status,
                'items': [{'name': oi.item.name, 'quantity': oi.quantity} for oi in order.orderitem_set.all()]
            } for order in orders
        ]
    }
    return JsonResponse(data)

@login_required
@csrf_exempt
def get_new_orders(request):
    """Get new orders since last ID."""
    last_order_id = int(request.GET.get('last_order_id', 0))
    date_str = request.GET.get('date', '')
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
    except ValueError:
        selected_date = timezone.now().date()

    new_orders = Order.objects.filter(id__gt=last_order_id, created_at__date=selected_date).order_by('created_at')
    orders_data = [
        {
            'id': order.id, 'user': order.user.username, 'location': order.location,
            'created_at': timezone.localtime(order.created_at).strftime('%Y-%m-%d %I:%M:%S %p'),  # 12-hour format
            'status': order.status,
            'items': [{'name': oi.item.name, 'quantity': oi.quantity} for oi in order.orderitem_set.all()]
        } for order in new_orders
    ]
    return JsonResponse({'orders': orders_data})

@login_required
@user_passes_test(is_staff)
@csrf_exempt
def update_reservation_attendance(request, reservation_type, reservation_id):
    """Update reservation attendance and award points."""
    if request.method == 'POST':
        logger.info(f"Received POST request for {reservation_type} reservation ID {reservation_id}")
        try:
            if reservation_type == 'table':
                reservation = TableReservation.objects.get(id=reservation_id)
            elif reservation_type == 'room':
                reservation = RoomReservation.objects.get(id=reservation_id)
            else:
                logger.error(f"Invalid reservation type: {reservation_type}")
                return HttpResponse('Invalid reservation type', status=400)

            attended = request.POST.get('attended')
            logger.info(f"Attended value received: {attended}")
            if attended == 'true':
                reservation.attended = True
                user_profile = UserProfile.objects.get(user=reservation.user)
                user_profile.points += 10
                user_profile.save()
                logger.info(f"Increased points for {reservation.user.username} to {user_profile.points}")
            elif attended == 'false':
                reservation.attended = False
            else:
                logger.error(f"Invalid attended value: {attended}")
                return HttpResponse('Invalid attended value', status=400)

            reservation.save()
            logger.info(f"Updated {reservation_type} reservation {reservation_id} with attended={reservation.attended}")
            return JsonResponse({'status': 'success', 'attended': reservation.attended})
        except (TableReservation.DoesNotExist, RoomReservation.DoesNotExist):
            logger.error(f"Reservation not found: {reservation_type} {reservation_id}")
            return HttpResponse('Reservation not found', status=404)
        except UserProfile.DoesNotExist:
            logger.error(f"UserProfile not found for user: {reservation.user.username}")
            return HttpResponse('User profile not found', status=500)
        except Exception as e:
            logger.error(f"Error updating attendance: {str(e)}")
            return HttpResponse(f'Error: {str(e)}', status=500)
    logger.warning(f"Invalid method: {request.method}")
    return HttpResponse('Method not allowed', status=405)

@login_required
@user_passes_test(is_staff)
@csrf_exempt
def update_order_status(request, order_id):
    """Update order status and award points on delivery."""
    if request.method == 'POST':
        logger.info(f"Received POST request to update order ID {order_id}")
        try:
            order = Order.objects.get(id=order_id)
            new_status = request.POST.get('status')
            valid_statuses = ['Pending', 'Preparing', 'Ready', 'Delivered']

            if new_status not in valid_statuses:
                logger.error(f"Invalid status value: {new_status}")
                return HttpResponse('Invalid status', status=400)

            if new_status == 'Delivered' and order.status != 'Delivered':
                try:
                    user_profile = UserProfile.objects.get(user=order.user)
                    user_profile.points += 10
                    user_profile.save()
                    logger.info(f"Increased points for {order.user.username} to {user_profile.points} for order {order_id}")
                except UserProfile.DoesNotExist:
                    logger.error(f"UserProfile not found for user: {order.user.username}")
                    return HttpResponse('User profile not found', status=500)

            order.status = new_status
            order.save()
            logger.info(f"Updated order {order_id} to status={order.status}")
            return HttpResponse(status=200)
        except Order.DoesNotExist:
            logger.error(f"Order not found: {order_id}")
            return HttpResponse('Order not found', status=404)
        except Exception as e:
            logger.error(f"Error updating order status: {str(e)}")
            return HttpResponse(f'Error: {str(e)}', status=500)
    logger.warning(f"Invalid method: {request.method}")
    return HttpResponse('Method not allowed', status=405)
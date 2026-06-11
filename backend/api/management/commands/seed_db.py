from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import UserProfile, Box, Collection, Assignment, Expense, Complaint, Activity, Message
from django.utils import timezone
from datetime import datetime, timezone as pytimezone
import secrets

class Command(BaseCommand):
    help = 'Seeds the database with sample operational data (optional dev command)'

    def handle(self, *args, **options):
        if UserProfile.objects.filter(role='admin').exists():
            self.stdout.write(self.style.ERROR(
                'An admin account already exists. Register via /register or create users manually.'
            ))
            return

        self.stdout.write("Clearing existing data...")
        User.objects.all().delete()
        Box.objects.all().delete()
        Collection.objects.all().delete()
        Assignment.objects.all().delete()
        Expense.objects.all().delete()
        Complaint.objects.all().delete()
        Activity.objects.all().delete()
        Message.objects.all().delete()

        # 1. Admin User
        admin_password = secrets.token_urlsafe(12)
        admin = User.objects.create_superuser('admin', 'admin@email.com', admin_password)
        admin.first_name = 'Admin'
        admin.save()
        
        # Ensure profile exists
        profile, created = UserProfile.objects.get_or_create(user=admin)
        profile.role = 'admin'
        profile.first_login = False
        profile.save()

        self.stdout.write(self.style.WARNING(f'Admin created — username: admin | password: {admin_password}'))

        # 2. Collectors
        collectors_data = [
            {'username': 'ahmed', 'name': 'Ahmed Khan', 'phone': '+92 301 2345678', 'email': 'ahmed.khan@email.com', 'area': 'Gulshan-e-Iqbal'},
            {'username': 'bilal', 'name': 'Bilal Hussain', 'phone': '+92 302 3456789', 'email': 'bilal.hussain@email.com', 'area': 'North Nazimabad'},
            {'username': 'farhan', 'name': 'Farhan Siddiqui', 'phone': '+92 303 4567890', 'email': 'farhan.s@email.com', 'area': 'Clifton'},
        ]
        collectors_map = {}
        for data in collectors_data:
            collector_password = secrets.token_urlsafe(12)
            name_parts = data['name'].split(' ')
            u = User.objects.create_user(
                username=data['username'],
                email=data['email'],
                password=collector_password,
                first_name=name_parts[0],
                last_name=name_parts[1]
            )
            u.profile.role = 'collector'
            u.profile.phone = data['phone']
            u.profile.area = data['area']
            u.profile.first_login = True
            u.profile.save()
            collectors_map[data['username']] = u
            self.stdout.write(self.style.WARNING(
                f'Collector created — username: {data["username"]} | password: {collector_password}'
            ))

        # 3. Boxes
        boxes_data = [
            {'name': 'Masjid Al-Noor Box', 'num': 1001, 'donor': 'Haji Abdul Rashid', 'phone': '+92 321 1111111', 'addr': 'Masjid Al-Noor, Block 5, Gulshan-e-Iqbal, Karachi', 'map': 'https://maps.google.com/?q=24.9213,67.0867', 'collector': 'ahmed', 'status': 'active'},
            {'name': 'Green Mart Store', 'num': 1002, 'donor': 'Muhammad Ismail', 'phone': '+92 321 2222222', 'addr': 'Shop #12, Main University Road, Gulshan-e-Iqbal', 'map': 'https://maps.google.com/?q=24.9273,67.0907', 'collector': 'ahmed', 'status': 'active'},
            {'name': 'Baitul Maal Office', 'num': 1003, 'donor': 'Dr. Farooq Ahmed', 'phone': '+92 321 3333333', 'addr': 'Office 201, Trade Tower, Shahrah-e-Faisal', 'map': None, 'collector': 'ahmed', 'status': 'active'},
            {'name': 'Jamia Masjid Collection', 'num': 1004, 'donor': 'Maulana Tariq', 'phone': '+92 322 4444444', 'addr': 'Jamia Masjid, Block 14, North Nazimabad', 'map': 'https://maps.google.com/?q=24.9423,67.0307', 'collector': 'bilal', 'status': 'active'},
            {'name': 'Pharmacy Plus', 'num': 1005, 'donor': 'Ali Pharmacy', 'phone': '+92 322 5555555', 'addr': 'Near Hyderi Market, North Nazimabad', 'map': 'https://maps.google.com/?q=24.9380,67.0350', 'collector': 'bilal', 'status': 'active'},
            {'name': 'Al-Khidmat Foundation', 'num': 1006, 'donor': 'Khidmat Trust', 'phone': '+92 322 6666666', 'addr': 'Al-Khidmat Office, Nazimabad No. 4', 'map': None, 'collector': 'bilal', 'status': 'active'},
            {'name': 'Clifton Masjid Box', 'num': 1007, 'donor': 'Haji Suleiman', 'phone': '+92 323 7777777', 'addr': 'Masjid-e-Tooba, Clifton Block 7', 'map': 'https://maps.google.com/?q=24.8137,67.0300', 'collector': 'farhan', 'status': 'active'},
            {'name': 'Sea View Restaurant', 'num': 1008, 'donor': 'Karachi Foods', 'phone': '+92 323 8888888', 'addr': 'Sea View Avenue, DHA Phase 6', 'map': 'https://maps.google.com/?q=24.8050,67.0350', 'collector': 'farhan', 'status': 'active'},
            {'name': 'Zamzam Medical', 'num': 1009, 'donor': 'Dr. Ayesha', 'phone': '+92 323 9999999', 'addr': 'Zamzam Medical Center, Clifton Block 2', 'map': None, 'collector': 'farhan', 'status': 'active'},
            {'name': 'Defence Bakery Box', 'num': 1010, 'donor': 'Kareem Bakery', 'phone': '+92 324 1010101', 'addr': 'Kareem Bakery, DHA Phase 5', 'map': 'https://maps.google.com/?q=24.8100,67.0600', 'collector': 'farhan', 'status': 'active'},
            {'name': 'Saddar Cloth Market', 'num': 1011, 'donor': 'Rahim Textiles', 'phone': '+92 324 1111112', 'addr': 'Shop 45, Saddar Cloth Market, Saddar', 'map': None, 'collector': None, 'status': 'active'},
            {'name': 'Korangi Masjid', 'num': 1012, 'donor': 'Korangi Masjid Committee', 'phone': '+92 324 1212121', 'addr': 'Main Korangi Road, Korangi Sector 33', 'map': 'https://maps.google.com/?q=24.8400,67.1300', 'collector': None, 'status': 'inactive'},
            {'name': 'Tariq Road Shop', 'num': 1013, 'donor': 'Usman Electronics', 'phone': '+92 325 1313131', 'addr': 'Usman Electronics, Tariq Road, PECHS', 'map': 'https://maps.google.com/?q=24.8700,67.0600', 'collector': 'ahmed', 'status': 'active'},
            {'name': 'Gulshan Market Box', 'num': 1014, 'donor': 'Nadeem General Store', 'phone': '+92 325 1414141', 'addr': 'Gulshan Market, Block 13-A', 'map': None, 'collector': 'ahmed', 'status': 'maintenance'},
            {'name': 'FB Area Masjid', 'num': 1015, 'donor': 'Masjid Committee FB Area', 'phone': '+92 325 1515151', 'addr': 'Federal B Area, Block 16, near Nagan Chowrangi', 'map': 'https://maps.google.com/?q=24.9500,67.0200', 'collector': 'bilal', 'status': 'active'},
        ]
        boxes_map = {}
        for data in boxes_data:
            qr = f"DBOX-{data['num']}-{data['name'].replace(' ', '').upper()[:8]}"
            assigned = collectors_map[data['collector']] if data['collector'] else None
            box = Box.objects.create(
                name=data['name'],
                box_number=data['num'],
                donor_name=data['donor'],
                donor_phone=data['phone'],
                address=data['addr'],
                map_link=data['map'],
                qr_code_data=qr,
                status=data['status'],
                assigned_collector=assigned
            )
            boxes_map[data['num']] = box

        # 4. Collections
        collections_data = [
            (1001, 'ahmed', 2500.0, 'Regular collection', '2025-06-01T14:00:00Z'),
            (1002, 'ahmed', 1800.0, '', '2025-06-01T15:00:00Z'),
            (1004, 'bilal', 3200.0, 'Box was almost full', '2025-06-02T10:00:00Z'),
            (1007, 'farhan', 4100.0, '', '2025-06-02T11:00:00Z'),
            (1005, 'bilal', 1500.0, 'Low collection', '2025-06-03T09:00:00Z'),
            (1008, 'farhan', 2200.0, '', '2025-06-03T12:00:00Z'),
            (1003, 'ahmed', 5000.0, 'Eid donation season', '2025-06-04T10:00:00Z'),
            (1013, 'ahmed', 3100.0, '', '2025-06-04T14:00:00Z'),
            (1009, 'farhan', 1900.0, '', '2025-06-05T09:00:00Z'),
            (1015, 'bilal', 2700.0, 'Jummah collection', '2025-06-05T14:00:00Z'),
            (1010, 'farhan', 1600.0, '', '2025-06-06T10:00:00Z'),
            (1001, 'ahmed', 2800.0, 'Second week', '2025-06-07T11:00:00Z'),
            (1004, 'bilal', 3500.0, '', '2025-06-08T09:00:00Z'),
            (1007, 'farhan', 4500.0, 'Friday collection', '2025-06-09T13:00:00Z'),
            (1002, 'ahmed', 2100.0, '', '2025-06-10T10:00:00Z'),
            (1006, 'bilal', 2900.0, '', '2025-06-11T11:00:00Z'),
            (1008, 'farhan', 2000.0, '', '2025-06-12T14:00:00Z'),
            (1005, 'bilal', 1700.0, 'Rainy day, low', '2025-06-13T09:00:00Z'),
            (1013, 'ahmed', 3300.0, '', '2025-06-14T10:00:00Z'),
            (1009, 'farhan', 2400.0, '', '2025-06-15T12:00:00Z'),
        ]
        for box_num, coll_user, amt, notes, dt in collections_data:
            box = boxes_map[box_num]
            user = collectors_map[coll_user]
            Collection.objects.create(
                box=box,
                collector=user,
                amount=amt,
                notes=notes,
                collection_date=datetime.strptime(dt, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytimezone.utc)
            )

        # 5. Assignments
        assignments_data = [
            ('ahmed', 1001, 'weekly', 1, 'collected', '2025-06-07'),
            ('ahmed', 1002, 'weekly', 1, 'collected', '2025-06-10'),
            ('ahmed', 1003, 'monthly', 4, 'pending', '2025-06-04'),
            ('ahmed', 1013, 'weekly', 6, 'collected', '2025-06-14'),
            ('ahmed', 1014, 'monthly', 15, 'overdue', None),
            ('bilal', 1004, 'weekly', 2, 'collected', '2025-06-08'),
            ('bilal', 1005, 'weekly', 3, 'pending', '2025-06-13'),
            ('bilal', 1006, 'monthly', 11, 'collected', '2025-06-11'),
            ('bilal', 1015, 'weekly', 5, 'collected', '2025-06-05'),
            ('farhan', 1007, 'weekly', 5, 'collected', '2025-06-09'),
            ('farhan', 1008, 'weekly', 4, 'pending', '2025-06-12'),
            ('farhan', 1009, 'monthly', 15, 'collected', '2025-06-15'),
            ('farhan', 1010, 'weekly', 6, 'overdue', '2025-06-06'),
        ]
        for coll_user, box_num, sched, sched_day, stat, last_coll in assignments_data:
            box = boxes_map[box_num]
            user = collectors_map[coll_user]
            last_coll_dt = datetime.strptime(last_coll, "%Y-%m-%d").replace(tzinfo=pytimezone.utc) if last_coll else None
            Assignment.objects.create(
                collector=user,
                box=box,
                schedule=sched,
                schedule_day=sched_day,
                status=stat,
                last_collected=last_coll_dt
            )

        # 6. Expenses
        expenses_data = [
            ('ahmed', 'transport', 500.0, 'CNG rickshaw for Gulshan route', '2025-06-01T18:00:00Z'),
            ('bilal', 'food', 300.0, 'Lunch during collection drive', '2025-06-03T13:00:00Z'),
            ('farhan', 'phone_balance', 200.0, 'Monthly phone recharge', '2025-06-05T16:00:00Z'),
            ('ahmed', 'transport', 800.0, 'Uber for long distance collection', '2025-06-08T17:00:00Z'),
            ('bilal', 'other', 150.0, 'Box seal tape and stickers', '2025-06-10T15:00:00Z'),
        ]
        for coll_user, exp_type, amt, desc, dt in expenses_data:
            user = collectors_map[coll_user]
            Expense.objects.create(
                collector=user,
                type=exp_type,
                amount=amt,
                description=desc,
                date=datetime.strptime(dt, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytimezone.utc)
            )

        # 7. Complaints
        complaints_data = [
            ('ahmed', 1014, 'box_damaged', 'The donation box lock is broken and the slot is bent. Needs immediate replacement.', 'urgent', 'under_review', '2025-06-05T10:00:00Z'),
            ('farhan', 1010, 'box_full', 'Box is overflowing with donations. Collection was done but it fills up very quickly.', 'normal', 'reported', '2025-06-08T14:00:00Z'),
            ('bilal', 1006, 'location_changed', 'The shop relocated to a new address. Box needs to be moved. New address: Block 3, Shop 18.', 'normal', 'resolved', '2025-06-02T09:00:00Z'),
        ]
        for coll_user, box_num, issue, desc, urg, stat, dt in complaints_data:
            user = collectors_map[coll_user]
            box = boxes_map[box_num]
            Complaint.objects.create(
                collector=user,
                box=box,
                issue_type=issue,
                description=desc,
                urgency=urg,
                status=stat,
                created_at=datetime.strptime(dt, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytimezone.utc)
            )

        # 8. Activities
        activities_data = [
            ('collection', 'Ahmed Khan collected PKR 2,800 from Masjid Al-Noor Box', '2025-06-07T11:00:00Z'),
            ('collection', 'Bilal Hussain collected PKR 3,500 from Jamia Masjid', '2025-06-08T09:00:00Z'),
            ('complaint', 'Ahmed Khan reported box damage at Gulshan Market Box', '2025-06-05T10:00:00Z'),
            ('collection', 'Farhan Siddiqui collected PKR 4,500 from Clifton Masjid', '2025-06-09T13:00:00Z'),
            ('collection', 'Ahmed Khan collected PKR 2,100 from Green Mart Store', '2025-06-10T10:00:00Z'),
            ('collection', 'Bilal Hussain collected PKR 2,900 from Al-Khidmat Foundation', '2025-06-11T11:00:00Z'),
            ('collection', 'Farhan Siddiqui collected PKR 2,000 from Sea View Restaurant', '2025-06-12T14:00:00Z'),
            ('collection', 'Bilal Hussain collected PKR 1,700 from Pharmacy Plus', '2025-06-13T09:00:00Z'),
            ('collection', 'Ahmed Khan collected PKR 3,300 from Tariq Road Shop', '2025-06-14T10:00:00Z'),
            ('collection', 'Farhan Siddiqui collected PKR 2,400 from Zamzam Medical', '2025-06-15T12:00:00Z'),
        ]
        for act_type, desc, dt in activities_data:
            Activity.objects.create(
                type=act_type,
                description=desc,
                timestamp=datetime.strptime(dt, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytimezone.utc)
            )

        # 9. Messages
        messages_data = [
            ('admin', 'ahmed', 'Admin', 'Hi Ahmed, did you collect the box at Masjid Al-Noor?', '2025-06-06T10:00:00Z'),
            ('ahmed', 'admin', 'Ahmed Khan', 'Yes, I did. I have logged it in the app.', '2025-06-06T10:10:00Z'),
            ('admin', 'ahmed', 'Admin', 'Excellent, thank you. Let know if there are any issues.', '2025-06-06T10:20:00Z'),
        ]
        for snd, rcv, name, cont, dt in messages_data:
            sender = admin if snd == 'admin' else collectors_map[snd]
            receiver = admin if rcv == 'admin' else collectors_map[rcv]
            Message.objects.create(
                sender=sender,
                receiver=receiver,
                sender_name=name,
                content=cont,
                timestamp=datetime.strptime(dt, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytimezone.utc)
            )

        self.stdout.write(self.style.SUCCESS("Database seeded successfully!"))

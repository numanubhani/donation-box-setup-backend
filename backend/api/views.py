import secrets
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .broadcast import emit_event
from .models import UserProfile, Box, Collection, Assignment, Expense, Complaint, Activity, Message, TwilioSettings
from .permissions import IsAuthenticatedUser, IsAdmin
from .serializers import (
    CollectorSerializer, BoxSerializer, CollectionSerializer, 
    AssignmentSerializer, ExpenseSerializer, ComplaintSerializer, 
    ActivitySerializer, MessageSerializer, TwilioSettingsSerializer
)
from .twilio_service import send_collection_thank_you_sms, send_test_sms, DEFAULT_TEMPLATE


def _auth_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


def _user_auth_payload(user):
    role = user.profile.role if hasattr(user, 'profile') else 'collector'
    first_login = user.profile.first_login if hasattr(user, 'profile') else True
    return {
        'success': True,
        'role': role,
        'currentUserId': 'admin' if role == 'admin' else str(user.id),
        'firstLogin': first_login,
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def register_admin_view(request):
    if UserProfile.objects.filter(role='admin').exists():
        return Response(
            {'error': 'An admin account already exists. Please sign in instead.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')
    name = request.data.get('name', '').strip()
    email = request.data.get('email', '').strip()
    
    if not username or not password or not name or not email:
        return Response({'error': 'Please fill in all fields'}, status=status.HTTP_400_BAD_REQUEST)
        
    if User.objects.filter(username__iexact=username).exists():
        return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)
        
    name_parts = name.split(' ', 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ''
    
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        is_staff=True,
        is_superuser=True
    )
    
    profile, created = UserProfile.objects.get_or_create(user=user)
    profile.role = 'admin'
    profile.first_login = False
    profile.save()
    
    return Response({'success': True, 'message': 'Admin registered successfully'})


def _notify_sync():
    emit_event('data_change', resource='all')


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')
    
    if not username or not password:
        return Response({'success': False, 'error': 'Please fill in all fields'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(username__iexact=username)
        if user.check_password(password) and user.is_active:
            payload = _user_auth_payload(user)
            payload.update(_auth_tokens_for_user(user))
            return Response(payload)
    except User.DoesNotExist:
        pass
        
    return Response({
        'success': False,
        'error': 'Invalid username or password'
    }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticatedUser])
def change_password_view(request, pk):
    if request.user.id != pk and not (
        hasattr(request.user, 'profile') and request.user.profile.role == 'admin'
    ):
        return Response({'error': 'You can only change your own password'}, status=status.HTTP_403_FORBIDDEN)

    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
    current_password = request.data.get('currentPassword')
    new_password = request.data.get('password')
    
    if not current_password or not new_password:
        return Response({'error': 'Both current and new passwords are required'}, status=status.HTTP_400_BAD_REQUEST)
        
    if not user.check_password(current_password):
        return Response({'error': 'Current password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)
        
    user.set_password(new_password)
    user.save()
    
    profile, created = UserProfile.objects.get_or_create(user=user)
    profile.first_login = False
    profile.save()
    
    return Response({'success': True})


@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAuthenticatedUser])
def collectors_list(request):
    if request.method == 'GET':
        collectors = User.objects.filter(profile__role='collector')
        serializer = CollectorSerializer(collectors, many=True)
        return Response(serializer.data)
        
    elif request.method == 'DELETE':
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        User.objects.filter(profile__role='collector').delete()
        Activity.objects.all().delete()
        Message.objects.all().delete()
        _notify_sync()
        return Response({'success': True, 'message': 'All collectors deleted successfully'})
        
    elif request.method == 'POST':
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

        name = request.data.get('name')
        email = request.data.get('email')
        phone = request.data.get('phone')
        area = request.data.get('area')
        
        if not name or not email:
            return Response({'error': 'Name and email are required'}, status=status.HTTP_400_BAD_REQUEST)
            
        username = name.lower().replace(' ', '')
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
            
        name_parts = name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        temp_password = secrets.token_urlsafe(10)
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=temp_password,
            first_name=first_name,
            last_name=last_name
        )
        
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.role = 'collector'
        profile.phone = phone
        profile.area = area
        profile.first_login = True
        profile.save()
        
        Activity.objects.create(
            type='collector_added',
            description=f'New collector "{name}" added',
            related_id=str(user.id)
        )
        
        serializer = CollectorSerializer(user)
        response_data = serializer.data
        response_data['temporaryPassword'] = temp_password
        _notify_sync()
        return Response(response_data, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdmin])
def collector_detail(request, pk):
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({'error': 'Collector not found'}, status=status.HTTP_404_NOT_FOUND)
        
    name = request.data.get('name')
    if name:
        name_parts = name.split(' ', 1)
        user.first_name = name_parts[0]
        user.last_name = name_parts[1] if len(name_parts) > 1 else ''
        
    user.email = request.data.get('email', user.email)
    user.save()
    
    profile, created = UserProfile.objects.get_or_create(user=user)
    profile.phone = request.data.get('phone', profile.phone)
    profile.area = request.data.get('area', profile.area)
    if 'status' in request.data:
        user.is_active = (request.data.get('status') == 'active')
        user.save()
    profile.save()
    
    serializer = CollectorSerializer(user)
    _notify_sync()
    return Response(serializer.data)


@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAuthenticatedUser])
def boxes_list(request):
    if request.method == 'GET':
        boxes = Box.objects.all()
        serializer = BoxSerializer(boxes, many=True)
        return Response(serializer.data)
        
    elif request.method == 'DELETE':
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        Box.objects.all().delete()
        Activity.objects.all().delete()
        Collection.objects.all().delete()
        _notify_sync()
        return Response({'success': True, 'message': 'All boxes/donors deleted successfully'})
        
    elif request.method == 'POST':
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

        name = request.data.get('name')
        box_number = request.data.get('boxNumber')
        donor_name = request.data.get('donorName')
        donor_phone = request.data.get('donorPhone')
        key_number = request.data.get('keyNumber', '')
        address = request.data.get('address')
        map_link = request.data.get('mapLink')
        box_status = request.data.get('status', 'active')
        
        if not name or not box_number:
            return Response({'error': 'Name and Box Number are required'}, status=status.HTTP_400_BAD_REQUEST)

        if Box.objects.filter(box_number=box_number).exists():
            return Response({'error': 'Box number already exists'}, status=status.HTTP_400_BAD_REQUEST)
            
        qr_code_data = f"DBOX-{box_number}"
        
        box = Box.objects.create(
            name=name,
            box_number=box_number,
            donor_name=donor_name,
            donor_phone=donor_phone,
            key_number=key_number,
            address=address,
            map_link=map_link,
            qr_code_data=qr_code_data,
            status=box_status
        )
        
        Activity.objects.create(
            type='box_added',
            description=f'New box "{name}" (#{box_number}) installed',
            related_id=str(box.id)
        )
        
        serializer = BoxSerializer(box)
        _notify_sync()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticatedUser])
def box_detail(request, pk):
    try:
        box = Box.objects.get(pk=pk)
    except Box.DoesNotExist:
        return Response({'error': 'Box not found'}, status=status.HTTP_444_NOT_FOUND if False else status.HTTP_404_NOT_FOUND)
        
    if request.method == 'GET':
        serializer = BoxSerializer(box)
        return Response(serializer.data)
        
    elif request.method in ['PUT', 'PATCH']:
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

        if 'assignedCollectorId' in request.data:
            collector_id = request.data.get('assignedCollectorId')
            if collector_id:
                try:
                    collector = User.objects.get(pk=collector_id)
                    box.assigned_collector = collector
                except User.DoesNotExist:
                    return Response({'error': 'Collector not found'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                box.assigned_collector = None
                
        box.name = request.data.get('name', box.name)
        box.donor_name = request.data.get('donorName', box.donor_name)
        box.donor_phone = request.data.get('donorPhone', box.donor_phone)
        if 'keyNumber' in request.data:
            box.key_number = request.data.get('keyNumber', '')
        box.address = request.data.get('address', box.address)
        box.map_link = request.data.get('mapLink', box.map_link)
        box.status = request.data.get('status', box.status)
        box.save()
        
        serializer = BoxSerializer(box)
        _notify_sync()
        return Response(serializer.data)
        
    elif request.method == 'DELETE':
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        # Clean up related assignments
        Assignment.objects.filter(box=box).delete()
        box.delete()
        _notify_sync()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedUser])
def assignments_list(request):
    if request.method == 'GET':
        assignments = Assignment.objects.all()
        serializer = AssignmentSerializer(assignments, many=True)
        return Response(serializer.data)
        
    elif request.method == 'POST':
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

        collector_id = request.data.get('collectorId')
        box_id = request.data.get('boxId')
        schedule = request.data.get('schedule')
        schedule_day = request.data.get('scheduleDay')
        
        try:
            collector = User.objects.get(pk=collector_id)
            box = Box.objects.get(pk=box_id)
        except (User.DoesNotExist, Box.DoesNotExist):
            return Response({'error': 'Collector or Box not found'}, status=status.HTTP_400_BAD_REQUEST)
            
        assignment = Assignment.objects.create(
            collector=collector,
            box=box,
            schedule=schedule,
            schedule_day=schedule_day,
            status='pending'
        )
        
        # Link assigned collector directly to Box
        box.assigned_collector = collector
        box.save()
        
        Activity.objects.create(
            type='assignment',
            description=f'Box "{box.name}" assigned to collector "{collector.first_name} {collector.last_name}"',
            related_id=str(assignment.id)
        )
        
        serializer = AssignmentSerializer(assignment)
        _notify_sync()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticatedUser])
def assignment_detail(request, pk):
    try:
        assignment = Assignment.objects.get(pk=pk)
    except Assignment.DoesNotExist:
        return Response({'error': 'Assignment not found'}, status=status.HTTP_404_NOT_FOUND)
        
    assignment.status = request.data.get('status', assignment.status)
    last_collected = request.data.get('lastCollected')
    if last_collected:
        assignment.last_collected = last_collected
    assignment.save()
    
    serializer = AssignmentSerializer(assignment)
    _notify_sync()
    return Response(serializer.data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedUser])
def collections_list(request):
    if request.method == 'GET':
        collections = Collection.objects.all()
        serializer = CollectionSerializer(collections, many=True)
        return Response(serializer.data)
        
    elif request.method == 'POST':
        box_id = request.data.get('boxId')
        collector_id = request.data.get('collectorId')
        amount = request.data.get('amount')
        notes = request.data.get('notes')
        collection_date = request.data.get('collectionDate')
        
        try:
            box = Box.objects.get(pk=box_id)
            collector = User.objects.get(pk=collector_id)
        except (Box.DoesNotExist, User.DoesNotExist):
            return Response({'error': 'Box or Collector not found'}, status=status.HTTP_400_BAD_REQUEST)
            
        collection = Collection.objects.create(
            box=box,
            collector=collector,
            amount=amount,
            notes=notes,
            collection_date=collection_date
        )
        
        # Update related assignments status to collected
        Assignment.objects.filter(box=box, collector=collector).update(
            status='collected',
            last_collected=collection_date
        )
        
        collector_name = f"{collector.first_name} {collector.last_name}".strip() or collector.username
        Activity.objects.create(
            type='collection',
            description=f'{collector_name} collected PKR {int(amount):,} from {box.name}',
            related_id=str(collection.id)
        )

        sms_result = send_collection_thank_you_sms(box=box, amount=amount)

        serializer = CollectionSerializer(collection)
        response_data = serializer.data
        response_data['smsSent'] = sms_result.get('sent', False)
        if not sms_result.get('sent'):
            response_data['smsReason'] = sms_result.get('reason')
        _notify_sync()
        return Response(response_data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH', 'PUT'])
@permission_classes([IsAuthenticatedUser])
def collection_detail(request, pk):
    try:
        collection = Collection.objects.get(pk=pk)
    except Collection.DoesNotExist:
        return Response({'error': 'Collection not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = CollectionSerializer(collection)
        return Response(serializer.data)

    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    if 'boxId' in request.data:
        box_id = request.data.get('boxId')
        try:
            collection.box = Box.objects.get(pk=box_id)
        except Box.DoesNotExist:
            return Response({'error': 'Box not found'}, status=status.HTTP_400_BAD_REQUEST)

    if 'collectorId' in request.data:
        collector_id = request.data.get('collectorId')
        try:
            collection.collector = User.objects.get(pk=collector_id)
        except User.DoesNotExist:
            return Response({'error': 'Collector not found'}, status=status.HTTP_400_BAD_REQUEST)

    if 'amount' in request.data:
        collection.amount = request.data.get('amount')

    if 'notes' in request.data:
        collection.notes = request.data.get('notes')

    if 'collectionDate' in request.data:
        collection.collection_date = request.data.get('collectionDate')

    collection.save()

    collector_name = f"{collection.collector.first_name} {collection.collector.last_name}".strip() or collection.collector.username
    Activity.objects.filter(related_id=str(collection.id), type='collection').update(
        description=f'{collector_name} collected PKR {int(collection.amount):,} from {collection.box.name}'
    )

    serializer = CollectionSerializer(collection)
    _notify_sync()
    return Response(serializer.data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedUser])
def expenses_list(request):
    if request.method == 'GET':
        expenses = Expense.objects.all()
        serializer = ExpenseSerializer(expenses, many=True)
        return Response(serializer.data)
        
    elif request.method == 'POST':
        collector_id = request.data.get('collectorId')
        expense_type = request.data.get('type')
        amount = request.data.get('amount')
        description = request.data.get('description')
        date = request.data.get('date')
        receipt_url = request.data.get('receiptUrl')
        
        try:
            collector = User.objects.get(pk=collector_id)
        except User.DoesNotExist:
            return Response({'error': 'Collector not found'}, status=status.HTTP_400_BAD_REQUEST)
            
        expense = Expense.objects.create(
            collector=collector,
            type=expense_type,
            amount=amount,
            description=description,
            date=date,
            receipt_url=receipt_url
        )
        
        serializer = ExpenseSerializer(expense)
        _notify_sync()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedUser])
def complaints_list(request):
    if request.method == 'GET':
        complaints = Complaint.objects.all()
        serializer = ComplaintSerializer(complaints, many=True)
        return Response(serializer.data)
        
    elif request.method == 'POST':
        collector_id = request.data.get('collectorId')
        box_id = request.data.get('boxId')
        issue_type = request.data.get('issueType')
        description = request.data.get('description')
        photo_url = request.data.get('photoUrl')
        urgency = request.data.get('urgency', 'normal')
        status_val = request.data.get('status', 'reported')
        
        try:
            collector = User.objects.get(pk=collector_id)
            box = Box.objects.get(pk=box_id)
        except (User.DoesNotExist, Box.DoesNotExist):
            return Response({'error': 'Collector or Box not found'}, status=status.HTTP_400_BAD_REQUEST)
            
        complaint = Complaint.objects.create(
            collector=collector,
            box=box,
            issue_type=issue_type,
            description=description,
            photo_url=photo_url,
            urgency=urgency,
            status=status_val
        )
        
        Activity.objects.create(
            type='complaint',
            description=f'New issue "{issue_type.replace("_", " ").title()}" reported on Box {box.box_number}',
            related_id=str(complaint.id)
        )
        
        serializer = ComplaintSerializer(complaint)
        _notify_sync()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticatedUser])
def complaint_detail(request, pk):
    try:
        complaint = Complaint.objects.get(pk=pk)
    except Complaint.DoesNotExist:
        return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)
        
    complaint.status = request.data.get('status', complaint.status)
    complaint.save()
    
    serializer = ComplaintSerializer(complaint)
    _notify_sync()
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticatedUser])
def activities_list(request):
    activities = Activity.objects.all().order_by('-timestamp')
    serializer = ActivitySerializer(activities, many=True)
    return Response(serializer.data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedUser])
def messages_list(request):
    if request.method == 'GET':
        messages = Message.objects.all().order_by('timestamp')
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)
        
    elif request.method == 'POST':
        content = request.data.get('content')
        sender_id = request.data.get('senderId')
        receiver_id = request.data.get('receiverId')
        sender_name = request.data.get('senderName')
        
        try:
            if sender_id == 'admin':
                sender = User.objects.filter(profile__role='admin').first()
            else:
                sender = User.objects.get(pk=sender_id)
                
            if receiver_id == 'admin':
                receiver = User.objects.filter(profile__role='admin').first()
            else:
                receiver = User.objects.get(pk=receiver_id)
        except User.DoesNotExist:
            return Response({'error': 'Sender or receiver user not found'}, status=status.HTTP_400_BAD_REQUEST)
            
        if not sender or not receiver:
            return Response({'error': 'Sender or receiver user not found'}, status=status.HTTP_400_BAD_REQUEST)

        msg = Message.objects.create(
            sender=sender,
            receiver=receiver,
            sender_name=sender_name,
            content=content,
            timestamp=timezone.now()
        )
        
        serializer = MessageSerializer(msg)
        emit_event('chat_message', payload=serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticatedUser])
def mark_messages_read(request):
    collector_id = request.data.get('collectorId')
    role = request.data.get('role')

    if not role:
        return Response({'error': 'role is required'}, status=status.HTTP_400_BAD_REQUEST)

    if role == 'admin':
        if collector_id == '__all__':
            Message.objects.filter(
                receiver__profile__role='admin',
                is_read=False,
            ).exclude(sender__profile__role='admin').update(is_read=True)
        elif collector_id:
            Message.objects.filter(
                sender_id=collector_id,
                receiver__profile__role='admin',
                is_read=False,
            ).update(is_read=True)
        else:
            return Response({'error': 'collectorId is required'}, status=status.HTTP_400_BAD_REQUEST)
    elif collector_id:
        Message.objects.filter(
            sender__profile__role='admin',
            receiver_id=collector_id,
            is_read=False,
        ).update(is_read=True)
    else:
        return Response({'error': 'collectorId is required'}, status=status.HTTP_400_BAD_REQUEST)
        
    emit_event('messages_read', payload={'collectorId': str(collector_id), 'role': role})
    return Response({'success': True})


@api_view(['GET', 'PATCH'])
@permission_classes([IsAdmin])
def twilio_settings_view(request):
    settings = TwilioSettings.load()

    if request.method == 'GET':
        return Response(TwilioSettingsSerializer(settings).data)

    data = request.data
    if 'enabled' in data:
        settings.enabled = bool(data['enabled'])
    elif settings.is_configured():
        settings.enabled = True
    if 'accountSid' in data:
        settings.account_sid = data['accountSid'] or ''
    if 'fromNumber' in data:
        settings.from_number = data['fromNumber'] or ''
    if 'messageTemplate' in data:
        settings.message_template = data['messageTemplate'] or DEFAULT_TEMPLATE

    auth_token = data.get('authToken', '')
    if auth_token and not str(auth_token).startswith('•'):
        settings.auth_token = auth_token

    if settings.is_configured() and not settings.enabled and 'enabled' not in data:
        settings.enabled = True

    settings.save()
    return Response(TwilioSettingsSerializer(settings).data)


@api_view(['POST'])
@permission_classes([IsAdmin])
def twilio_test_sms_view(request):
    phone = request.data.get('phone', '').strip()
    if not phone:
        return Response({'error': 'phone is required'}, status=status.HTTP_400_BAD_REQUEST)

    result = send_test_sms(to_phone=phone)
    if result.get('sent'):
        return Response({'success': True, 'message': 'Test SMS sent successfully'})
    return Response(
        {'error': result.get('reason', 'Failed to send test SMS')},
        status=status.HTTP_400_BAD_REQUEST,
    )

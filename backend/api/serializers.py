from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, Box, Collection, Assignment, Expense, Complaint, Activity, Message, TwilioSettings

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['role', 'phone', 'area', 'first_login']

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile']


class CollectorSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    email = serializers.EmailField()
    area = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    firstLogin = serializers.SerializerMethodField()
    username = serializers.CharField()
    createdAt = serializers.DateTimeField(source='date_joined', format="%Y-%m-%dT%H:%M:%SZ", read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'name', 'phone', 'email', 'area', 'status', 'firstLogin', 'username', 'createdAt']
        
    def get_id(self, obj):
        return str(obj.id)
        
    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username
        
    def get_phone(self, obj):
        return obj.profile.phone if hasattr(obj, 'profile') else ""
        
    def get_area(self, obj):
        return obj.profile.area if hasattr(obj, 'profile') else ""
        
    def get_firstLogin(self, obj):
        return obj.profile.first_login if hasattr(obj, 'profile') else True
        
    def get_status(self, obj):
        return 'active' if obj.is_active else 'inactive'


class BoxSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    assignedCollectorId = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source='created_at', format="%Y-%m-%dT%H:%M:%SZ", read_only=True)
    qrCodeData = serializers.CharField(source='qr_code_data', read_only=True)
    boxNumber = serializers.IntegerField(source='box_number')
    donorName = serializers.CharField(source='donor_name')
    donorPhone = serializers.CharField(source='donor_phone')
    keyNumber = serializers.CharField(source='key_number', required=False, allow_blank=True)
    mapLink = serializers.URLField(source='map_link', required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = Box
        fields = ['id', 'name', 'boxNumber', 'donorName', 'donorPhone', 'keyNumber', 'address', 'mapLink', 'qrCodeData', 'status', 'assignedCollectorId', 'createdAt']

    def get_id(self, obj):
        return str(obj.id)

    def get_assignedCollectorId(self, obj):
        return str(obj.assigned_collector.id) if obj.assigned_collector else None


class CollectionSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    boxId = serializers.SerializerMethodField()
    collectorId = serializers.SerializerMethodField()
    collectionDate = serializers.DateTimeField(source='collection_date', format="%Y-%m-%dT%H:%M:%SZ")
    createdAt = serializers.DateTimeField(source='created_at', format="%Y-%m-%dT%H:%M:%SZ", read_only=True)
    amount = serializers.FloatField()

    class Meta:
        model = Collection
        fields = ['id', 'boxId', 'collectorId', 'amount', 'notes', 'collectionDate', 'createdAt']

    def get_id(self, obj):
        return str(obj.id)

    def get_boxId(self, obj):
        return str(obj.box.id)

    def get_collectorId(self, obj):
        return str(obj.collector.id)


class AssignmentSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    boxId = serializers.SerializerMethodField()
    collectorId = serializers.SerializerMethodField()
    scheduleDay = serializers.IntegerField(source='schedule_day', required=False, allow_null=True)
    lastCollected = serializers.DateTimeField(source='last_collected', format="%Y-%m-%dT%H:%M:%SZ", required=False, allow_null=True)
    createdAt = serializers.DateTimeField(source='created_at', format="%Y-%m-%dT%H:%M:%SZ", read_only=True)

    class Meta:
        model = Assignment
        fields = ['id', 'collectorId', 'boxId', 'schedule', 'scheduleDay', 'status', 'lastCollected', 'createdAt']

    def get_id(self, obj):
        return str(obj.id)

    def get_boxId(self, obj):
        return str(obj.box.id)

    def get_collectorId(self, obj):
        return str(obj.collector.id)


class ExpenseSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    collectorId = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source='created_at', format="%Y-%m-%dT%H:%M:%SZ", read_only=True)
    date = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ")
    receiptUrl = serializers.URLField(source='receipt_url', required=False, allow_null=True, allow_blank=True)
    amount = serializers.FloatField()

    class Meta:
        model = Expense
        fields = ['id', 'collectorId', 'type', 'amount', 'description', 'date', 'receiptUrl', 'createdAt']

    def get_id(self, obj):
        return str(obj.id)

    def get_collectorId(self, obj):
        return str(obj.collector.id)


class ComplaintSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    collectorId = serializers.SerializerMethodField()
    boxId = serializers.SerializerMethodField()
    issueType = serializers.CharField(source='issue_type')
    photoUrl = serializers.URLField(source='photo_url', required=False, allow_null=True, allow_blank=True)
    createdAt = serializers.DateTimeField(source='created_at', format="%Y-%m-%dT%H:%M:%SZ", read_only=True)

    class Meta:
        model = Complaint
        fields = ['id', 'collectorId', 'boxId', 'issueType', 'description', 'photoUrl', 'urgency', 'status', 'createdAt']

    def get_id(self, obj):
        return str(obj.id)

    def get_collectorId(self, obj):
        return str(obj.collector.id)

    def get_boxId(self, obj):
        return str(obj.box.id)


class ActivitySerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    relatedId = serializers.CharField(source='related_id', required=False, allow_null=True)
    timestamp = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ")

    class Meta:
        model = Activity
        fields = ['id', 'type', 'description', 'timestamp', 'relatedId']

    def get_id(self, obj):
        return str(obj.id)


class MessageSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    senderId = serializers.SerializerMethodField()
    receiverId = serializers.SerializerMethodField()
    senderName = serializers.CharField(source='sender_name')
    isRead = serializers.BooleanField(source='is_read')
    timestamp = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ")

    class Meta:
        model = Message
        fields = ['id', 'senderId', 'receiverId', 'senderName', 'content', 'timestamp', 'isRead']

    def get_id(self, obj):
        return str(obj.id)

    def get_senderId(self, obj):
        if hasattr(obj.sender, 'profile') and obj.sender.profile.role == 'admin':
            return 'admin'
        return str(obj.sender.id)

    def get_receiverId(self, obj):
        if hasattr(obj.receiver, 'profile') and obj.receiver.profile.role == 'admin':
            return 'admin'
        return str(obj.receiver.id)


class TwilioSettingsSerializer(serializers.ModelSerializer):
    accountSid = serializers.CharField(source='account_sid', required=False, allow_blank=True)
    authToken = serializers.SerializerMethodField()
    fromNumber = serializers.CharField(source='from_number', required=False, allow_blank=True)
    messageTemplate = serializers.CharField(source='message_template', required=False, allow_blank=True)
    updatedAt = serializers.DateTimeField(source='updated_at', format='%Y-%m-%dT%H:%M:%SZ', read_only=True)

    class Meta:
        model = TwilioSettings
        fields = ['enabled', 'accountSid', 'authToken', 'fromNumber', 'messageTemplate', 'updatedAt']

    def get_authToken(self, obj):
        if not obj.auth_token:
            return ''
        if len(obj.auth_token) >= 4:
            return '••••••••' + obj.auth_token[-4:]
        return '••••••••'

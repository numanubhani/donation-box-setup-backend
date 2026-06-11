from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('collector', 'Collector'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='collector')
    phone = models.CharField(max_length=20, blank=True, null=True)
    area = models.CharField(max_length=100, blank=True, null=True)
    first_login = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

# Automatically create or update UserProfile when a User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        UserProfile.objects.create(user=instance)


class Box(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Maintenance'),
    ]
    name = models.CharField(max_length=100)
    box_number = models.IntegerField(unique=True)
    donor_name = models.CharField(max_length=100)
    donor_phone = models.CharField(max_length=20)
    key_number = models.CharField(max_length=50, blank=True, default='')
    address = models.TextField()
    map_link = models.URLField(max_length=500, blank=True, null=True)
    qr_code_data = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    assigned_collector = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='assigned_boxes')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (#{self.box_number})"


class Collection(models.Model):
    box = models.ForeignKey(Box, on_delete=models.CASCADE, related_name='collections')
    collector = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collections')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    collection_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PKR {self.amount} from Box {self.box.box_number} by {self.collector.username}"


class Assignment(models.Model):
    SCHEDULE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('collected', 'Collected'),
        ('overdue', 'Overdue'),
    ]
    collector = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignments')
    box = models.ForeignKey(Box, on_delete=models.CASCADE, related_name='assignments')
    schedule = models.CharField(max_length=20, choices=SCHEDULE_CHOICES)
    schedule_day = models.IntegerField(blank=True, null=True)  # 0-6 or 1-31
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    last_collected = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Box {self.box.box_number} to {self.collector.username} ({self.schedule})"


class Expense(models.Model):
    EXPENSE_CHOICES = [
        ('transport', 'Transport'),
        ('food', 'Food'),
        ('phone_balance', 'Phone Balance'),
        ('other', 'Other'),
    ]
    collector = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')
    type = models.CharField(max_length=20, choices=EXPENSE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    date = models.DateTimeField()
    receipt_url = models.URLField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} - PKR {self.amount} by {self.collector.username}"


class Complaint(models.Model):
    ISSUE_CHOICES = [
        ('box_damaged', 'Box Damaged'),
        ('box_stolen', 'Box Stolen'),
        ('location_changed', 'Location Changed'),
        ('box_full', 'Box Full'),
        ('other', 'Other'),
    ]
    URGENCY_CHOICES = [
        ('normal', 'Normal'),
        ('urgent', 'Urgent'),
    ]
    STATUS_CHOICES = [
        ('reported', 'Reported'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
    ]
    collector = models.ForeignKey(User, on_delete=models.CASCADE, related_name='complaints')
    box = models.ForeignKey(Box, on_delete=models.CASCADE, related_name='complaints')
    issue_type = models.CharField(max_length=30, choices=ISSUE_CHOICES)
    description = models.TextField()
    photo_url = models.URLField(max_length=500, blank=True, null=True)
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='normal')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='reported')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.issue_type} on Box {self.box.box_number}"


class Activity(models.Model):
    TYPE_CHOICES = [
        ('collection', 'Collection'),
        ('box_added', 'Box Added'),
        ('collector_added', 'Collector Added'),
        ('complaint', 'Complaint'),
        ('assignment', 'Assignment'),
    ]
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    related_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.type}: {self.description[:30]}"


class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    sender_name = models.CharField(max_length=100)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Msg from {self.sender.username} to {self.receiver.username}"


class TwilioSettings(models.Model):
    enabled = models.BooleanField(default=True)
    account_sid = models.CharField(max_length=64, blank=True, default='')
    auth_token = models.CharField(max_length=64, blank=True, default='')
    from_number = models.CharField(max_length=20, blank=True, default='')
    message_template = models.TextField(
        default=(
            'Thank you {name} for your donation! '
            'Al-Najaat Foundation has received your amount: PKR {amount}. JazakAllah Khair!'
        )
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Twilio settings'

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'Twilio SMS Settings'

    def is_configured(self) -> bool:
        return bool(self.account_sid and self.auth_token and self.from_number)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_twilio_enabled_default'),
    ]

    operations = [
        migrations.AddField(
            model_name='box',
            name='key_number',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
    ]

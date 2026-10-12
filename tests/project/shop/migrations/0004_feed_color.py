from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0003_feed_refresh'),
    ]

    operations = [
        migrations.AddField(
            model_name='feed',
            name='color',
            field=models.CharField(blank=True, default='', max_length=10),
        ),
    ]

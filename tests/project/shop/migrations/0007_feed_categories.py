from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0006_feed_section'),
    ]

    operations = [
        migrations.AddField(
            model_name='feed',
            name='categories',
            field=models.ManyToManyField(blank=True, related_name='feeds', to='shop.category'),
        ),
    ]

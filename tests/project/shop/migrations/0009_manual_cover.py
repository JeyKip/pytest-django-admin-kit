from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0008_manual'),
    ]

    operations = [
        migrations.AddField(
            model_name='manual',
            name='cover',
            field=models.ImageField(blank=True, upload_to='covers/'),
        ),
    ]

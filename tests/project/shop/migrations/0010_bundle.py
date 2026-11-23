from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0009_manual_cover'),
    ]

    operations = [
        migrations.CreateModel(
            name='Bundle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('categories', models.ManyToManyField(blank=True, related_name='+', to='shop.category')),
                ('sections', models.ManyToManyField(blank=True, related_name='+', to='shop.category')),
            ],
        ),
    ]

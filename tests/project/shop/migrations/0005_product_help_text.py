from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0004_feed_color'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='sku',
            field=models.CharField(help_text='The code printed on the label.', max_length=32, unique=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='quantity',
            field=models.PositiveIntegerField(default=1, help_text='How many are in stock, counted <em>at the warehouse</em>.'),
        ),
        migrations.AlterField(
            model_name='product',
            name='is_active',
            field=models.BooleanField(default=True, help_text='Only active products are listed in the shop.'),
        ),
    ]

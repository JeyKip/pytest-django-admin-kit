import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0011_bundle_autocomplete'),
    ]

    operations = [
        migrations.AddField(
            model_name='bundle',
            name='replacement',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='shop.product'),
        ),
        migrations.AddField(
            model_name='bundle',
            name='spares',
            field=models.ManyToManyField(blank=True, related_name='+', to='shop.product'),
        ),
    ]

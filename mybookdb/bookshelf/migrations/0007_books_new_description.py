# Generated by Django 2.0.8 on 2018-08-23 12:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookshelf', '0006_auto_20180823_1208'),
    ]

    operations = [
        migrations.AddField(
            model_name='books',
            name='new_description',
            field=models.TextField(blank=True, null=True),
        ),
    ]

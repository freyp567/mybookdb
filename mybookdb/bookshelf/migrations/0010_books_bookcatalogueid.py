# Generated by Django 3.0.6 on 2020-06-04 17:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookshelf', '0009_onleihebooks_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='books',
            name='bookCatalogueId',
            field=models.UUIDField(null=True),
        ),
    ]

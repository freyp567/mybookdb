# Generated by Django 3.1.5 on 2021-01-07 06:31

from django.db import migrations, models


def set_synced_defaults(apps, schema_editor):
    books = apps.get_model('bookshelf', 'books')
    for book_obj in books.objects.all().iterator():
        book_obj.synced = book_obj.sync_mybookdroid
        book_obj.save()


def reverse_synced_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('bookshelf', '0013_auto_20200828_1448'),
    ]

    operations = [
        migrations.AddField(
            model_name='books',
            name='synced',
            field=models.DateField(null=True),
        ),
        migrations.RunPython(set_synced_defaults, reverse_synced_func),
    ]


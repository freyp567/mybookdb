# Generated by Django 2.0.3 on 2018-03-31 16:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bookshelf', '0002_auto_20180331_0923'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reviews',
            name='bookId',
        ),
        migrations.RemoveField(
            model_name='states',
            name='bookId',
        ),
        migrations.AddField(
            model_name='reviews',
            name='book',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='bookshelf.books'),
        ),
        migrations.AddField(
            model_name='states',
            name='book',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='bookshelf.books'),
        ),
    ]
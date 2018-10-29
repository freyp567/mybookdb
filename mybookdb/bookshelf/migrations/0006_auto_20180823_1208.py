# Generated by Django 2.0.8 on 2018-08-23 10:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookshelf', '0005_auto_20180403_1120'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='books',
            options={'permissions': (('can_create', 'Create book'), ('can_edit', 'Edit book'), ('can_delete', 'Delete book'))},
        ),
        migrations.AlterModelOptions(
            name='comments',
            options={'ordering': ['-dateCreated']},
        ),
        migrations.AddField(
            model_name='authors',
            name='updated',
            field=models.DateField(null=True),
        ),
        migrations.AlterField(
            model_name='books',
            name='isbn10',
            field=models.TextField(max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='books',
            name='isbn13',
            field=models.TextField(max_length=13, null=True),
        ),
        migrations.AlterField(
            model_name='books',
            name='title',
            field=models.TextField(max_length=255),
        ),
    ]
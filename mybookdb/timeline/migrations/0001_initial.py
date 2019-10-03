# Generated by Django 2.0.13 on 2019-09-19 18:01

from django.db import migrations, models
import django.db.models.deletion
import partial_date.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('bookshelf', '0014_auto_20181124_1018'),
    ]

    operations = [
        migrations.CreateModel(
            name='timelineevent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', partial_date.fields.PartialDateField()),
                ('location', models.TextField(null=True)),
                ('comment', models.TextField(null=True)),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bookshelf.books')),
            ],
        ),
    ]
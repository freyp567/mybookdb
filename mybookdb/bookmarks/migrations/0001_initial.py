# Generated by Django 2.0.9 on 2018-12-10 18:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('bookshelf', '0014_auto_20181124_1018'),
    ]

    operations = [
        migrations.CreateModel(
            name='author_links',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('link_name', models.TextField()),
                ('link_target', models.TextField()),
                ('link_uri', models.TextField()),
                ('link_state', models.TextField()),
                ('created', models.DateField()),
                ('updated', models.DateField()),
                ('verified', models.DateField(null=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='author_links', to='bookshelf.authors')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='book_links',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('link_name', models.TextField()),
                ('link_target', models.TextField()),
                ('link_uri', models.TextField()),
                ('link_state', models.TextField()),
                ('created', models.DateField()),
                ('updated', models.DateField()),
                ('verified', models.DateField(null=True)),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='book_links', to='bookshelf.books')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='linktargets',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField()),
                ('description', models.TextField(null=True)),
                ('base_url', models.TextField()),
            ],
        ),
    ]

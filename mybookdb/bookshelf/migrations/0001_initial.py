# Generated by Django 2.0.3 on 2018-03-28 13:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='authors',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField()),
                ('lowerCaseName', models.TextField()),
                ('familyName', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='books',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('isbn10', models.TextField(null=True)),
                ('isbn13', models.TextField(null=True)),
                ('title', models.TextField()),
                ('binding', models.CharField(max_length=80, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('numberOfPages', models.CharField(blank=True, max_length=10, null=True)),
                ('publisher', models.TextField(blank=True, null=True)),
                ('publicationDate', models.DateField(null=True)),
                ('reviewsFetchedDate', models.DateField(null=True)),
                ('offersFetchedDate', models.DateField(null=True)),
                ('grRating', models.FloatField(null=True)),
                ('grRatingsCount', models.IntegerField(null=True)),
                ('subject', models.TextField(blank=True, null=True)),
                ('created', models.DateField()),
                ('updated', models.DateField(null=True)),
                ('stateId', models.IntegerField()),
                ('userRating', models.IntegerField(null=True)),
                ('lentToName', models.CharField(max_length=120, null=True)),
                ('lentToUri', models.TextField(blank=True, null=True)),
                ('thumbnailSmall', models.TextField(blank=True, null=True)),
                ('thumbnailLarge', models.TextField(blank=True, null=True)),
                ('amazonBookId', models.IntegerField(null=True)),
                ('authors', models.ManyToManyField(to='bookshelf.authors')),
            ],
        ),
        migrations.CreateModel(
            name='comments',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('bookTitle', models.TextField()),
                ('dateCreated', models.IntegerField()),
                ('bookId', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bookId', to='bookshelf.books')),
            ],
        ),
        migrations.CreateModel(
            name='googleBooks',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('identifier', models.TextField()),
                ('subtitle', models.TextField()),
                ('subject', models.TextField()),
                ('publisher', models.TextField()),
                ('description', models.TextField()),
                ('format', models.TextField()),
                ('googleLink', models.TextField()),
                ('book', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='googleBookId', to='bookshelf.books')),
            ],
        ),
        migrations.CreateModel(
            name='grBooks',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('grId', models.TextField()),
                ('grAvgRating', models.FloatField()),
                ('grRatingsCount', models.IntegerField()),
                ('grRatingsSum', models.IntegerField()),
                ('grRatingDistOne', models.IntegerField()),
                ('grRatingDistTwo', models.IntegerField()),
                ('grRatingDistThree', models.IntegerField()),
                ('grRatingDistFour', models.IntegerField()),
                ('grRatingDistFive', models.IntegerField()),
                ('grLinkDetail', models.TextField()),
                ('book', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='grBookId', to='bookshelf.books')),
            ],
        ),
        migrations.CreateModel(
            name='groups',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='reviews',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bookId', models.IntegerField()),
                ('grReviewId', models.TextField()),
                ('dateCreated', models.IntegerField()),
                ('userName', models.TextField()),
                ('userUrl', models.TextField()),
                ('url', models.TextField()),
                ('body', models.TextField()),
                ('fullBody', models.TextField()),
                ('rating', models.IntegerField()),
                ('votes', models.IntegerField()),
                ('spoiler', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='states',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bookId', models.IntegerField()),
                ('favorite', models.IntegerField(default=0)),
                ('haveRead', models.IntegerField(default=0)),
                ('readingNow', models.IntegerField(default=0)),
                ('iOwn', models.IntegerField(default=0)),
                ('toBuy', models.IntegerField(default=0)),
                ('toRead', models.IntegerField(default=0)),
            ],
        ),
    ]

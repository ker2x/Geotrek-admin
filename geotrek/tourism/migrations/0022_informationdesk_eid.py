# Generated by Django 3.1.14 on 2022-06-13 08:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tourism', '0021_auto_20220203_1625'),
    ]

    operations = [
        migrations.AddField(
            model_name='informationdesk',
            name='eid',
            field=models.CharField(blank=True, max_length=1024, null=True, verbose_name='External id'),
        ),
    ]
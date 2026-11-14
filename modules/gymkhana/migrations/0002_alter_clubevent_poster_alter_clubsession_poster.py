from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gymkhana', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clubevent',
            name='poster',
            field=models.FileField(blank=True, null=True, upload_to='gymkhana/posters/'),
        ),
        migrations.AlterField(
            model_name='clubsession',
            name='poster',
            field=models.FileField(blank=True, null=True, upload_to='gymkhana/posters/'),
        ),
    ]

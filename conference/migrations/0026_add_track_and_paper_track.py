from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):
    dependencies = [
        ('conference', '0025_alter_subreviewerinvite_unique_together_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Track',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('track_id', models.CharField(max_length=20, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('conference', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tracks', to='conference.conference')),
                ('chair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chaired_tracks', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='paper',
            name='track',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='papers', to='conference.track'),
        ),
    ] 
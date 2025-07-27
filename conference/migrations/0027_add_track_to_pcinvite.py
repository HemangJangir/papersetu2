from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('conference', '0026_add_track_and_paper_track'),
    ]

    operations = [
        migrations.AddField(
            model_name='pcinvite',
            name='track',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pc_invites', to='conference.track'),
        ),
    ] 
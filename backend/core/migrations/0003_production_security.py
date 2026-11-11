from django.db import migrations, models
import django.db.models.deletion
class Migration(migrations.Migration):
    dependencies=[('core','0002_game_economy')]
    operations=[
      migrations.AddField(model_name='adopportunity',name='provider_reference',field=models.CharField(blank=True,max_length=128)),
      migrations.CreateModel(name='RefreshSession',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False)),('token_hash',models.CharField(max_length=64,unique=True)),('expires_at',models.DateTimeField()),('revoked_at',models.DateTimeField(blank=True,null=True)),('created_at',models.DateTimeField(auto_now_add=True)),('user',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='refresh_sessions',to='auth.user'))]),
      migrations.CreateModel(name='EmailVerification',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False)),('token_hash',models.CharField(max_length=64,unique=True)),('expires_at',models.DateTimeField()),('verified_at',models.DateTimeField(blank=True,null=True)),('user',models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,related_name='email_verification',to='auth.user'))]),
      migrations.CreateModel(name='PasswordResetToken',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False)),('token_hash',models.CharField(max_length=64,unique=True)),('expires_at',models.DateTimeField()),('used_at',models.DateTimeField(blank=True,null=True)),('user',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='password_resets',to='auth.user'))]),
      migrations.CreateModel(name='ApiKey',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False)),('name',models.CharField(max_length=80)),('key_prefix',models.CharField(max_length=12)),('key_hash',models.CharField(max_length=64,unique=True)),('last_used_at',models.DateTimeField(blank=True,null=True)),('revoked_at',models.DateTimeField(blank=True,null=True)),('created_at',models.DateTimeField(auto_now_add=True)),('user',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='api_keys',to='auth.user'))]),
    ]

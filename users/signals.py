import os
from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate
from django.dispatch import receiver

@receiver(post_migrate)
def create_superuser(sender, **kwargs):
    if os.environ.get("CREATE_SUPERUSER", "False") == "True":
        User = get_user_model()
        superuser_email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
        superuser_password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        superuser_username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')

        if superuser_email and superuser_password:
            if not User.objects.filter(is_superuser=True).exists(): 
                User.objects.create_superuser(
                    username=superuser_username,
                    email=superuser_email,
                    password=superuser_password
                )

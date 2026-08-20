from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Configura el usuario administrador único para pruebas (admin / mde123) y remueve usuarios sobrantes.'

    def handle(self, *args, **options):
        User = get_user_model()
        
        # Eliminar cualquier usuario que no sea admin
        User.objects.exclude(username='admin').delete()
        
        user, created = User.objects.get_or_create(username='admin')
        user.set_password('mde123')
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.save()
        
        if created:
            self.stdout.write(self.style.SUCCESS('Usuario admin creado exitosamente con contraseña mde123.'))
        else:
            self.stdout.write(self.style.SUCCESS('Usuario admin actualizado exitosamente con contraseña mde123.'))

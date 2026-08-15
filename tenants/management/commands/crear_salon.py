import secrets

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from tenants.models import Tenant


class Command(BaseCommand):
    help = (
        "Alta rápida de un salón nuevo (prospecto): crea el Tenant y un "
        "usuario propietario listo para entrar a /panel/<slug>/. Los "
        "peluqueros y servicios se cargan después, desde /admin/ o el bot."
    )

    def add_arguments(self, parser):
        parser.add_argument("--nombre", required=True, help="Nombre del salón, ej. 'Barbería XYZ'")
        parser.add_argument("--slug", help="Slug para la URL. Si no se pasa, se genera del nombre.")
        parser.add_argument("--whatsapp", default="", help="Número de WhatsApp Business, formato E.164")
        parser.add_argument("--username", required=True, help="Usuario para que el dueño entre al panel")
        parser.add_argument("--password", help="Si no se pasa, se genera una aleatoria y se muestra en pantalla")
        parser.add_argument("--email", default="", help="Email del propietario (opcional)")
        parser.add_argument("--color", default="#e94560", help="Color de marca en hex, ej. #1e88e5")

    def handle(self, *args, **options):
        nombre = options["nombre"]
        slug = options["slug"] or slugify(nombre)
        username = options["username"]
        password = options["password"] or secrets.token_urlsafe(9)

        if Tenant.objects.filter(slug=slug).exists():
            raise CommandError(f"Ya existe un salón con slug '{slug}'.")

        User = get_user_model()
        if User.objects.filter(username=username).exists():
            raise CommandError(f"Ya existe un usuario '{username}'. Elegí otro --username.")

        tenant = Tenant.objects.create(
            nombre=nombre, slug=slug, whatsapp_number=options["whatsapp"], color_primario=options["color"],
        )
        propietario = User.objects.create_user(
            username=username, password=password, email=options["email"], is_staff=False,
        )
        tenant.propietarios.add(propietario)

        self.stdout.write(self.style.SUCCESS(f"Salón '{nombre}' creado (slug={slug})."))
        self.stdout.write("")
        self.stdout.write(f"  Mini-web pública:  /salones/{slug}/")
        self.stdout.write(f"  Panel del dueño:   /panel/{slug}/")
        self.stdout.write(f"  Usuario:           {username}")
        self.stdout.write(f"  Contraseña:        {password}")
        self.stdout.write("")
        self.stdout.write(self.style.WARNING(
            "Pasos que faltan antes de mandárselo al cliente: cargar peluqueros y "
            "servicios desde /admin/, y si van a usar el bot de WhatsApp o Mercado "
            "Pago, completar esos datos en el Tenant."
        ))

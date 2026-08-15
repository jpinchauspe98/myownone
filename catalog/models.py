from django.db import models

from tenants.models import Tenant


class CategoriaServicio(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="categorias_servicio")
    nombre = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "Categorías de servicio"
        unique_together = ("tenant", "nombre")

    def __str__(self):
        return self.nombre


class Servicio(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="servicios")
    nombre = models.CharField(max_length=150)
    categoria = models.ForeignKey(
        CategoriaServicio, on_delete=models.SET_NULL, null=True, blank=True, related_name="servicios"
    )
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    duracion_min = models.PositiveIntegerField(default=30)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} (${self.precio})"


class Producto(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="productos")
    nombre = models.CharField(max_length=150)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Promocion(models.Model):
    class Tipo(models.TextChoices):
        PORCENTAJE = "porcentaje", "% de descuento"
        DOS_POR_UNO = "2x1", "2x1"
        COMBO = "combo", "Combo servicio + producto"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="promociones")
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, null=True, blank=True, related_name="promociones"
    )
    servicio = models.ForeignKey(
        Servicio, on_delete=models.CASCADE, null=True, blank=True, related_name="promociones"
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    valor = models.DecimalField(
        max_digits=6, decimal_places=2,
        help_text="% de descuento si tipo=porcentaje; sin uso en 2x1/combo",
        null=True, blank=True,
    )
    vigencia_desde = models.DateField()
    vigencia_hasta = models.DateField()
    stock = models.PositiveIntegerField(null=True, blank=True, help_text="Cupos disponibles, vacío = ilimitado")
    veces_usada = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["-vigencia_desde"]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.tenant.nombre}"

    def vigente(self):
        from django.utils import timezone
        hoy = timezone.localdate()
        return self.activo and self.vigencia_desde <= hoy <= self.vigencia_hasta

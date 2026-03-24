from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()

class AppUser(models.Model):
	class Role(models.TextChoices):
		FPO = "fpo", "FPO"
		FARMER = "farmer", "Farmer"

	user = models.OneToOneField(User, on_delete=models.CASCADE)
	role = models.CharField(max_length=20, choices=Role.choices)
	
	def __str__(self) -> str:
		return f"{self.user.username} ({self.role})"



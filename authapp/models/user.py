from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()

class AppUser(models.Model):
	class Role(models.TextChoices):
		SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
		ORG_USER = "ORG_USER", "Org User"
		FPO = "FPO", "FPO"
		FARMER = "FARMER", "FARMER"

	class PreferredLanguage(models.TextChoices):
		ENGLISH = "en", "English"
		HINDI = "hi", "Hindi"
		MARATHI = "mr", "Marathi"
		GUJARATI = "gu", "Gujarati"
		PUNJABI = "pa", "Punjabi"
		BANGLA = "bn", "Bangla"
		KANNADA = "kn", "Kannada"
		TELUGU = "te", "Telugu"
		TAMIL = "ta", "Tamil"

	user = models.OneToOneField(User, on_delete=models.CASCADE)
	role = models.CharField(max_length=20, choices=Role.choices)
	preferred_language = models.CharField(
		max_length=5,
		choices=PreferredLanguage.choices,
		default=PreferredLanguage.ENGLISH,
	)

	def __str__(self) -> str:
		return f"{self.user.username} ({self.role})"



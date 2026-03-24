from django.db import models

class Locality(models.Model):
	pin_code = models.CharField(max_length=10)
	village = models.CharField(max_length=150)
	taluka = models.CharField(max_length=150)
	district = models.CharField(max_length=150)
	state = models.CharField(max_length=150)

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=["pin_code", "village", "taluka", "district", "state"],
				name="unique_locality_combination",
			)
		]

	def __str__(self) -> str:
		return f"{self.village}, {self.district}, {self.state}"

from django.db import models
from .user import AppUser
from .locality import Locality

class FpoProfile(models.Model):
	app_user = models.OneToOneField(
		AppUser,
		on_delete=models.CASCADE,
		related_name="fpo_profile",
	)
	locality = models.ForeignKey(
		Locality,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="fpo_profiles",
	)
	fpo_name = models.CharField(max_length=255)
	contact_person_name = models.CharField(max_length=255)
	email = models.EmailField()
	mobile = models.CharField(max_length=20)
	gst_number = models.CharField(max_length=50)
	pan_number = models.CharField(max_length=50)
	cin_number = models.CharField(max_length=50)
	pan_file = models.FileField(upload_to="documents/fpo/pan/", null=True, blank=True)
	cin_file = models.FileField(upload_to="documents/fpo/cin/", null=True, blank=True)
	gst_file = models.FileField(upload_to="documents/fpo/gst/", null=True, blank=True)

	def __str__(self) -> str:
		return self.fpo_name


class FarmerProfile(models.Model):
	app_user = models.OneToOneField(
		AppUser,
		on_delete=models.CASCADE,
		related_name="farmer_profile",
	)
	locality = models.ForeignKey(
		Locality,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="farmer_profiles",
	)
	farmer_name = models.CharField(max_length=255)
	contact_number = models.CharField(max_length=20)
	email = models.EmailField(null=True, blank=True)
	registered_with_fpo = models.ForeignKey(
		FpoProfile,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="registered_farmers",
	)
	aadhaar_number = models.CharField(max_length=50)
	aadhaar_file = models.FileField(upload_to="documents/farmer/aadhaar/", null=True, blank=True)

	def __str__(self) -> str:
		return self.farmer_name

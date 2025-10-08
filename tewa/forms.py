# tewa/forms.py
# tewa/forms.py
from django import forms
from django.core.exceptions import ValidationError

from tewa.models import DefendedAsset


class DefendedAssetForm(forms.ModelForm):
    class Meta:
        model = DefendedAsset
        fields = ['name', 'lat', 'lon', 'radius_km']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter DA name'}),
            'lat': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001', 'placeholder': 'Latitude'}),
            'lon': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001', 'placeholder': 'Longitude'}),
            'radius_km': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Radius in km'}),
        }

    def clean_radius_km(self):
        radius = self.cleaned_data.get('radius_km')
        if radius is None:
            raise ValidationError('Radius is required.')
        if radius <= 0 or radius > 1000:
            raise ValidationError('Radius must be between 0 and 1000 km.')
        return radius

    def clean_lat(self):
        lat = self.cleaned_data.get('lat')
        if lat is None:
            raise ValidationError('Latitude is required.')
        if lat < -90 or lat > 90:
            raise ValidationError(
                'Latitude must be between -90 and 90 degrees.')
        return lat

    def clean_lon(self):
        lon = self.cleaned_data.get('lon')
        if lon is None:
            raise ValidationError('Longitude is required.')
        if lon < -180 or lon > 180:
            raise ValidationError(
                'Longitude must be between -180 and 180 degrees.')
        return lon


class UploadTrackForm(forms.Form):
    file = forms.FileField(required=True)
    scenario_id = forms.IntegerField(required=False)

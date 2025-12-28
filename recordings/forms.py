"""Forms for recordings app"""
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML
from .models import Recording, UserSettings


class RecordingForm(forms.ModelForm):
    """Form for uploading recording"""
    
    class Meta:
        model = Recording
        fields = ['title', 'audio_file', 'whisper_model']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название записи'}),
            'audio_file': forms.FileInput(attrs={'class': 'form-control', 'accept': 'audio/*'}),
            'whisper_model': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('title', css_class='form-group col-md-12 mb-3'),
                css_class='form-row'
            ),
            Row(
                Column('audio_file', css_class='form-group col-md-12 mb-3'),
                css_class='form-row'
            ),
            Row(
                Column('whisper_model', css_class='form-group col-md-12 mb-3'),
                css_class='form-row'
            ),
            HTML('<small class="form-text text-muted mb-3">Выберите модель Whisper для распознавания. Большие модели дают лучшее качество, но работают медленнее.</small>'),
            Submit('submit', 'Загрузить', css_class='btn btn-primary')
        )


class UserSettingsForm(forms.ModelForm):
    """Form for user settings"""
    
    class Meta:
        model = UserSettings
        fields = ['default_whisper_model', 'auto_transcribe', 'language']
        widgets = {
            'default_whisper_model': forms.Select(attrs={'class': 'form-select'}),
            'auto_transcribe': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'language': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ru'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('default_whisper_model', css_class='form-group col-md-12 mb-3'),
                css_class='form-row'
            ),
            Row(
                Column('auto_transcribe', css_class='form-group col-md-12 mb-3'),
                css_class='form-row'
            ),
            Row(
                Column('language', css_class='form-group col-md-12 mb-3'),
                css_class='form-row'
            ),
            HTML('<small class="form-text text-muted mb-3">Настройки по умолчанию для новых записей</small>'),
            Submit('submit', 'Сохранить настройки', css_class='btn btn-primary')
        )


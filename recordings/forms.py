"""Forms for recordings app"""
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML
from .models import Recording, UserSettings


class RecordingForm(forms.ModelForm):
    """Form for uploading recording"""
    
    class Meta:
        model = Recording
        fields = ['title', 'audio_file', 'recognition_service', 'whisper_model']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название записи'}),
            'audio_file': forms.FileInput(attrs={'class': 'form-control', 'accept': 'audio/*'}),
            'recognition_service': forms.Select(attrs={'class': 'form-select'}),
            'whisper_model': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Сделать whisper_model необязательным
        self.fields['whisper_model'].required = False
        
        # Примечание: vosk_model обрабатывается отдельно в view через request.POST,
        # так как оно зависит от выбранного recognition_service
        
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
                Column('recognition_service', css_class='form-group col-md-12 mb-3'),
                css_class='form-row'
            ),
            Row(
                Column('whisper_model', css_class='form-group col-md-12 mb-3'),
                css_class='form-row'
            ),
            HTML('<small class="form-text text-muted mb-3">Выберите библиотеку и модель для распознавания. Faster-Whisper работает в 4-5 раз быстрее стандартного Whisper.</small>'),
            Submit('submit', 'Загрузить', css_class='btn btn-primary')
        )


class UserSettingsForm(forms.ModelForm):
    """Form for user settings"""
    
    class Meta:
        model = UserSettings
        fields = ['default_recognition_service', 'default_whisper_model', 'default_vosk_model', 'auto_transcribe', 'language']
        widgets = {
            'default_recognition_service': forms.Select(attrs={'class': 'form-select'}),
            'default_whisper_model': forms.Select(attrs={'class': 'form-select'}),
            'default_vosk_model': forms.Select(attrs={'class': 'form-select'}),
            'auto_transcribe': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'language': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ru'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Динамически заполняем choices для default_vosk_model
        from .services.vosk_model_manager import get_model_choices
        vosk_choices = get_model_choices()
        self.fields['default_vosk_model'].choices = vosk_choices
        self.fields['default_vosk_model'].required = False
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('default_recognition_service', css_class='form-group col-md-12 mb-3'),
                css_class='form-row'
            ),
            Row(
                Column('default_whisper_model', css_class='form-group col-md-12 mb-3'),
                css_class='form-row'
            ),
            Row(
                Column('default_vosk_model', css_class='form-group col-md-12 mb-3'),
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


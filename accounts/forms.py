from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.contrib.auth.forms import UserChangeForm

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Sign Up', css_class='btn btn-success w-100'))

        # Remove help text unless field has errors
        for field_name, field in self.fields.items():
            field.help_text = ''  # Clear help text by default
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

class CustomUserEditForm(UserChangeForm):
    password = None  # Optional: hide password field

    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('staff', 'Staff'),
    )

    role = forms.ChoiceField(choices=ROLE_CHOICES, required=True)
    
    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Save Changes', css_class='btn btn-success w-100'))

        for field_name, field in self.fields.items():
            field.help_text = ''

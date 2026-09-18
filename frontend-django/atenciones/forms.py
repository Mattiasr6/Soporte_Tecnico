from django import forms


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Correo", widget=forms.EmailInput(attrs={"autofocus": True})
    )
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)

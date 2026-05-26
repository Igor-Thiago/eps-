from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import Analista, Caso, ConfiguracaoAnalista


class AnalistaRegistrationForm(forms.Form):
    nome = forms.CharField(label='Nome completo', max_length=150)
    matricula = forms.CharField(label='Matricula', max_length=20)
    senha = forms.CharField(label='Senha', widget=forms.PasswordInput)
    confirmar_senha = forms.CharField(label='Confirmar senha', widget=forms.PasswordInput)

    def clean_matricula(self):
        matricula = self.cleaned_data['matricula'].strip()
        if Analista.objects.filter(matricula=matricula).exists():
            raise forms.ValidationError('Ja existe um analista com esta matricula.')
        return matricula

    def clean(self):
        cleaned_data = super().clean()
        senha = cleaned_data.get('senha')
        confirmar_senha = cleaned_data.get('confirmar_senha')
        if senha and confirmar_senha and senha != confirmar_senha:
            raise forms.ValidationError('As senhas informadas nao conferem.')
        return cleaned_data

    def save(self):
        nome = self.cleaned_data['nome'].strip()
        partes_nome = nome.split(maxsplit=1)
        first_name = partes_nome[0]
        last_name = partes_nome[1] if len(partes_nome) > 1 else ''
        matricula = self.cleaned_data['matricula']

        return Analista.objects.create_user(
            username=matricula,
            password=self.cleaned_data['senha'],
            matricula=matricula,
            first_name=first_name,
            last_name=last_name,
        )


class CriarAdminForm(forms.Form):
    nome = forms.CharField(label='Nome completo', max_length=150)
    matricula = forms.CharField(label='Matricula', max_length=20)
    senha = forms.CharField(label='Senha', widget=forms.PasswordInput)
    confirmar_senha = forms.CharField(label='Confirmar senha', widget=forms.PasswordInput)

    def clean_matricula(self):
        matricula = self.cleaned_data['matricula'].strip()
        if Analista.objects.filter(matricula=matricula).exists():
            raise forms.ValidationError('Ja existe um usuario com esta matricula.')
        return matricula

    def clean(self):
        cleaned_data = super().clean()
        senha = cleaned_data.get('senha')
        confirmar_senha = cleaned_data.get('confirmar_senha')
        if senha and confirmar_senha and senha != confirmar_senha:
            raise forms.ValidationError('As senhas informadas nao conferem.')
        return cleaned_data

    def save(self):
        nome = self.cleaned_data['nome'].strip()
        partes = nome.split(maxsplit=1)
        matricula = self.cleaned_data['matricula']
        return Analista.objects.create_user(
            username=matricula,
            password=self.cleaned_data['senha'],
            matricula=matricula,
            first_name=partes[0],
            last_name=partes[1] if len(partes) > 1 else '',
            role=Analista.Role.ADMIN_PCDF,
            is_staff=True,
        )


class MatriculaAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label='Matricula', max_length=20)


class CasoForm(forms.Form):
    nome = forms.CharField(label='Nome do caso', max_length=255)
    numero_processo = forms.CharField(label='Numero do processo', max_length=100, required=False)
    pasta_base = forms.CharField(
        label='Pasta base personalizada',
        max_length=500,
        required=False,
        help_text='Opcional. Se vazio, sera usada a pasta padrao configurada no sistema.',
    )

    def clean_nome(self):
        nome = self.cleaned_data['nome'].strip()
        if not nome:
            raise forms.ValidationError('Informe o nome do caso.')
        return nome

    def clean_numero_processo(self):
        return self.cleaned_data.get('numero_processo', '').strip()

    def clean_pasta_base(self):
        return self.cleaned_data.get('pasta_base', '').strip()

    def save(self, analista, path_pasta):
        return Caso.objects.create(
            nome=self.cleaned_data['nome'],
            numero_processo=self.cleaned_data['numero_processo'],
            analista=analista,
            path_pasta=str(path_pasta),
        )


class ConfiguracaoForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoAnalista
        fields = [
            'pasta_padrao',
            'intervalo_screenshot',
            'logo',
            'cabecalho',
            'assinatura_nome',
            'assinatura_cargo',
            'assinatura_orgao',
            'incluir_info_tecnica',
        ]
        widgets = {
            'cabecalho': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {
            'pasta_padrao': 'Pasta padrão de salvamento',
            'intervalo_screenshot': 'Intervalo de capturas periódicas',
            'logo': 'Logo institucional (PNG/JPG, máx. 2 MB)',
            'cabecalho': 'Cabeçalho dos relatórios',
            'assinatura_nome': 'Nome do analista',
            'assinatura_cargo': 'Cargo',
            'assinatura_orgao': 'Órgão / Matrícula',
            'incluir_info_tecnica': 'Incluir seção de metadados técnicos nos relatórios',
        }

    def clean_logo(self):
        logo = self.cleaned_data.get('logo')
        if logo and hasattr(logo, 'size') and logo.size > 2 * 1024 * 1024:
            raise forms.ValidationError('O arquivo de logo não pode ultrapassar 2 MB.')
        return logo


class SiteCaptureForm(forms.Form):
    url = forms.URLField(
        label='URL do site',
        max_length=2048,
        widget=forms.URLInput(attrs={'placeholder': 'https://exemplo.com'}),
    )

    def clean_url(self):
        url = self.cleaned_data['url'].strip()
        if not url.startswith(('http://', 'https://')):
            raise forms.ValidationError('Informe uma URL HTTP ou HTTPS valida.')
        return url

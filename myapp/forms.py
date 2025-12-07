from django import forms
from .models import Question, Test
from django.contrib.auth.forms import UserCreationForm,AuthenticationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError
class QuizForm(forms.Form):
    def __init__(self, *args, **kwargs):
        questions = kwargs.pop('questions', None)
        super().__init__(*args, **kwargs)
        if questions:
            for question in questions:
                self.fields[f'question_{question.id}'] = forms.ChoiceField(
                    label=question.text,
                    choices=[
                        ('A', question.option_a),
                        ('B', question.option_b),
                        ('C', question.option_c),
                        ('D', question.option_d)
                    ],
                    widget=forms.RadioSelect
                )


class TestSelectionForm(forms.Form):
    test_id = forms.ChoiceField(choices=[], label="选择试卷")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 动态生成试卷选择列表，优先使用Test模型的试卷
        tests = Test.objects.all()
        choices = []
        
        # 如果有试卷，则添加到选项中
        if tests.exists():
            for test in tests:
                choices.append((f"paper_{test.id}", test.title))
        
        # 同时获取旧版本的test_id
        test_ids = Question.objects.values_list('test_id', flat=True).distinct()
        for tid in test_ids:
            # 过滤掉空值、temp_id和已经包含的新格式test_id
            if tid and tid != 'temp_id':
                # 检查是否已存在
                if not any(tid == existing[0] for existing in choices):
                    # 检查是否是paper_格式且与已有试卷冲突
                    paper_conflict = False
                    if tid.startswith('paper_'):
                        for test in tests:
                            if f"paper_{test.id}" == tid:
                                paper_conflict = True
                                break
                    
                    if not paper_conflict:
                        choices.append((tid, f"试卷-{tid}"))
        
        self.fields['test_id'].choices = choices
        
        # 如果没有选项，添加一个默认选项
        if not choices:
            self.fields['test_id'].choices = [('', '暂无可用试卷')]

class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        max_length=254,
        help_text=_('必填。请输入有效的电子邮箱地址。'),
        label=_('电子邮箱')
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = _('必填。150 个字符或更少。只能包含字母、数字和 @/./+/-/_。')
        self.fields['password1'].help_text = _(
            '您的密码不能与您的其他个人信息过于相似，至少包含 8 个字符，'
            '不能完全由数字组成，需要包含字母和数字的组合。'
        )
        self.fields['password2'].help_text = _('请再次输入密码，以确认您的密码。')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise ValidationError(_('两次输入的密码不匹配'))

        if password1 and len(password1) < 8:
            raise ValidationError(_('密码长度至少为8位'))

        if password1 and not any(char.isdigit() for char in password1):
            raise ValidationError(_('密码必须包含至少一个数字'))

        if password1 and not any(char.isalpha() for char in password1):
            raise ValidationError(_('密码必须包含至少一个字母'))

        # 检查密码是否与用户名相似
        if password1 and self.cleaned_data.get("username"):
            if self.cleaned_data["username"].lower() in password1.lower():
                raise ValidationError(_('密码不能与用户名相似'))

        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        return user
class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label='用户名')
    password = forms.CharField(label='密码', widget=forms.PasswordInput)
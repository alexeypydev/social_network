from django import forms

from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        # На основе какой модели создаётся класс формы
        model = Post
        # Укажем, какие поля будут в форме
        fields = ('text', 'group', 'image')

    def clean_text(self):
        data = self.cleaned_data['text']

        # Проверка "а заполнено ли поле?"
        if data == '':
            raise forms.ValidationError('Небходимо заполнить текстовое поле')

        # Метод-валидатор обязательно должен вернуть очищенные данные,
        # даже если не изменил их
        return data


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        labels = {
            'text': 'Текст комментария',
        }
        help_text = {
            'text': 'Введите свой комментарий'
        }
        fields = ('text',)

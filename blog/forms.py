from .models import Comment
from django import forms


class CommentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(CommentForm, self).__init__(*args, **kwargs)
        self.fields['content'].label = False  # "content *" 표시 없애기.

    class Meta:
        model = Comment
        fields = ('content',)
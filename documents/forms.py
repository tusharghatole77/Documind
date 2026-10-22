from django import forms
from django.conf import settings


class DocumentUploadForm(forms.Form):
    file = forms.FileField(
        label="Choose a PDF or text file",
        widget=forms.ClearableFileInput(
            attrs={"class": "form-control", "accept": ".pdf,.txt,text/plain,application/pdf"}
        ),
    )

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        if uploaded_file.size > settings.MAX_UPLOAD_BYTES:
            raise forms.ValidationError("Files must be 10 MB or smaller.")

        suffix = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
        if suffix not in {"pdf", "txt"}:
            raise forms.ValidationError("Upload a PDF or TXT file.")
        return uploaded_file

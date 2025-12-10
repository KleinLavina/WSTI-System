from django.apps import AppConfig


class SubmissionSettingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'submission_settings'

    def ready(self):
        import submission_settings.signals


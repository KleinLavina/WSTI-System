from django.apps import AppConfig

class SubmissionManagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "submission_management"

    def ready(self):
        # import signals to register them
        import submission_management.signals  # noqa: F401

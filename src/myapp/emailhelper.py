import threading

from django.conf import settings
from django.core.mail import EmailMessage


class EmailHelper:
    """
    A helper class to handle email sending in Django using Zoho SMTP.
    Implements threading for non-blocking email sending.
    """

    def _send_email(
        self,
        subject: str,
        message: str,
        recipient_list: list[str],
        from_email: str | None = None,
        html_message: str | None = None,
        attachments: list | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        connection=None,
    ) -> bool:
        """
        Internal method to handle the actual email sending
        """
        try:
            from_email = from_email or getattr(
                settings, "EMAIL_HOST_USER", "smtp.zoho.com"
            )
            email = EmailMessage(
                subject=subject,
                body=html_message if html_message else message,
                from_email=from_email,
                to=recipient_list,
                cc=cc,
                bcc=bcc,
                connection=connection,
            )

            if html_message:
                email.content_subtype = "html"

            # Add attachments if any
            if attachments:
                for attachment in attachments:
                    if isinstance(attachment, str):
                        # If attachment is a file path
                        email.attach_file(attachment)
                    elif isinstance(attachment, dict):
                        # If attachment is a dictionary with file data
                        email.attach(
                            filename=attachment["filename"],
                            content=attachment["content"],
                            mimetype=attachment["mimetype"],
                        )

            email.send(fail_silently=False)
            return True

        except Exception as e:
            print(f"Error sending email: {e!s}")
            return False

    def send_email_async(
        self,
        subject: str,
        message: str,
        recipient_list: list[str],
        from_email: str | None = None,
        html_message: str | None = None,
        attachments: list | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        connection=None,
    ) -> None:
        """
        Send email asynchronously using threading

        Args:
            subject (str): Email subject
            message (str): Plain text message
            recipient_list (List[str]): List of recipient email addresses
            from_email (Optional[str]): Sender email address. Defaults to support@template.com
            html_message (Optional[str]): HTML version of the message
            attachments (Optional[List]): List of file paths to attach
            cc (Optional[List[str]]): List of CC recipient email addresses
            bcc (Optional[List[str]]): List of BCC recipient email addresses

        """
        thread = threading.Thread(
            target=self._send_email,
            args=(subject, message, recipient_list),
            kwargs={
                "from_email": from_email,
                "html_message": html_message,
                "attachments": attachments,
                "cc": cc,
                "bcc": bcc,
                "connection": connection,
            },
        )
        thread.start()

    def send_email(
        self,
        subject: str,
        message: str,
        recipient_list: list[str],
        from_email: str | None = None,
        html_message: str | None = None,
        attachments: list | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        connection=None,
    ) -> bool:
        """
        Send email synchronously

        Args:
            subject (str): Email subject
            message (str): Plain text message
            recipient_list (List[str]): List of recipient email addresses
            from_email (Optional[str]): Sender email address. Defaults to support@template.com
            html_message (Optional[str]): HTML version of the message
            attachments (Optional[List]): List of file paths to attach
            cc (Optional[List[str]]): List of CC recipient email addresses
            bcc (Optional[List[str]]): List of BCC recipient email addresses
            connection (Optional): Email backend connection

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        return self._send_email(
            subject=subject,
            message=message,
            recipient_list=recipient_list,
            from_email=from_email,
            html_message=html_message,
            attachments=attachments,
            cc=cc,
            bcc=bcc,
            connection=connection,
        )

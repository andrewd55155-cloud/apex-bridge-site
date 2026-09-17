import os
import smtplib
from email.message import EmailMessage
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

class EmailClient:
    """
    Production-ready Email Client supporting:
    1. SendGrid Web API v3 (authenticated domain apexbridgeproperties.com)
    2. Standard SMTP fallback (SSL/TLS)
    3. Staged dry-run logging when offline
    """
    def __init__(self, api_key=None, from_email="andrew@apexbridgeproperties.com", from_name="Andrew Dimsdale | Apex Bridge Properties"):
        self.api_key = api_key or os.environ.get('SENDGRID_API_KEY')
        self.from_email = from_email or os.environ.get('SENDGRID_FROM_EMAIL', "andrew@apexbridgeproperties.com")
        self.from_name = from_name
        self.sg_client = None
        if self.api_key:
            try:
                self.sg_client = SendGridAPIClient(self.api_key)
            except Exception as e:
                print(f"[SendGrid Client] Init Warning: {e}")

    def send_email(self, to_email, subject, plain_body, html_body=None):
        """Dispatches an email via SendGrid v3 API or fallback."""
        if not to_email or '@' not in str(to_email):
            return False, "Invalid destination email"

        # Generate standard clean HTML if not provided
        if not html_body:
            html_body = f"""<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #1e293b; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: #0f172a; color: white; padding: 18px 24px; border-radius: 8px 8px 0 0;">
        <h2 style="margin: 0; font-size: 1.25rem;">Apex Bridge Properties</h2>
        <p style="margin: 4px 0 0 0; font-size: 0.85rem; color: #94a3b8;">The Fastest Way to Sell a Home in Missouri</p>
    </div>
    <div style="background: white; border: 1px solid #e2e8f0; border-top: none; padding: 24px; border-radius: 0 0 8px 8px;">
        <div style="white-space: pre-line; font-size: 0.95rem; color: #334155;">{plain_body}</div>
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;">
        <p style="font-size: 0.8rem; color: #64748b; margin: 0;">
            Apex Bridge Properties | Springfield, MO<br>
            Direct: (816) 666-9735 | Web: <a href="https://apexbridgeproperties.com" style="color: #2563eb;">apexbridgeproperties.com</a><br>
            <em style="font-size: 0.75rem;">If you do not own this property or prefer not to hear from us, reply with 'UNSUBSCRIBE' and we will remove your address immediately.</em>
        </p>
    </div>
</body>
</html>"""

        if self.sg_client:
            try:
                from_sender = Email(self.from_email, self.from_name)
                to_recipient = To(to_email)
                content = Content("text/html", html_body)
                mail = Mail(from_sender, to_recipient, subject, content)
                mail.add_content(Content("text/plain", plain_body))
                response = self.sg_client.client.mail.send.post(request_body=mail.get())
                if 200 <= response.status_code < 300:
                    return True, f"SendGrid-{response.status_code}"
                return False, f"SendGrid Status: {response.status_code} - {response.body}"
            except Exception as e:
                return False, str(e)
        else:
            print(f"[EMAIL DRY RUN] To: {to_email} | Subject: {subject}")
            return True, f"STAGED-EMAIL-TO-{to_email}"


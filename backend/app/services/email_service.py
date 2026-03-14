import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings

try:
    import dns.resolver
except ImportError:
    dns = None

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def validate_mx_record(email: str) -> bool:
        if dns is None:
            # Fallback if library is missing
            return True
        domain = email.split('@')[-1]
        try:
            # Check for MX records
            dns.resolver.resolve(domain, 'MX')
            return True
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, Exception) as e:
            logger.error(f"MX lookup failed for {domain}: {e}")
            return False

    @staticmethod
    def send_verification_email(email: str, token: str):
        # TODO: Replace with custom domain email e.g. no-reply@yourdomain.com
        sender_email = settings.GMAIL_USER
        password = settings.GMAIL_APP_PASSWORD
        
        verify_url = f"{settings.BASE_URL}/confirm/?token={token}&email={email}"
        
        message = MIMEMultipart("alternative")
        message["Subject"] = "Verify your NexaBank Account"
        message["From"] = f"NexaBank Security <{sender_email}>" # TODO: Replace with custom domain email e.g. no-reply@yourdomain.com
        message["To"] = email

        # Create the plain-text and HTML version of your message
        text = f"""
        Welcome to NexaBank!
        Please verify your account by clicking the link below:
        {verify_url}
        """
        html = f"""
        <html>
          <body style="font-family: 'Inter', sans-serif; color: #1e293b; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 40px; border: 1px solid #e2e8f0; border-radius: 24px;">
              <h2 style="color: #050811; font-weight: 800; margin-bottom: 24px;">Welcome to NexaBank</h2>
              <p>Thank you for joining NexaBank. To get started, please verify your email address by clicking the button below:</p>
              <div style="margin: 32px 0;">
                <a href="{verify_url}" style="background: #2563eb; color: #ffffff; padding: 14px 28px; border-radius: 12px; text-decoration: none; font-weight: 600; display: inline-block;">Verify My Account</a>
              </div>
              <p style="font-size: 14px; color: #64748b;">Or copy and paste this link into your browser:</p>
              <p style="font-size: 14px; color: #2563eb; word-break: break-all;">{verify_url}</p>
              <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 32px 0;">
              <p style="font-size: 12px; color: #94a3b8;">If you did not sign up for a NexaBank account, you can safely ignore this email.</p>
            </div>
          </body>
        </html>
        """

        # Turn these into plain/html MIMEText objects
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")

        # Add HTML/plain-text parts to MIMEMultipart message
        # The email client will try to render the last part first
        message.attach(part1)
        message.attach(part2)

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, password)
                server.sendmail(sender_email, email, message.as_string())
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False

email_service = EmailService()

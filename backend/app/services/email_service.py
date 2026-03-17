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

    @staticmethod
    def send_transaction_email(email: str, user_name: str, tx_type: str, amount: float, balance: float, 
                               reference: str, date_time: str, recipient_name: str = None, 
                               sender_name: str = None):
        sender_email = settings.GMAIL_USER
        password = settings.GMAIL_APP_PASSWORD

        subject = f"NexaBank — {tx_type.capitalize()} of ${amount:,.2f}"
        if tx_type == "transfer_received":
            subject = f"NexaBank — You received ${amount:,.2f}"
        elif tx_type == "transfer_sent":
            subject = f"NexaBank — You sent ${amount:,.2f}"

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"NexaBank <{sender_email}>"
        message["To"] = email

        type_label = tx_type.replace("_", " ").title()
        details_html = ""
        if tx_type == "transfer_sent" and recipient_name:
            details_html = f'<p style="margin: 0; color: #64748b;">Recipient: <strong>{recipient_name}</strong></p>'
        elif tx_type == "transfer_received" and sender_name:
            details_html = f'<p style="margin: 0; color: #64748b;">From: <strong>{sender_name}</strong></p>'

        html = f"""
        <html>
          <body style="font-family: 'Inter', sans-serif; color: #1e293b; line-height: 1.6; margin: 0; padding: 0; background-color: #f8fafc;">
            <div style="max-width: 600px; margin: 20px auto; padding: 40px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
              <div style="text-align: center; margin-bottom: 32px;">
                <h1 style="color: #0f172a; margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.025em;">NexaBank</h1>
              </div>
              
              <div style="text-align: center; margin-bottom: 32px; padding: 24px; background-color: #f1f5f9; border-radius: 12px;">
                <p style="margin: 0; font-size: 14px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">{type_label}</p>
                <p style="margin: 8px 0 0; font-size: 36px; font-weight: 800; color: #0284c7;">${amount:,.2f}</p>
              </div>

              <div style="margin-bottom: 32px;">
                <p style="margin: 0 0 16px; font-size: 16px; color: #334155;">Hello {user_name},</p>
                <p style="margin: 0 0 24px; font-size: 16px; color: #334155;">This is to confirm that a {type_label.lower()} of <strong>${amount:,.2f}</strong> has been processed on your account.</p>
                
                <div style="padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                        <span style="color: #64748b; font-size: 14px;">Reference:</span>
                        <span style="color: #0f172a; font-size: 14px; font-weight: 600;">{reference}</span>
                    </div>
                    {f'<div style="display: flex; justify-content: space-between; margin-bottom: 12px;"><span style="color: #64748b; font-size: 14px;">To:</span><span style="color: #0f172a; font-size: 14px; font-weight: 600;">{recipient_name}</span></div>' if recipient_name else ""}
                    {f'<div style="display: flex; justify-content: space-between; margin-bottom: 12px;"><span style="color: #64748b; font-size: 14px;">From:</span><span style="color: #0f172a; font-size: 14px; font-weight: 600;">{sender_name}</span></div>' if sender_name else ""}
                    <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                        <span style="color: #64748b; font-size: 14px;">New Balance:</span>
                        <span style="color: #0f172a; font-size: 14px; font-weight: 600;">${balance:,.2f}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #64748b; font-size: 14px;">Date & Time:</span>
                        <span style="color: #0f172a; font-size: 14px; font-weight: 600;">{date_time}</span>
                    </div>
                </div>
              </div>

              <div style="text-align: center; font-size: 14px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 24px;">
                <p style="margin: 0 0 8px;">If you did not authorize this transaction, please contact us immediately.</p>
                <p style="margin: 0;">© 2026 NexaBank. All rights reserved.</p>
              </div>
            </div>
          </body>
        </html>
        """

        part2 = MIMEText(html, "html")
        message.attach(part2)

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, password)
                server.sendmail(sender_email, email, message.as_string())
            return True
        except Exception as e:
            print(f"Error sending transaction email: {e}")
            return False

    @staticmethod
    def send_security_alert(email: str, user_name: str, action_type: str, timestamp: str):
        sender_email = settings.GMAIL_USER
        password = settings.GMAIL_APP_PASSWORD

        subject = f"Security Alert: NexaBank {action_type.title()} Changed"
        
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"NexaBank Security <{sender_email}>"
        message["To"] = email

        html = f"""
        <html>
          <body style="font-family: 'Inter', sans-serif; color: #1e293b; line-height: 1.6; margin: 0; padding: 0; background-color: #f8fafc;">
            <div style="max-width: 600px; margin: 20px auto; padding: 40px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
              <div style="text-align: center; margin-bottom: 32px;">
                <h1 style="color: #0f172a; margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.025em;">NexaBank Security</h1>
              </div>
              
              <div style="margin-bottom: 32px;">
                <p style="margin: 0 0 16px; font-size: 16px; color: #334155;">Hello {user_name},</p>
                <p style="margin: 0 0 24px; font-size: 16px; color: #334155;">This is an automated alert to confirm that your <strong>{action_type}</strong> has been successfully updated.</p>
                
                <div style="padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #fff7ed;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                        <span style="color: #9a3412; font-size: 14px; font-weight: 600;">Activity:</span>
                        <span style="color: #0f172a; font-size: 14px; font-weight: 600;">{action_type.title()} Update</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #9a3412; font-size: 14px; font-weight: 600;">Date & Time:</span>
                        <span style="color: #0f172a; font-size: 14px; font-weight: 600;">{timestamp}</span>
                    </div>
                </div>
              </div>

              <div style="margin-bottom: 32px;">
                 <p style="color: #ef4444; font-weight: 700; margin-bottom: 8px;">Important:</p>
                 <p style="font-size: 14px; color: #475569; margin: 0;">If you did not make this change, please contact our support team immediately or log in to your account and lock your cards.</p>
              </div>

              <div style="text-align: center; font-size: 14px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 24px;">
                <p style="margin: 0 0 8px;">© 2026 NexaBank Security. All rights reserved.</p>
              </div>
            </div>
          </body>
        </html>
        """

        part2 = MIMEText(html, "html")
        message.attach(part2)

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, password)
                server.sendmail(sender_email, email, message.as_string())
            
            # Simple log simulation
            log_path = os.path.join(os.path.dirname(__file__), "email_logs.txt")
            with open(log_path, "a") as f:
                f.write(f"\nSECURITY ALERT [{timestamp}] To: {email} | Action: {action_type}")
            
            return True
        except Exception as e:
            print(f"Error sending security email: {e}")
            return False

email_service = EmailService()

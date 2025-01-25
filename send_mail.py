import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl


def send_email(subject, body, to_email, from_email, password, smtp_server, port):
    try:
        # Create a MIMEMultipart object
        msg = MIMEMultipart()
        context = ssl.create_default_context()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject

        # Attach the email body
        msg.attach(MIMEText(body, 'plain'))

        # Connect to the SMTP server
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()  # Secure the connection
            #server.set_debuglevel(1)
            server.login(from_email, password)  # Log in to the SMTP server
            server.sendmail(from_email, to_email, msg.as_string())  # Send the email
            print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

# Example usage
if __name__ == "__main__":
    subject = "Hello from RAVI!"
    body = "This is a test email sent using Python."
    to_email = "sankojuravi2020@gmail.com"
    from_email =  "srsravi2024@gmail.com"
    password = 'wzsq updn tdin qbsy'
    smtp_server = "smtp.gmail.com"
    port = 587  # For TLS

    send_email(subject, body, to_email, from_email, password, smtp_server, port)

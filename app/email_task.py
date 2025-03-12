from mailersend import emails
from celery import shared_task
import time
import markdown

from sms.settings import mailersend_token, email_from


@shared_task(name="send_email_with_mailersend")
def send_email(
        name: str,
        email: str,
        subject: str,
        text: str,
) -> str:

    mailer = emails.NewEmail(mailersend_token)

    mail_body = {}

    mail_from = {
        "name": "OquLabs",
        "email": email_from,
    }

    recipients = [
        {
            "name": name,
            "email": email,
        }
    ]

    reply_to = [
        {
            "name": "Delicatest",
            "email": "info@dsacademy.kz",
        }
    ]

    # make a simple html out of text using markdown
    html = f"""
    <HTML>
        <body>
            {markdown.markdown(text)}
        </body>
    </HTML>
    """

    mailer.set_mail_from(mail_from, mail_body)
    mailer.set_mail_to(recipients, mail_body)
    mailer.set_subject(subject, mail_body)
    mailer.set_html_content(html, mail_body)
    mailer.set_plaintext_content(text, mail_body)
    mailer.set_reply_to(reply_to, mail_body)

    while True:
        print("Sending email to:", email)
        result = mailer.send(mail_body)
        results = result.split("\n", maxsplit=1)
        code = int(results[0])
        result = result[1]
        if int(code) == 202:
            return f"Sent an email to {email}"
        elif int(code) == 429:
            time.sleep(30)
        else:
            return f"Something went wrong: {email}, result: {result}"

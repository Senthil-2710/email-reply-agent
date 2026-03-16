import imaplib
import smtplib
import email
import time
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime

try:
    from google import genai
except ImportError:
    os.system("pip install google-genai")
    from google import genai


GMAIL_ADDRESS     = "senthilvj2001@gmail.com"         
GMAIL_APP_PASSWORD = "drdj fwwh qerx hcor"  
GEMINI_API_KEY    = "AIzaSyAE1xmL5InnCpFHYm6_NN0dOZC95VmIVyk"  

MY_NAME = "Senthil"
MY_INFO = """
I am Senthil, a software developer from Chennai, India.
I work on Angular, AI, and web development projects.
I am available Monday to Friday, 9 AM to 6 PM IST.
For urgent matters people can reach me on email.
"""

IGNORE_SENDERS = [
    "no-reply", "noreply", "donotreply",
    "newsletter", "notification",
    "mailer-daemon", "postmaster",
]

REPLIED_FILE = "replied_emails.txt"


def load_replied():
    if os.path.exists(REPLIED_FILE):
        with open(REPLIED_FILE, "r") as f:
            return set(f.read().splitlines())
    return set()


def save_replied(message_id):
    with open(REPLIED_FILE, "a") as f:
        f.write(message_id + "\n")


def should_ignore(sender):
    sender_lower = sender.lower()
    for ignore in IGNORE_SENDERS:
        if ignore in sender_lower:
            return True
    return False


def decode_subject(subject):
    decoded = decode_header(subject)
    parts = []
    for part, encoding in decoded:
        if isinstance(part, bytes):
            parts.append(part.decode(encoding or "utf-8", errors="ignore"))
        else:
            parts.append(part)
    return " ".join(parts)


def get_email_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    break
                except:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
        except:
            pass
    return body[:2000]


def generate_reply(sender_name, sender_email, subject, body):
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
You are {MY_NAME}. Here is some info about you:
{MY_INFO}

Someone sent you an email. Write a professional, friendly and helpful reply.

Sender name: {sender_name}
Sender email: {sender_email}
Email subject: {subject}
Email content:
{body}

Rules for your reply:
- Keep it short and clear (3-5 sentences)
- Be friendly and professional
- Sign off as {MY_NAME}
- Do NOT include subject line in reply
- Do NOT use placeholder text like [your name]
- Reply naturally as if you are {MY_NAME}

Write only the reply text, nothing else.
"""
    response = client.models.generate_content(
        model="gemini-2.0-flash-lite",
        contents=prompt
    )
    return response.text.strip()


def send_reply(to_email, to_name, subject, reply_text, original_message_id):
    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = f"Re: {subject}"
    msg["In-Reply-To"] = original_message_id
    msg["References"] = original_message_id
    msg.attach(MIMEText(reply_text, "plain"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, to_email, msg.as_string())


def check_and_reply_emails():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking emails...")
    replied = load_replied()
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        mail.select("inbox")
        status, messages = mail.search(None, "UNSEEN")
        if status != "OK" or not messages[0]:
            print("  No new emails!")
            mail.logout()
            return
        email_ids = messages[0].split()
        print(f"  Found {len(email_ids)} new email(s)!")
        for email_id in email_ids:
            try:
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                message_id = msg.get("Message-ID", "").strip()
                sender = msg.get("From", "")
                subject = decode_subject(msg.get("Subject", "No Subject"))
                body = get_email_body(msg)
                if "<" in sender:
                    sender_name = sender.split("<")[0].strip().strip('"')
                    sender_email = sender.split("<")[1].strip(">")
                else:
                    sender_name = sender
                    sender_email = sender
                print(f"\n  From    : {sender_name} <{sender_email}>")
                print(f"  Subject : {subject}")
                if message_id and message_id in replied:
                    print("  Skipping — already replied!")
                    continue
                if should_ignore(sender_email):
                    print("  Skipping — ignored sender!")
                    continue
                if not body.strip():
                    print("  Skipping — empty email!")
                    continue
                print("  Generating AI reply...")
                reply_text = generate_reply(sender_name, sender_email, subject, body)
                print(f"  Reply preview: {reply_text[:100]}...")
                send_reply(sender_email, sender_name, subject, reply_text, message_id)
                print("  Reply sent successfully!")
                if message_id:
                    save_replied(message_id)
            except Exception as e:
                print(f"  Error processing email: {e}")
        mail.logout()
    except Exception as e:
        print(f"  Connection error: {e}")


def main():
    print("=" * 50)
    print("  Email Auto Reply Agent Started!")
    print("=" * 50)
    print(f"  Gmail     : {GMAIL_ADDRESS}")
    print(f"  Checking  : Every 2 minutes")
    print(f"  AI Model  : Gemini 2.0 Flash")
    print("=" * 50)
    check_and_reply_emails()
    while True:
        time.sleep(60)
        check_and_reply_emails()


if __name__ == "__main__":
    main()

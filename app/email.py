from flask_mail import Message
from flask import render_template, current_app
from app import mail


def send_password_reset_email(user):
    token = user.get_reset_password_token()
    msg = Message(
        "[mBlog] Reset Your Password",
        sender=current_app.config["ADMINS"][0],
        recipients=[user.email],
    )

    # We will create this text file in Step 4!
    msg.body = render_template("email/reset_password.txt", user=user, token=token)
    mail.send(msg)

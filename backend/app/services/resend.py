import httpx

from app.core.config import get_settings


class ResendDeliveryError(RuntimeError):
    pass


def _send_code_email(
    *,
    recipient: str,
    subject: str,
    html: str,
) -> None:
    settings = get_settings()
    if not settings.resend_api_key or not settings.resend_from_email:
        raise ResendDeliveryError("Resend email service is not configured")

    payload = {
        "from": settings.resend_from_email,
        "to": [recipient],
        "subject": subject,
        "html": html,
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
    except (httpx.HTTPError, ValueError) as error:
        raise ResendDeliveryError("Resend email delivery failed") from error


def send_password_reset_code_email(*, recipient: str, code: str) -> None:
    _send_code_email(
        recipient=recipient,
        subject="Climbing Log 비밀번호 재설정 인증번호",
        html=(
            "<p>Climbing Log 비밀번호 재설정 인증번호입니다.</p>"
            f"<p><strong>{code}</strong></p>"
            "<p>인증번호는 5분 동안 유효합니다.</p>"
            "<p>본인이 요청하지 않았다면 이 이메일을 무시해 주세요.</p>"
        ),
    )


def send_email_verification_code_email(*, recipient: str, code: str) -> None:
    _send_code_email(
        recipient=recipient,
        subject="Climbing Log 이메일 인증번호",
        html=(
            "<p>Climbing Log 회원가입 이메일 인증번호입니다.</p>"
            f"<p><strong>{code}</strong></p>"
            "<p>인증번호는 10분 동안 유효합니다.</p>"
            "<p>본인이 요청하지 않았다면 이 이메일을 무시해 주세요.</p>"
        ),
    )

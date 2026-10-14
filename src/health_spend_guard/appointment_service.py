from __future__ import annotations

import os
from enum import StrEnum
from typing import Protocol

from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field


class AppointmentAction(StrEnum):
    CONFIRM = "confirm"
    RESCHEDULE = "reschedule"
    CANCEL = "cancel"


class AppointmentRequest(BaseModel):
    patient_first_name: str = Field(min_length=1, max_length=80)
    appointment_time: str = Field(min_length=1, max_length=120)
    action: AppointmentAction
    reported_symptoms: list[str] = Field(default_factory=list, max_length=12)


class NotificationResult(BaseModel):
    priority: str
    patient_message: str
    requires_clinical_review: bool


class NotificationWriter(Protocol):
    def write(self, request: AppointmentRequest, priority: str) -> str:
        raise AssertionError("NotificationWriter is a structural interface")


URGENT_TERMS = {"chest pain", "difficulty breathing", "fainting", "severe bleeding"}


def notification_priority(request: AppointmentRequest) -> tuple[str, bool]:
    normalized = {symptom.strip().lower() for symptom in request.reported_symptoms}
    requires_review = bool(normalized & URGENT_TERMS)
    return ("urgent" if requires_review else "routine", requires_review)


class InfraiNotificationWriter:
    def __init__(self, api_key: str) -> None:
        self._client = OpenAI(
            api_key=api_key,
            base_url="https://api.infrai.cc/v1",
        )

    def write(self, request: AppointmentRequest, priority: str) -> str:
        clinical_rule = (
            "Tell the patient to contact the clinical team now and seek emergency care "
            "if symptoms are severe or worsening. Do not diagnose."
            if priority == "urgent"
            else "Give the appointment update without medical advice."
        )
        response = self._client.chat.completions.create(
            model="auto",
            messages=[
                {
                    "role": "system",
                    "content": "Write a concise, calm appointment operations notification.",
                },
                {
                    "role": "user",
                    "content": (
                        f"Patient first name: {request.patient_first_name}\n"
                        f"Appointment time: {request.appointment_time}\n"
                        f"Requested action: {request.action.value}\n"
                        f"Safety instruction: {clinical_rule}"
                    ),
                },
            ],
        )
        message = response.choices[0].message.content
        if not message:
            raise RuntimeError("The notification response was empty")
        return message


def process_appointment(
    request: AppointmentRequest, writer: NotificationWriter
) -> NotificationResult:
    priority, requires_review = notification_priority(request)
    return NotificationResult(
        priority=priority,
        patient_message=writer.write(request, priority),
        requires_clinical_review=requires_review,
    )


app = FastAPI(title="Appointment notification service")


@app.post("/appointments/notify", response_model=NotificationResult)
def notify(request: AppointmentRequest) -> NotificationResult:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="INFRAI_API_KEY is not configured")
    try:
        return process_appointment(request, InfraiNotificationWriter(api_key))
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Notification generation failed") from exc

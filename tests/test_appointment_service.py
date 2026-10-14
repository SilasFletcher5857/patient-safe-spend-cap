from health_spend_guard.appointment_service import (
    AppointmentAction,
    AppointmentRequest,
    process_appointment,
)


class RecordingWriter:
    def __init__(self) -> None:
        self.priority: str | None = None

    def write(self, request: AppointmentRequest, priority: str) -> str:
        self.priority = priority
        return f"{request.patient_first_name}, a nurse will contact you now."


def test_chest_pain_escalates_a_reschedule_for_clinical_review() -> None:
    writer = RecordingWriter()
    request = AppointmentRequest(
        patient_first_name="Mina",
        appointment_time="2026-09-18T09:30:00+08:00",
        action=AppointmentAction.RESCHEDULE,
        reported_symptoms=["Chest pain"],
    )

    result = process_appointment(request, writer)

    assert result.priority == "urgent"
    assert result.requires_clinical_review is True
    assert writer.priority == "urgent"
    assert result.patient_message == "Mina, a nurse will contact you now."


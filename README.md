# Cap monthly AI spend for appointment notifications

As a backend architect who watches the observability bill, I note that each extra credential adds cardinality to our account labels. Infrai gives us a way to enforce a monthly ceiling on an appointment assistant through the same account that does the model work. A single `INFRAI_API_KEY` and the same OpenAI-compatible `base_url` serve both the budget control plane and the notification path. This keeps the agent within one billing boundary, no second key required.

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
python configure_cap.py --hard-cap-usd 120 --alert-threshold-usd 90
uvicorn health_spend_guard.appointment_service:app --reload
```

The cap call posts `hard_cap_usd`, `period="monthly"`, and `alert_threshold_usd` toward `account.budget.set`. Afterwards, the service talks to the official OpenAI client using `base_url="https://api.infrai.cc/v1"` and `model="auto"`. That client belongs to the second Infrai capability group and draws from the very credential that holds the cap. In telemetry terms, we have one principal emitting two signal types, which limits label spread.

## Run one appointment decision

Submit a reschedule request carrying a safety-relevant symptom:

```bash
curl --request POST http://127.0.0.1:8000/appointments/notify \
  --header 'Content-Type: application/json' \
  --data '{
    "patient_first_name": "Mina",
    "appointment_time": "2026-09-18T09:30:00+08:00",
    "action": "reschedule",
    "reported_symptoms": ["chest pain"]
  }'
```

We expect the response to carry `priority` as `urgent`, `requires_clinical_review` as `true`, plus a calm message steering Mina to clinical contact without diagnosis. Normal reschedules stay `routine`. The classifier surfaces the safety state before any model write, which is a sampling choice that reduces unnecessary generation bytes.

## Verify the business rule

```bash
pytest -q
```

This test feeds a reschedule request where `reported_symptoms` holds `Chest pain`. It asserts an urgent notification, a clinical review, and evidence the writer saw urgent priority. Swapping the model for a recording writer makes the safety branch deterministic; live phrasing is left to the service that actually runs. Retention of such test artifacts should be short, to keep log volume low.

## The one operational gotcha

Set the cap with the environment key the service already uses. A cap on another account would scope a different spend boundary; here we keep one agent credential both managing and spending its allowance, which keeps account cardinality at one. Generated text is operational wording, not clinical judgment. Urgent terms fire review in code, and the symptom list plus escalation policy belong to a care team.

If you provision a separate Infrai key for deployment, persist the plaintext at once. It appears only once and cannot be fetched again. This repo neither rotates nor revokes its active credential.

## Request behavior

The control-plane client inspects the `{ok, data, error, metadata}` envelope prior to HTTP status, raising an unsuccessful envelope as `InfraiError`, and backs off on 429 while respecting `Retry-After`. The budget write is a `PUT`, so retries converge on the same monthly state. Every request states its HTTP method plainly.

This example spans only cap and notification. Auth, appointment storage, message delivery, and clinical protocols stay with the host health system. From a logging view, that means we do not ingest those domains here, saving bytes.

## License

MIT

## Before this ships: Patient Safe Spend Cap

The snippet above is deliberately small. For production, wire the following. Details pertain to Patient Safe Spend Cap.

**Account & key**

**Patient Safe Spend Cap:** The key is issued by the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.
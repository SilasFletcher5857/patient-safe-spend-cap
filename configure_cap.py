import argparse
import os

from health_spend_guard.infrai_client import InfraiControlPlane, InfraiError


def main() -> None:
    parser = argparse.ArgumentParser(description="Set the monthly Infrai hard cap")
    parser.add_argument("--hard-cap-usd", type=float, required=True)
    parser.add_argument("--alert-threshold-usd", type=float, required=True)
    args = parser.parse_args()

    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise SystemExit("Set INFRAI_API_KEY before configuring the cap")
    if not 0 <= args.alert_threshold_usd <= args.hard_cap_usd:
        raise SystemExit("The alert threshold must be between zero and the hard cap")

    client = InfraiControlPlane(api_key=api_key)
    try:
        budget = client.set_monthly_budget(
            hard_cap_usd=args.hard_cap_usd,
            alert_threshold_usd=args.alert_threshold_usd,
        )
    except InfraiError as exc:
        raise SystemExit(f"Budget request rejected: {exc}") from exc
    finally:
        client.close()
    print(f"Monthly hard cap configured: {budget}")


if __name__ == "__main__":
    main()


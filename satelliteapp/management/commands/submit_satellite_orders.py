import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from satelliteapp.services.order_submit import submit_fpos


class Command(BaseCommand):
    help = "Create IrriWatch orders for all eligible farms of the given FPOs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fpo-ids",
            nargs="+",
            type=int,
            required=True,
            help="FpoProfile ids whose farms should be submitted.",
        )
        parser.add_argument(
            "--months",
            type=int,
            required=True,
            help="Subscription duration (months) for newly created subscriptions.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=50,
            help="Max farms per IrriWatch order (default 50).",
        )
        parser.add_argument(
            "--company-uuid",
            default=settings.IRRIWATCH_ORDER_COMPANY_UUID,
            help="IrriWatch company uuid (defaults to IRRIWATCH_ORDER_COMPANY_UUID).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Build payloads and report skips without creating anything or calling IrriWatch.",
        )
        parser.add_argument(
            "--output",
            help="Dry run only: write the order payload(s) to this JSON file.",
        )

    def handle(self, *args, **options):
        if options["months"] < 1:
            raise CommandError("--months must be at least 1")
        if options["batch_size"] < 1:
            raise CommandError("--batch-size must be at least 1")

        dry_run = options["dry_run"]
        self.stdout.write(
            f"{'DRY RUN: ' if dry_run else ''}Submitting FPOs {options['fpo_ids']} "
            f"to company {options['company_uuid']} "
            f"(months={options['months']}, batch_size={options['batch_size']})"
        )

        try:
            reports = submit_fpos(
                options["fpo_ids"],
                options["company_uuid"],
                options["months"],
                batch_size=options["batch_size"],
                dry_run=dry_run,
            )
        except ValueError as exc:
            raise CommandError(str(exc))

        for report in reports:
            self._print_report(report, dry_run)

        if dry_run and options["output"]:
            payloads = {r["fpo"]: r["payloads"] for r in reports}
            with open(options["output"], "w") as fh:
                json.dump(payloads, fh, indent=2)
            self.stdout.write(f"Payloads written to {options['output']}")

    def _print_report(self, report, dry_run):
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n== {report['fpo']} =="))

        if dry_run:
            count = sum(len(p["features"]) for p in report["payloads"])
            self.stdout.write(
                self.style.SUCCESS(
                    f"Would submit {count} farms in {len(report['payloads'])} order(s)"
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"Submitted: {len(report['submitted'])} farms"))
            self.stdout.write(f"Orders created: {report['orders']}")
            if report["unmapped"]:
                self.stdout.write(
                    self.style.WARNING(
                        f"Submitted but field uuid not mapped ({len(report['unmapped'])}): "
                        f"{report['unmapped']}"
                    )
                )
            for farm_id, reason in report["failed"]:
                self.stdout.write(self.style.ERROR(f"FAILED farm {farm_id}: {reason}"))

        self.stdout.write(f"Skipped: {len(report['skipped'])} farms")
        for farm_id, reason in report["skipped"]:
            self.stdout.write(f"  farm {farm_id}: {reason}")

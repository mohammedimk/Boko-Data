# """Seeds ServicePlan with CheapDataHub's published Data & Cable TV plan IDs and prices."""
# from decimal import Decimal

# from django.core.management.base import BaseCommand

# from core.models import ServicePlan, ServiceCommission

# # (network, plan_id, name, price) — Data plans
# DATA_PLANS = [
#     ('AIRTEL', '70', '1GB (Social Bundle) Gifting (3 Days)', '295.0'),
#     ('AIRTEL', '13', '500MB Gifting (7 days)', '490.0'),
#     ('AIRTEL', '69', '1.5GB Gifting (1 Day)', '500.0'),
#     ('AIRTEL', '66', '1.5GB Gifting (2 Days)', '599.0'),
#     ('AIRTEL', '15', '1GB Gifting (7 Days)', '800.0'),
#     ('AIRTEL', '17', '2GB Gifting (30 Days)', '1490.0'),
#     ('AIRTEL', '52', '5GB Gifting (7 Days)', '1570.0'),
#     ('AIRTEL', '18', '3GB Gifting (30 Days)', '1960.0'),
#     ('AIRTEL', '22', '6GB SME (7 Days)', '2455.0'),
#     ('AIRTEL', '19', '4GB Gifting (30 Days)', '2570.0'),
#     ('AIRTEL', '20', '8GB Gifting (30 Days)', '2999.0'),
#     ('AIRTEL', '21', '10GB Gifting (30 Days)', '4070.0'),
#     ('GLO', '42', '200MB corprate gifting (1 Day)', '92.0'),
#     ('GLO', '35', '500MB corprate gifting (30 Days)', '225.0'),
#     ('GLO', '68', '1GB corprate gifting (3 Days)', '300.0'),
#     ('GLO', '36', '1GB corprate gifting (30 Days)', '425.0'),
#     ('GLO', '41', '1GB Gifting (14 Days)', '485.0'),
#     ('GLO', '40', '2GB corprate gifting (30 Days)', '850.0'),
#     ('GLO', '37', '3GB corprate gifting (30 Days)', '1300.0'),
#     ('GLO', '54', '5GB corprate gifting (7 Days)', '1699.0'),
#     ('GLO', '38', '5GB corprate gifting (30 Days)', '2250.0'),
#     ('GLO', '39', '10GB corprate gifting (30 Days)', '4390.0'),
#     ('GLO', '59', '20.5GB Gifting (30 Days)', '5300.0'),
#     ('GLO', '58', '107GB Gifting (30 Days)', '19300.0'),
#     ('MTN', '43', '110MB Gifting (1 Day)', '99.0'),
#     ('MTN', '74', '230MB Gifting (1 Day)', '200.0'),
#     ('MTN', '76', '500MB SME (2 Days)', '250.0'),
#     ('MTN', '78', '1GB SME (1Day)', '270.0'),
#     ('MTN', '81', '1GB corprate gifting (30 Days)', '280.0'),
#     ('MTN', '44', '500MB SME (30 Days)', '350.0'),
#     ('MTN', '77', '1GB SME (2 Days)', '399.0'),
#     ('MTN', '45', '1GB SME (7 Days)', '450.0'),
#     ('MTN', '46', '1GB SME (30 Days)', '570.0'),
#     ('MTN', '79', '2.5GB SME (1 Day)', '600.0'),
#     ('MTN', '27', '2.5GB Gifting (2 Days)', '900.0'),
#     ('MTN', '71', '2GB Gifting (7 Days)', '900.0'),
#     ('MTN', '47', '2GB SME (7 Days)', '930.0'),
#     ('MTN', '60', '4.5GB Gifting (1 Day)', '1050.0'),
#     ('MTN', '48', '2GB SME (30 Days)', '1150.0'),
#     ('MTN', '61', '4GB Gifting (2 Days)', '1175.0'),
#     ('MTN', '80', '5GB corprate gifting (14 Days)', '1299.0'),
#     ('MTN', '82', '5GB SME (30 Days)', '1299.0'),
#     ('MTN', '49', '3GB SME (30 Days)', '1370.0'),
#     ('MTN', '50', '5GB SME (30 Days)', '2050.0'),
#     ('MTN', '53', '6GB Gifting (7 Days)', '2495.0'),
#     ('MTN', '33', '7GB Gifting (30 Days)', '3499.0'),
#     ('MTN', '55', '11GB Gifting (7 Days)', '3550.0'),
#     ('MTN', '67', '10GB Gifting (30 Days)', '4800.0'),
#     ('MTN', '57', '36GB Gifting (30 Days)', '10800.0'),
#     ('MTN', '51', '75GB SME (30 Days)', '17990.0'),
# ]

# # (network, plan_id, name, price) — Cable TV bouquets
# CABLE_PLANS = [
#     ('DSTV', '8', 'DStv Compact', '19000'),
#     ('DSTV', '9', 'DStv Compact Plus', '30000'),
#     ('DSTV', '7', 'DStv Confam', '11000'),
#     ('DSTV', '3', 'DStv Padi', '4400'),
#     ('DSTV', '10', 'DStv Premium', '44500'),
#     ('DSTV', '6', 'DStv Yanga', '6000'),
#     ('GOTV', '11', 'GOtv Jinja', '3900'),
#     ('GOTV', '12', 'Gotv Jolli', '5800'),
#     ('GOTV', '13', 'GOtv Max', '8500'),
#     ('GOTV', '4', 'GOtv Smallie-monthly', '1900'),
#     ('GOTV', '14', 'GOtv Supa', '11400'),
#     ('GOTV', '15', 'GOtv Supa Plus', '16800'),
#     ('STARTIMES', '18', 'Basic (Antenna) -1 Week', '1400'),
#     ('STARTIMES', '20', 'Basic (Antenna)- 1 month', '4000'),
#     ('STARTIMES', '19', 'Basic (Dish) - 1 week', '1700'),
#     ('STARTIMES', '21', 'Basic (dish) - 1Month', '5100'),
#     ('STARTIMES', '22', 'Classic (Dish) - 1 Week', '2500'),
#     ('STARTIMES', '23', 'Classic (Dish) -1 Month', '7400'),
#     ('STARTIMES', '17', 'Nova (Antenna) - 1 Month', '2100'),
#     ('STARTIMES', '5', 'Nova (antenna) -1 week', '700'),
#     ('STARTIMES', '16', 'Nova (Dish) - 1 Week', '700'),
#     ('STARTIMES', '25', 'Super (Antenna) - 1 week', '3200'),
#     ('STARTIMES', '26', 'Super (Antenna) -1 Month', '9500'),
#     ('STARTIMES', '24', 'Super (Dish) - 1 Week', '3300'),
# ]


# class Command(BaseCommand):
#     help = "Seed ServicePlan with CheapDataHub's Data & Cable plan IDs/prices, and default commissions."

#     def handle(self, *args, **options):
#         created_count = 0
#         for network, plan_id, name, cost in DATA_PLANS:
#             _, created = ServicePlan.objects.update_or_create(
#                 service=ServicePlan.Service.DATA, network=network, provider_plan_id=plan_id,
#                 defaults={'name': name, 'cost_price': Decimal(cost)},
#             )
#             created_count += created

#         for network, plan_id, name, cost in CABLE_PLANS:
#             _, created = ServicePlan.objects.update_or_create(
#                 service=ServicePlan.Service.CABLE, network=network, provider_plan_id=plan_id,
#                 defaults={'name': name, 'cost_price': Decimal(cost)},
#             )
#             created_count += created

#         ServiceCommission.objects.get_or_create(service=ServiceCommission.Service.AIRTIME, defaults={'commission_percent': Decimal('3.00')})
#         ServiceCommission.objects.get_or_create(service=ServiceCommission.Service.ELECTRICITY, defaults={'commission_percent': Decimal('1.50')})

#         self.stdout.write(self.style.SUCCESS(
#             f"Seeded {len(DATA_PLANS) + len(CABLE_PLANS)} plans ({created_count} new/updated)."
#         ))




import re
from decimal import Decimal
from django.core.management.base import BaseCommand
from core.models import ServicePlan  # Adjust import if your app is named differently


DATA_PLANS_RAW = """
70 | airtel | 1GB (Social Bundle) | 3 Days | ₦350.0 | ₦330.0 | ₦295.0
13 | airtel | 500MB | 7 days | ₦500.0 | ₦495.0 | ₦490.0
69 | airtel | 1.5GB | 1 Day | ₦530.0 | ₦520.0 | ₦500.0
66 | airtel | 1.5GB | 2 Days | ₦650.0 | ₦630.0 | ₦599.0
15 | airtel | 1GB | 7 Days | ₦1000.0 | ₦800.0 | ₦800.0
17 | airtel | 2GB | 30 Days | ₦1550.0 | ₦1550.0 | ₦1490.0
52 | airtel | 5GB | 7 Days | ₦1599.0 | ₦1575.0 | ₦1570.0
18 | airtel | 3GB | 30 Days | ₦2100.0 | ₦1999.0 | ₦1960.0
22 | airtel | 6GB | 7 Days | ₦2599.0 | ₦2495.0 | ₦2455.0
19 | airtel | 4GB | 30 Days | ₦2650.0 | ₦2599.0 | ₦2570.0
20 | airtel | 8GB | 30 Days | ₦3200.0 | ₦3100.0 | ₦2999.0
21 | airtel | 10GB | 30 Days | ₦4200.0 | ₦4099.0 | ₦4070.0
42 | glo | 200 MB | 1 Day | ₦100.0 | ₦95.0 | ₦92.0
35 | glo | 500MB | 30 Days | ₦250.0 | ₦230.0 | ₦225.0
68 | glo | 1GB | 3 Days | ₦350.0 | ₦300.0 | ₦300.0
36 | glo | 1GB | 30 Days | ₦450.0 | ₦430.0 | ₦425.0
41 | glo | 1GB | 14 Days | ₦500.0 | ₦490.0 | ₦485.0
40 | glo | 2GB | 30 Days | ₦900.0 | ₦850.0 | ₦850.0
37 | glo | 3GB | 30 Days | ₦1500.0 | ₦1300.0 | ₦1300.0
54 | glo | 5GB | 7 Days | ₦1800.0 | ₦1750.0 | ₦1699.0
38 | glo | 5GB | 30 Days | ₦2400.0 | ₦2300.0 | ₦2250.0
39 | glo | 10GB | 30 Days | ₦4500.0 | ₦4399.0 | ₦4390.0
59 | glo | 20.5GB | 30 Days | ₦6000.0 | ₦5500.0 | ₦5300.0
58 | glo | 107GB | 30 Days | ₦20000.0 | ₦19500.0 | ₦19300.0
43 | mtn | 110MB | 1 Day | ₦100.0 | ₦99.0 | ₦99.0
74 | mtn | 230MB | 1 Day | ₦250.0 | ₦230.0 | ₦200.0
76 | mtn | 500MB | 2 Days | ₦270.0 | ₦270.0 | ₦250.0
78 | mtn | 1GB | 1Day | ₦300.0 | ₦300.0 | ₦270.0
81 | mtn | 1 GB | 30 Days | ₦350.0 | ₦350.0 | ₦280.0
44 | mtn | 500MB | 30 Days | ₦400.0 | ₦390.0 | ₦350.0
77 | mtn | 1GB | 2 Days | ₦450.0 | ₦440.0 | ₦399.0
45 | mtn | 1GB | 7 Days | ₦499.0 | ₦450.0 | ₦450.0
46 | mtn | 1GB | 30 Days | ₦600.0 | ₦570.0 | ₦570.0
79 | mtn | 2.5GB | 1 Day | ₦650.0 | ₦650.0 | ₦600.0
47 | mtn | 2GB | 7 Days | ₦950.0 | ₦930.0 | ₦930.0
27 | mtn | 2.5GB | 2 Days | ₦1000.0 | ₦950.0 | ₦900.0
71 | mtn | 2GB | 7 Days | ₦1000.0 | ₦950.0 | ₦900.0
60 | mtn | 4.5GB | 1 Day | ₦1100.0 | ₦1100.0 | ₦1050.0
48 | mtn | 2GB | 30 Days | ₦1250.0 | ₦1199.0 | ₦1150.0
61 | mtn | 4GB | 2 Days | ₦1300.0 | ₦1200.0 | ₦1175.0
82 | mtn | 5GB | 30 Days | ₦1500.0 | ₦1400.0 | ₦1299.0
80 | mtn | 5GB | 14 Days | ₦1500.0 | ₦1400.0 | ₦1299.0
49 | mtn | 3GB | 30 Days | ₦1500.0 | ₦1399.0 | ₦1370.0
50 | mtn | 5GB | 30 Days | ₦2300.0 | ₦2099.0 | ₦2050.0
53 | mtn | 6GB | 7 Days | ₦2600.0 | ₦2500.0 | ₦2495.0
33 | mtn | 7GB | 30 Days | ₦3599.0 | ₦3550.0 | ₦3499.0
55 | mtn | 11GB | 7 Days | ₦3600.0 | ₦3600.0 | ₦3550.0
67 | mtn | 10GB | 30 Days | ₦5000.0 | ₦4900.0 | ₦4800.0
57 | mtn | 36GB | 30 Days | ₦11000.0 | ₦10900.0 | ₦10800.0
51 | mtn | 75GB | 30 Days | ₦18500.0 | ₦17999.0 | ₦17990.0
"""

CABLE_PLANS_RAW = """
3 | DSTV | DStv Padi | ₦4400
4 | GOTV | GOtv Smallie-monthly | ₦1900
5 | STARTIMES | Nova (antenna) -1 week | ₦700
6 | DSTV | DStv Yanga | ₦6000
7 | DSTV | DStv Confam | ₦11000
8 | DSTV | DStv Compact | ₦19000
9 | DSTV | DStv Compact Plus | ₦30000
10 | DSTV | DStv Premium | ₦44500
11 | GOTV | GOtv Jinja | ₦3900
12 | GOTV | Gotv Jolli | ₦5800
13 | GOTV | GOtv Max | ₦8500
14 | GOTV | GOtv Supa | ₦11400
15 | GOTV | GOtv Supa Plus | ₦16800
16 | STARTIMES | Nova (Dish) - 1 Week | ₦700
17 | STARTIMES | Nova (Antenna) - 1 Month | ₦2100
18 | STARTIMES | Basic (Antenna) -1 Week | ₦1400
19 | STARTIMES | Basic (Dish) - 1 week | ₦1700
20 | STARTIMES | Basic (Antenna)- 1 month | ₦4000
21 | STARTIMES | Basic (dish) - 1Month | ₦5100
22 | STARTIMES | Classic (Dish) - 1 Week | ₦2500
23 | STARTIMES | Classic (Dish) -1 Month | ₦7400
24 | STARTIMES | Super (Dish) - 1 Week | ₦3300
25 | STARTIMES | Super (Antenna) - 1 week | ₦3200
26 | STARTIMES | Super (Antenna) -1 Month | ₦9500
"""


def clean_price(val: str) -> Decimal:
    """Strips currency signs, commas, and converts string to Decimal."""
    cleaned = re.sub(r"[^\d.]", "", val)
    return Decimal(cleaned) if cleaned else Decimal("0.00")


class Command(BaseCommand):
    help = "Populates database with Data and Cable TV ServicePlan records."

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        # --- 1. Process Data Plans ---
        data_lines = [
            line.strip()
            for line in DATA_PLANS_RAW.strip().split("\n")
            if line.strip()
        ]
        for line in data_lines:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 7:
                continue

            provider_plan_id = parts[0]
            network = parts[1].upper()
            size = parts[2]
            validity = parts[3]
            api_price_raw = parts[6]  # Column 7 is CheapDataHub API Price

            plan_name = f"{size} ({validity})"
            cost_price = clean_price(api_price_raw)

            _, created = ServicePlan.objects.update_or_create(
                service=ServicePlan.Service.DATA,
                network=network,
                provider_plan_id=provider_plan_id,
                defaults={
                    "name": plan_name,
                    "validity": validity,
                    "cost_price": cost_price,
                    "is_active": True,
                },
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        # --- 2. Process Cable TV Plans ---
        cable_lines = [
            line.strip()
            for line in CABLE_PLANS_RAW.strip().split("\n")
            if line.strip()
        ]
        for line in cable_lines:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 4:
                continue

            provider_plan_id = parts[0]
            network = parts[1].upper()
            plan_name = parts[2]
            price_raw = parts[3]

            cost_price = clean_price(price_raw)

            # Extract validity if present inside brackets or string
            validity = ""
            validity_match = re.search(
                r"(\d+\s*(?:Week|Month|Day)s?)", plan_name, re.IGNORECASE
            )
            if validity_match:
                validity = validity_match.group(1)

            _, created = ServicePlan.objects.update_or_create(
                service=ServicePlan.Service.CABLE,
                network=network,
                provider_plan_id=provider_plan_id,
                defaults={
                    "name": plan_name,
                    "validity": validity,
                    "cost_price": cost_price,
                    "is_active": True,
                },
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeding complete! {created_count} plans created, {updated_count} updated."
            )
        )
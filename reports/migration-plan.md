# Migration plan: Kestrel Ridge Mutual

## Executive summary

Kestrel Ridge Mutual runs 250 applications on 941 servers in its data center. Flow analysis found 340 application dependencies, 89 of which were missing from the CMDB, plus 2 servers that are not in the inventory at all. The 6R rules place the portfolio as 109 replatform, 75 rehost, 29 retire, 27 repurchase, 7 refactor, 3 retain. People overrode 1 of those decisions.

The migration runs in 14 monthly waves from Jan 2027 to Feb 2028, starting with a low risk pilot. Waves were built to keep chatty dependencies together: cross-wave traffic is 380 weight units against 2,992 for a plan by business unit, 87.3% less. The shared claims database cuts over in wave 3 with replication running before it.

One time migration cost is $7.4M. After the program, run cost is $2.9M a year lower than staying. Five year NPV of the change is $3.4M. Break-even is in month 39 (2030-03-01).

The register holds 136 risks, 36 of them high. The largest: R-001 Claims Data Hub serves 26 migrating apps (6 of them not in the CMDB); 18 cut over in a different wave than the database (score 20); R-002 3 apps talk to 10.88.14.40 on port 445, an address that is not in the CMDB (2 GB in 14 days) (score 16); R-003 4 apps talk to 10.88.14.21 on port 1433, an address that is not in the CMDB (65 GB in 14 days) (score 16).

## Wave comparison

| Plan | Cross-wave traffic (weight/day) | Of which shared DB | Split dependencies | Latency sensitive splits | WAN GB during migration | vs by business unit |
|---|---|---|---|---|---|---|
| Graph partitioning (greedy merge + refinement) | 380 | 181 | 67 of 235 | 22 | 28,922 | -87% |
| Alphabetical | 2,926 | 248 | 208 of 235 | 81 | 181,404 | -2% |
| By business unit | 2,992 | 376 | 194 of 235 | 71 | 102,381 | baseline |

Cross-wave traffic is the edge weight (GB per day plus 1 per 10,000 connections per day) between apps in different waves. WAN GB multiplies each split edge's daily volume by the months between its two waves.

## Waves

| Wave | Month | Apps | Effort | Servers | Notes |
|---|---|---|---|---|---|
| 1 | Jan 2027 | 3 | 5 of 10 | 11 | pilot |
| 2 | Feb 2027 | 15 | 28 of 34 | 56 |  |
| 3 | Mar 2027 | 18 | 29 of 34 | 62 | Claims Data Hub cutover |
| 4 | Apr 2027 | 22 | 33.5 of 34 | 85 |  |
| 5 | May 2027 | 19 | 29 of 34 | 73 |  |
| 6 | Jun 2027 | 20 | 31 of 34 | 64 |  |
| 7 | Jul 2027 | 18 | 29 of 34 | 71 |  |
| 8 | Aug 2027 | 13 | 19 of 34 | 47 |  |
| 9 | Sep 2027 | 16 | 28.5 of 34 | 66 |  |
| 10 | Oct 2027 | 9 | 20 of 34 | 36 |  |
| 11 | Nov 2027 | 14 | 27 of 34 | 49 |  |
| 12 | Dec 2027 | 18 | 28.5 of 34 | 70 |  |
| 13 | Jan 2028 | 20 | 32 of 34 | 73 |  |
| 14 | Feb 2028 | 12 | 20 of 34 | 47 |  |

- **Wave 1 (Jan 2027)**: Repair Network Viewer (rehost), Job Scheduler Viewer (replatform), File Transfer Service (replatform)
- **Wave 2 (Feb 2027)**: Auto Quote Sync (rehost), Auto Quote Hub (rehost), Renewal Service (rehost), Underwriting Rules Workbench (replatform), Life Illustration Service (replatform), Tax Sync (replatform), Reinsurance Gateway (replatform), Lead Routing Engine (replatform), Agency Contract API (replatform), Lead Routing Loader (repurchase), Agency Contract Hub (replatform), Commission Sync (replatform), Identity Sync Tracker (repurchase), Identity Sync API (refactor), Identity Sync Engine (replatform)
- **Wave 3 (Mar 2027)**: Submission Sync (replatform), Exposure Portal (repurchase), Loss Control Portal (replatform), Risk Survey API (replatform), Salvage Console (rehost), First Notice Hub (replatform), Medical Bill Gateway (rehost), Fraud Score Calculator (repurchase), Repair Network Gateway (replatform), Repair Network Calculator (replatform), Subrogation Batch (rehost), Commission Split Service (rehost), Annuity Payout Service (replatform), Beneficiary Gateway (replatform), Lead Routing API (replatform), Lead Routing Hub (rehost), Producer Licensing API (replatform), Lead Routing Reporting (rehost)
- **Wave 4 (Apr 2027)**: Discount API (replatform), Submission Workbench (replatform), Fleet Rating Calculator (rehost), Claim Payment Console (rehost), Reserve Gateway (replatform), Reserve Hub (rehost), Reserve Loader (replatform), Medical Bill Console (rehost), Beneficiary Portal (replatform), Medical Underwriting Service (rehost), Tax Batch (repurchase), General Ledger Viewer (replatform), Tax Tracker (rehost), Commission Console (replatform), Agency Contract Tracker (rehost), Marketing Campaign Loader (replatform), Service Desk Tracker (replatform), Service Desk Gateway (rehost), File Transfer Viewer (repurchase), File Transfer Gateway (rehost), Service Desk Workbench (repurchase), Identity Sync Service (replatform)
- **Wave 5 (May 2027)**: Reserve Calculator (rehost), First Notice Console (replatform), Salvage Sync (rehost), Salvage Batch (replatform), Medical Bill Tracker (repurchase), Adjuster Console (replatform), Salvage Reporting (rehost), Claim Payment Loader (replatform), Expense Hub (replatform), Statutory Reporting Viewer (rehost), Lead Routing Workbench (rehost), Producer Licensing Loader (replatform), Producer Licensing Sync (replatform), Agent Portal Calculator (rehost), Producer Licensing Reporting (rehost), Identity Sync Batch (replatform), Document Archive Workbench (rehost), Job Scheduler Loader (repurchase), Document Archive Hub (replatform)
- **Wave 6 (Jun 2027)**: Home Rating Service (replatform), Policy Issuance Console (rehost), Telematics Calculator (rehost), Coverage Selector Viewer (replatform), Telematics Workbench (replatform), First Notice Service (replatform), First Notice Reporting (replatform), Catastrophe Gateway (repurchase), First Notice Tracker (rehost), Adjuster Calculator (replatform), General Ledger Portal (repurchase), Reinsurance Viewer (rehost), Reinsurance API (replatform), Accounts Payable Reporting (rehost), Statutory Reporting Batch (replatform), Commission Portal (rehost), Agent Portal Loader (replatform), Commission Workbench (replatform), Benefits Sync (rehost), Time Entry Tracker (rehost)
- **Wave 7 (Jul 2027)**: Loss Control Service (replatform), Medical Underwriting Console (rehost), Beneficiary Tracker (rehost), Medical Underwriting Workbench (rehost), Medical Underwriting Portal (replatform), Expense Engine (repurchase), Premium Accounting Viewer (rehost), Expense Service (rehost), Reinsurance Engine (repurchase), Reinsurance Workbench (rehost), Accounts Payable Tracker (replatform), Loss Triangle Workbench (refactor), Pricing Model Hub (replatform), Learning Viewer (rehost), Time Entry Gateway (repurchase), Email Archive Loader (replatform), Identity Sync Gateway (replatform), Print Stream Viewer (repurchase)
- **Wave 8 (Aug 2027)**: Discount Console (rehost), Endorsement API (repurchase), Underwriting Rules Calculator (rehost), Policy Issuance Sync (rehost), Billing Plan Loader (replatform), Risk Survey Sync (rehost), Workers Comp Sync (replatform), Annuity Payout Sync (rehost), Commission Split Sync (replatform), Medical Underwriting Batch (replatform), Premium Accounting Calculator (rehost), Premium Accounting Gateway (repurchase), Premium Accounting Workbench (replatform)
- **Wave 9 (Sep 2027)**: Billing Plan Gateway (rehost), Submission Calculator (rehost), Bond Portal (replatform), Exposure Tracker (replatform), Broker Quote Calculator (replatform), Policy Loan Viewer (rehost), Beneficiary Calculator (replatform), Reinsurance Hub (rehost), Tax Viewer (replatform), Tax Engine (replatform), Statutory Reporting Console (repurchase), Cash Management Reporting (repurchase), Premium Accounting Hub (replatform), Pricing Model Service (refactor), Capital Model Console (replatform), Loss Triangle Console (repurchase)
- **Wave 10 (Oct 2027)**: Billing Plan API (refactor), Underwriting Rules Service (replatform), Underwriting Rules Gateway (repurchase), Loss Control Viewer (replatform), Workers Comp Viewer (rehost), Loss Triangle Hub (refactor), Capital Model Hub (replatform), Experience Study Hub (replatform), Learning Service (repurchase)
- **Wave 11 (Nov 2027)**: Endorsement Console (rehost), Home Rating Calculator (replatform), Endorsement Calculator (replatform), Billing Plan Portal (replatform), Exposure Hub (replatform), Bond Gateway (replatform), Repair Network Portal (rehost), Repair Network Tracker (replatform), Reserve Reporting (replatform), Medical Bill Service (rehost), Subrogation Tracker (rehost), Experience Study Viewer (rehost), Experience Study Gateway (refactor), Pricing Model Gateway (refactor)
- **Wave 12 (Dec 2027)**: Auto Quote Tracker (repurchase), Discount Loader (replatform), Auto Quote API (replatform), Renewal Hub (repurchase), Billing Plan Sync (repurchase), Renewal Calculator (repurchase), Bond Service (replatform), Fleet Rating Viewer (rehost), Fleet Rating Gateway (rehost), Fleet Rating Loader (rehost), Medical Bill Calculator (repurchase), Catastrophe Engine (replatform), Subrogation Gateway (replatform), Repair Network Hub (replatform), Pricing Model Calculator (rehost), Capital Model Engine (replatform), Pricing Model API (rehost), Benefits Batch (replatform)
- **Wave 13 (Jan 2028)**: Underwriting Rules Engine (replatform), Home Rating Portal (replatform), Endorsement Batch (rehost), Underwriting Rules Viewer (replatform), Telematics Viewer (replatform), Home Rating Viewer (replatform), Renewal Viewer (rehost), Coverage Selector Reporting (replatform), Risk Survey Workbench (replatform), Catastrophe API (rehost), Adjuster Batch (replatform), Subrogation Hub (rehost), Catastrophe Tracker (replatform), First Notice Gateway (rehost), Fraud Score Batch (replatform), Life Illustration Loader (rehost), Annuity Payout Portal (rehost), Life Illustration Engine (replatform), Recruiting Batch (rehost), Benefits Console (replatform)
- **Wave 14 (Feb 2028)**: Auto Quote Portal (replatform), Endorsement Workbench (replatform), Endorsement Viewer (rehost), Underwriting Rules Loader (replatform), Billing Plan Calculator (rehost), Renewal Console (rehost), Exposure Console (replatform), Workers Comp Console (replatform), Submission Batch (replatform), Workers Comp Gateway (rehost), Annuity Payout API (replatform), Commission Split Loader (replatform)

Not moving: 29 retired, 3 retained.

## Portfolio (6R)

| App | Strategy | Wave | Main reason |
|---|---|---|---|
| APP-001 Home Rating Service | replatform | 6 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-002 Auto Quote Sync | rehost | 2 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-003 Discount API | replatform | 4 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-004 Discount Console | rehost | 8 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-005 Endorsement Console | rehost | 11 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-006 Policy Issuance Console | rehost | 6 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-007 Underwriting Rules Engine | replatform | 13 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-008 Telematics Calculator | rehost | 6 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-009 Coverage Selector Viewer | replatform | 6 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-010 Auto Quote Portal | replatform | 14 | RHEL 6 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-011 Home Rating Portal | replatform | 13 | Windows Server 2012 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-012 Billing Plan API | refactor | 10 | High value (5/5), 50 deploys a year, and the team runs containers today |
| APP-013 Underwriting Rules Service | replatform | 10 | Oracle 19c can move to a managed database service, which removes patching and some license cost |
| APP-014 Auto Quote Tracker | repurchase | 12 | Off the shelf product (LearnGrid) with a SaaS edition from the vendor |
| APP-015 Endorsement Batch | rehost | 13 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-016 Endorsement Workbench | replatform | 14 | Windows Server 2012 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-017 Telematics API | retain |  | Makes online MQ calls to the mainframe on every transaction; keep it next to the mainframe for now |
| APP-018 Home Rating Calculator | replatform | 11 | RHEL 6 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-019 Discount Loader | replatform | 12 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-020 Endorsement API | repurchase | 8 | Off the shelf product (ServiceLoop ITSM) with a SaaS edition from the vendor |
| APP-021 Underwriting Rules Calculator | rehost | 8 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-022 Coverage Selector Batch | retire |  | Does the same job as Telematics Viewer and has only 27 monthly users |
| APP-023 Billing Plan Gateway | rehost | 9 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-024 Auto Quote API | replatform | 12 | SQL Server 2014 can move to a managed database service, which removes patching and some license cost |
| APP-025 Endorsement Calculator | replatform | 11 | SQL Server 2019 can move to a managed database service, which removes patching and some license cost |
| APP-026 Renewal Sync | retire |  | Windows Server 2012 R2 is past end of support and only 10 people use it a month |
| APP-027 Endorsement Viewer | rehost | 14 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-028 Underwriting Rules Gateway | repurchase | 10 | Off the shelf product (ExpensePilot) with a SaaS edition from the vendor |
| APP-029 Telematics Workbench | replatform | 6 | SQL Server 2019 can move to a managed database service, which removes patching and some license cost |
| APP-030 Auto Quote Hub | rehost | 2 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-031 Underwriting Rules Loader | replatform | 14 | SQL Server 2014 can move to a managed database service, which removes patching and some license cost |
| APP-032 Underwriting Rules Viewer | replatform | 13 | Windows Server 2012 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-033 Telematics Viewer | replatform | 13 | RHEL 6 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-034 Coverage Selector Service | retire |  | Does the same job as Underwriting Rules Service and has only 22 monthly users |
| APP-035 Coverage Selector Tracker | retire |  | AIX 7.1 is past end of support and only 33 people use it a month |
| APP-036 Home Rating Viewer | replatform | 13 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-037 Renewal Viewer | rehost | 13 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-038 Billing Plan Calculator | rehost | 14 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-039 Renewal Service | rehost | 2 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-040 Policy Issuance Sync | rehost | 8 | Stable (4 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-041 Renewal Hub | repurchase | 12 | Off the shelf product (LearnGrid) with a SaaS edition from the vendor |
| APP-042 Renewal Console | rehost | 14 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-043 Billing Plan Sync | repurchase | 12 | Off the shelf product (ArchiveVault) with a SaaS edition from the vendor |
| APP-044 Billing Plan Portal | replatform | 11 | Solaris 10 on proprietary hardware has no like for like cloud target; it has to be ported to Linux |
| APP-045 Underwriting Rules Workbench | replatform | 2 | SQL Server 2014 can move to a managed database service, which removes patching and some license cost |
| APP-046 Billing Plan Loader | replatform | 8 | SQL Server 2019 can move to a managed database service, which removes patching and some license cost |
| APP-047 Coverage Selector Reporting | replatform | 13 | SQL Server 2019 can move to a managed database service, which removes patching and some license cost |
| APP-048 Renewal Calculator | repurchase | 12 | Off the shelf product (ExpensePilot) with a SaaS edition from the vendor |
| APP-049 Submission Calculator | rehost | 9 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-050 Bond Service | replatform | 12 | SQL Server 2019 can move to a managed database service, which removes patching and some license cost |
| APP-051 Risk Survey Calculator | retire |  | No change in 5.6 years, 21 monthly users, nothing calls it |
| APP-052 Exposure Sync | retire |  | No change in 4.1 years, 42 monthly users, nothing calls it |
| APP-053 Exposure Workbench | retire |  | No change in 6.4 years, 17 monthly users, nothing calls it |
| APP-054 Bond Console | retire |  | Solaris 10 is past end of support and only 37 people use it a month |
| APP-055 Exposure Hub | replatform | 11 | RHEL 6 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-056 Submission Sync | replatform | 3 | AIX 7.1 on proprietary hardware has no like for like cloud target; it has to be ported to Linux |
| APP-057 Submission Workbench | replatform | 4 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-058 Exposure Console | replatform | 14 | Oracle 12c can move to a managed database service, which removes patching and some license cost |
| APP-059 Risk Survey Sync | rehost | 8 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-060 Exposure Portal | repurchase | 3 | Off the shelf product (TalentDesk) with a SaaS edition from the vendor |
| APP-061 Fleet Rating Viewer | rehost | 12 | Vendor product (DocuForge) without SaaS; the vendor supports the same install on cloud VMs |
| APP-062 Submission Engine | retire |  | Windows Server 2012 R2 is past end of support and only 36 people use it a month |
| APP-063 Workers Comp Sync | replatform | 8 | SQL Server 2019 can move to a managed database service, which removes patching and some license cost |
| APP-064 Submission API | retire |  | RHEL 7 is past end of support and only 30 people use it a month |
| APP-065 Bond Portal | replatform | 9 | RHEL 6 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-066 Fleet Rating Calculator | rehost | 4 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-067 Loss Control Viewer | replatform | 10 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-068 Exposure Calculator | retire |  | Does the same job as Submission Workbench and has only 32 monthly users |
| APP-069 Exposure Tracker | replatform | 9 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-070 Loss Control Portal | replatform | 3 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-071 Loss Control Service | replatform | 7 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-072 Fleet Rating Gateway | rehost | 12 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-073 Workers Comp Viewer | rehost | 10 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-074 Risk Survey Workbench | replatform | 13 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-075 Broker Quote Console | retire |  | Windows Server 2008 R2 is past end of support and only 35 people use it a month |
| APP-076 Workers Comp Console | replatform | 14 | Windows Server 2012 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-077 Fleet Rating Loader | rehost | 12 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-078 Submission Batch | replatform | 14 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-079 Broker Quote Calculator | replatform | 9 | SQL Server 2014 can move to a managed database service, which removes patching and some license cost |
| APP-080 Bond Gateway | replatform | 11 | SQL Server 2014 can move to a managed database service, which removes patching and some license cost |
| APP-081 Risk Survey API | replatform | 3 | Windows Server 2012 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-082 Workers Comp Gateway | rehost | 14 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-083 Salvage Console | rehost | 3 | Rehost is the default and no rule scored higher |
| APP-084 Medical Bill Calculator | repurchase | 12 | Off the shelf product (ArchiveVault) with a SaaS edition from the vendor |
| APP-085 Reserve Calculator | rehost | 5 | Rehost is the default and no rule scored higher |
| APP-086 Claim Payment Console | rehost | 4 | Rehost is the default and no rule scored higher |
| APP-087 Catastrophe API | rehost | 13 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-088 Adjuster Batch | replatform | 13 | RHEL 6 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-089 Subrogation Hub | rehost | 13 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-090 Reserve Gateway | replatform | 4 | Solaris 10 on proprietary hardware has no like for like cloud target; it has to be ported to Linux |
| APP-091 Catastrophe Tracker | replatform | 13 | Windows Server 2012 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-092 First Notice Hub | replatform | 3 | AIX 7.1 on proprietary hardware has no like for like cloud target; it has to be ported to Linux |
| APP-093 First Notice Gateway | rehost | 13 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-094 Medical Bill Gateway | rehost | 3 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-095 Repair Network Viewer | rehost | 1 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-096 First Notice Console | replatform | 5 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-097 Fraud Score Console | retire |  | Windows Server 2012 R2 is past end of support and only 14 people use it a month |
| APP-098 First Notice Service | replatform | 6 | SQL Server 2014 can move to a managed database service, which removes patching and some license cost |
| APP-099 Salvage Sync | rehost | 5 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-100 Salvage Batch | replatform | 5 | Windows Server 2012 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-101 Catastrophe Engine | replatform | 12 | AIX 7.1 on proprietary hardware has no like for like cloud target; it has to be ported to Linux |
| APP-102 Medical Bill Tracker | repurchase | 5 | Off the shelf product (ExpensePilot) with a SaaS edition from the vendor |
| APP-103 Adjuster Service | retire |  | Does the same job as Repair Network Viewer and has only 37 monthly users |
| APP-104 Repair Network Portal | rehost | 11 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-105 Subrogation Gateway | replatform | 12 | Solaris 10 on proprietary hardware has no like for like cloud target; it has to be ported to Linux |
| APP-106 First Notice Reporting | replatform | 6 | SQL Server 2019 can move to a managed database service, which removes patching and some license cost |
| APP-107 Repair Network Tracker | replatform | 11 | AIX 7.1 on proprietary hardware has no like for like cloud target; it has to be ported to Linux |
| APP-108 Reserve Reporting | replatform | 11 | Windows Server 2008 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-109 Fraud Score Calculator | repurchase | 3 | Off the shelf product (ServiceLoop ITSM) with a SaaS edition from the vendor |
| APP-110 Catastrophe Gateway | repurchase | 6 | Off the shelf product (CampaignCraft) with a SaaS edition from the vendor |
| APP-111 Repair Network Hub | replatform | 12 | SQL Server 2019 can move to a managed database service, which removes patching and some license cost |
| APP-112 Claim Payment Viewer | retire |  | Does the same job as Salvage Batch and has only 29 monthly users |
| APP-113 First Notice Tracker | rehost | 6 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-114 Adjuster Console | replatform | 5 | SQL Server 2019 can move to a managed database service, which removes patching and some license cost |
| APP-115 Reserve Hub | rehost | 4 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-116 Reserve Loader | replatform | 4 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-117 Medical Bill Console | rehost | 4 | Rehost is the default and no rule scored higher |
| APP-118 Repair Network Gateway | replatform | 3 | SQL Server 2008 can move to a managed database service, which removes patching and some license cost |
| APP-119 Fraud Score Batch | replatform | 13 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-120 Salvage Reporting | rehost | 5 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-121 Adjuster Calculator | replatform | 6 | SQL Server 2019 can move to a managed database service, which removes patching and some license cost |
| APP-122 Claim Payment Loader | replatform | 5 | Windows Server 2012 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-123 Medical Bill Service | rehost | 11 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-124 Repair Network Calculator | replatform | 3 | Solaris 10 on proprietary hardware has no like for like cloud target; it has to be ported to Linux |
| APP-125 Subrogation Tracker | rehost | 11 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-126 Subrogation Batch | rehost | 3 | Rehost is the default and no rule scored higher |
| APP-127 Policy Loan Engine | retire |  | No change in 5.2 years, 10 monthly users, nothing calls it |
| APP-128 Medical Underwriting Console | rehost | 7 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-129 Medical Underwriting Loader | retire |  | Does the same job as Annuity Payout API and has only 17 monthly users |
| APP-130 Policy Loan Viewer | rehost | 9 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-131 Commission Split Hub | retire |  | RHEL 7 is past end of support and only 25 people use it a month |
| APP-132 Annuity Payout Sync | rehost | 8 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-133 Commission Split Sync | replatform | 8 | Oracle 12c can move to a managed database service, which removes patching and some license cost |
| APP-134 Beneficiary Tracker | rehost | 7 | Rehost is the default and no rule scored higher |
| APP-135 Beneficiary Portal | replatform | 4 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-136 Life Illustration Loader | rehost | 13 | Rehost is the default and no rule scored higher |
| APP-137 Medical Underwriting Workbench | rehost | 7 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-138 Commission Split Service | rehost | 3 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-139 Beneficiary Calculator | replatform | 9 | SQL Server 2014 can move to a managed database service, which removes patching and some license cost |
| APP-140 Medical Underwriting Portal | replatform | 7 | Windows Server 2008 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-141 Annuity Payout Portal | rehost | 13 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-142 Medical Underwriting Batch | replatform | 8 | Solaris 10 on proprietary hardware has no like for like cloud target; it has to be ported to Linux |
| APP-143 Annuity Payout Service | replatform | 3 | Windows Server 2008 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-144 Annuity Payout API | replatform | 14 | AIX 7.1 on proprietary hardware has no like for like cloud target; it has to be ported to Linux |
| APP-145 Annuity Payout Loader | retire |  | No change in 5.3 years, 34 monthly users, nothing calls it |
| APP-146 Life Illustration Engine | replatform | 13 | Solaris 10 on proprietary hardware has no like for like cloud target; it has to be ported to Linux |
| APP-147 Beneficiary Gateway | replatform | 3 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-148 Commission Split Loader | replatform | 14 | Oracle 11g can move to a managed database service, which removes patching and some license cost |
| APP-149 Life Illustration Service | replatform | 2 | AIX 7.1 on proprietary hardware has no like for like cloud target; it has to be ported to Linux |
| APP-150 Medical Underwriting Service | rehost | 4 | Rehost is the default and no rule scored higher |
| APP-151 General Ledger Portal | repurchase | 6 | Off the shelf product (LearnGrid) with a SaaS edition from the vendor |
| APP-152 Tax Batch | repurchase | 4 | Off the shelf product (ExpensePilot) with a SaaS edition from the vendor |
| APP-153 Reinsurance Hub | rehost | 9 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-154 Reinsurance Viewer | rehost | 6 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-155 Premium Accounting Calculator | rehost | 8 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-156 Tax Sync | replatform | 2 | Windows Server 2012 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-157 Tax Viewer | replatform | 9 | RHEL 6 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-158 Reinsurance API | replatform | 6 | SQL Server 2019 can move to a managed database service, which removes patching and some license cost |
| APP-159 Premium Accounting Gateway | repurchase | 8 | Off the shelf product (PayFlex HR) with a SaaS edition from the vendor |
| APP-160 General Ledger Reporting | retire |  | No change in 4.4 years, 29 monthly users, nothing calls it |
| APP-161 Expense Engine | repurchase | 7 | Off the shelf product (PayFlex HR) with a SaaS edition from the vendor |
| APP-162 Premium Accounting Workbench | replatform | 8 | Windows Server 2012 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-163 General Ledger Viewer | replatform | 4 | Windows Server 2012 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-164 Premium Accounting Viewer | rehost | 7 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-165 Accounts Payable Reporting | rehost | 6 | Vendor product (RateSmith) without SaaS; the vendor supports the same install on cloud VMs |
| APP-166 Expense Service | rehost | 7 | Vendor product (LedgerWorks) without SaaS; the vendor supports the same install on cloud VMs |
| APP-167 Reinsurance Engine | repurchase | 7 | Off the shelf product (CampaignCraft) with a SaaS edition from the vendor |
| APP-168 Tax Engine | replatform | 9 | SQL Server 2008 can move to a managed database service, which removes patching and some license cost |
| APP-169 Expense Hub | replatform | 5 | Windows Server 2012 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-170 Tax Tracker | rehost | 4 | Vendor product (ReinsureOne) without SaaS; the vendor supports the same install on cloud VMs |
| APP-171 Reinsurance Gateway | replatform | 2 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-172 Statutory Reporting Viewer | rehost | 5 | Vendor product (ReinsureOne) without SaaS; the vendor supports the same install on cloud VMs |
| APP-173 Reinsurance Workbench | rehost | 7 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-174 Statutory Reporting Console | repurchase | 9 | Off the shelf product (ExpensePilot) with a SaaS edition from the vendor |
| APP-175 Cash Management Reporting | repurchase | 9 | Off the shelf product (LearnGrid) with a SaaS edition from the vendor |
| APP-176 Premium Accounting Hub | replatform | 9 | SQL Server 2008 can move to a managed database service, which removes patching and some license cost |
| APP-177 Statutory Reporting Batch | replatform | 6 | Windows Server 2012 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-178 Tax Service | retire |  | RHEL 7 is past end of support and only 44 people use it a month |
| APP-179 Accounts Payable Console | retire |  | Does the same job as Premium Accounting Viewer and has only 29 monthly users |
| APP-180 Accounts Payable Tracker | replatform | 7 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-181 Lead Routing API | replatform | 3 | Windows Server 2008 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-182 Lead Routing Workbench | rehost | 5 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-183 Lead Routing Engine | replatform | 2 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-184 Lead Routing Hub | rehost | 3 | Vendor product (ReinsureOne) without SaaS; the vendor supports the same install on cloud VMs |
| APP-185 Commission Console | replatform | 4 | SQL Server 2014 can move to a managed database service, which removes patching and some license cost |
| APP-186 Agency Contract API | replatform | 2 | SQL Server 2008 can move to a managed database service, which removes patching and some license cost |
| APP-187 Agency Contract Tracker | rehost | 4 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-188 Lead Routing Loader | repurchase | 2 | Off the shelf product (LearnGrid) with a SaaS edition from the vendor |
| APP-189 Commission Gateway | retire |  | RHEL 6 is past end of support and only 30 people use it a month |
| APP-190 Agency Contract Hub | replatform | 2 | Windows Server 2012 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-191 Producer Licensing API | replatform | 3 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-192 Marketing Campaign Loader | replatform | 4 | SQL Server 2014 can move to a managed database service, which removes patching and some license cost |
| APP-193 Commission Portal | rehost | 6 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-194 Agent Portal Loader | replatform | 6 | SQL Server 2019 can move to a managed database service, which removes patching and some license cost |
| APP-195 Producer Licensing Loader | replatform | 5 | Windows Server 2012 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-196 Commission Sync | replatform | 2 | SQL Server 2014 can move to a managed database service, which removes patching and some license cost |
| APP-197 Producer Licensing Sync | replatform | 5 | SQL Server 2019 can move to a managed database service, which removes patching and some license cost |
| APP-198 Agent Portal Calculator | rehost | 5 | Rehost is the default and no rule scored higher |
| APP-199 Marketing Campaign Reporting | retire |  | Does the same job as Commission Workbench and has only 7 monthly users |
| APP-200 Commission Workbench | replatform | 6 | Windows Server 2008 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-201 Agency Contract Batch | retain |  | Tied to the agent portal contract renewal in 2028; revisit then (override by Enterprise architecture board) |
| APP-202 Producer Licensing Reporting | rehost | 5 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-203 Agent Portal API | retire |  | Windows Server 2012 R2 is past end of support and only 42 people use it a month |
| APP-204 Lead Routing Reporting | rehost | 3 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-205 Experience Study Viewer | rehost | 11 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-206 Loss Triangle Workbench | refactor | 7 | High value (5/5), 17 deploys a year, and the team runs containers today |
| APP-207 Loss Triangle Hub | refactor | 10 | High value (5/5), 25 deploys a year, and the team runs containers today |
| APP-208 Pricing Model Service | refactor | 9 | High value (4/5), 43 deploys a year, and the team runs containers today |
| APP-209 Experience Study Gateway | refactor | 11 | High value (4/5), 12 deploys a year, and the team runs containers today |
| APP-210 Pricing Model Gateway | refactor | 11 | High value (5/5), 34 deploys a year, and the team runs containers today |
| APP-211 Pricing Model Calculator | rehost | 12 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-212 Capital Model Hub | replatform | 10 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-213 Capital Model Console | replatform | 9 | Windows Server 2008 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-214 Capital Model Engine | replatform | 12 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-215 Experience Study Hub | replatform | 10 | SQL Server 2019 can move to a managed database service, which removes patching and some license cost |
| APP-216 Pricing Model API | rehost | 12 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-217 Pricing Model Hub | replatform | 7 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-218 Loss Triangle Console | repurchase | 9 | Off the shelf product (ServiceLoop ITSM) with a SaaS edition from the vendor |
| APP-219 Learning Viewer | rehost | 7 | Vendor product (RateSmith) without SaaS; the vendor supports the same install on cloud VMs |
| APP-220 Benefits Sync | rehost | 6 | Vendor product (ClaimsVision 8) without SaaS; the vendor supports the same install on cloud VMs |
| APP-221 Benefits Batch | replatform | 12 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-222 Benefits API | retire |  | RHEL 7 is past end of support and only 45 people use it a month |
| APP-223 Recruiting Engine | retire |  | No change in 6.4 years, 30 monthly users, nothing calls it |
| APP-224 Time Entry Gateway | repurchase | 7 | Off the shelf product (PayFlex HR) with a SaaS edition from the vendor |
| APP-225 Recruiting Batch | rehost | 13 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-226 Time Entry Tracker | rehost | 6 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-227 Learning Service | repurchase | 10 | Off the shelf product (ExpensePilot) with a SaaS edition from the vendor |
| APP-228 Benefits Console | replatform | 13 | SQL Server 2014 can move to a managed database service, which removes patching and some license cost |
| APP-229 Email Archive Loader | replatform | 7 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-230 Identity Sync Batch | replatform | 5 | Solaris 10 on proprietary hardware has no like for like cloud target; it has to be ported to Linux |
| APP-231 Job Scheduler Viewer | replatform | 1 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-232 Identity Sync Gateway | replatform | 7 | Windows Server 2012 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-233 Service Desk Tracker | replatform | 4 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-234 Print Stream Viewer | repurchase | 7 | Off the shelf product (LearnGrid) with a SaaS edition from the vendor |
| APP-235 Service Desk Gateway | rehost | 4 | Vendor product (LedgerWorks) without SaaS; the vendor supports the same install on cloud VMs |
| APP-236 File Transfer Viewer | repurchase | 4 | Off the shelf product (PayFlex HR) with a SaaS edition from the vendor |
| APP-237 File Transfer Gateway | rehost | 4 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-238 Document Archive Workbench | rehost | 5 | Stable (0 deploys a year) on a supported OS; lift and shift is the cheapest move |
| APP-239 Job Scheduler Loader | repurchase | 5 | Off the shelf product (CampaignCraft) with a SaaS edition from the vendor |
| APP-240 Identity Sync Tracker | repurchase | 2 | Off the shelf product (ArchiveVault) with a SaaS edition from the vendor |
| APP-241 Document Archive Hub | replatform | 5 | Windows Server 2008 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-242 Service Desk Workbench | repurchase | 4 | Off the shelf product (CampaignCraft) with a SaaS edition from the vendor |
| APP-243 Identity Sync API | refactor | 2 | High value (5/5), 49 deploys a year, and the team runs containers today |
| APP-244 Identity Sync Engine | replatform | 2 | Windows Server 2012 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-245 Email Archive Gateway | retire |  | Windows Server 2008 R2 is past end of support and only 22 people use it a month |
| APP-246 Identity Sync Service | replatform | 4 | RHEL 7 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-247 File Transfer Service | replatform | 1 | Windows Server 2008 R2 is past end of support; a rehost would carry an unsupported OS into the cloud |
| APP-248 Print Stream Engine | retire |  | Solaris 10 is past end of support and only 30 people use it a month |
| APP-249 Claims Data Hub | replatform | 3 | Shared database used by 30 apps; move it once to a managed service with replication |
| APP-250 Policy Admin Mainframe | retain |  | Mainframe workload (z/OS 2.5); stays in place until a separate modernization program |

## TCO (5 years)

| Year | Stay on premises | Migrate | Savings |
|---|---|---|---|
| 1 | $20,095,228 | $27,047,849 | $-6,952,621 |
| 2 | $17,270,028 | $15,043,794 | $2,226,234 |
| 3 | $17,317,928 | $13,769,625 | $3,548,303 |
| 4 | $17,319,128 | $13,770,625 | $3,548,503 |
| 5 | $17,223,928 | $13,772,725 | $3,451,203 |

- One time cost: $7,402,000
- NPV at 8%: $3,377,769
- Break-even month: 39 (2030-03-01)
- Hardware refresh avoided: $2,043,600
- Steady state annual savings: $2,864,403

### Assumptions

- `months`: 60
- `discount_rate`: 0.08
- `refresh_years`: 5
- `refresh_physical_usd`: 18000
- `refresh_virtual_per_vcpu_usd`: 450
- `refresh_virtual_per_gb_usd`: 25
- `san_usd_per_gb_month`: 0.1
- `watts_physical`: 450
- `watts_per_vcpu`: 12
- `pue`: 1.6
- `usd_per_kwh`: 0.13
- `facility_usd_per_server_month`: 55
- `vmware_usd_per_vcpu_year`: 85
- `windows_usd_per_server_year`: 900
- `rhel_usd_per_server_year`: 800
- `unix_support_usd_per_server_year`: 3000
- `oracle_support_usd_per_license_year`: 10450
- `oracle_core_factor_onprem`: 0.5
- `sql_support_usd_per_core_year`: 1890
- `onprem_servers_per_fte`: 60
- `fte_usd_year`: 150000
- `mainframe_usd_year`: 4200000
- `target_cpu_util`: 0.65
- `target_mem_util`: 0.8
- `min_vcpu`: 2
- `usd_per_vcpu_hour`: {'general': 0.048, 'memory': 0.063, 'compute': 0.0425}
- `gb_per_vcpu`: {'general': 4, 'memory': 8, 'compute': 2}
- `sizes_vcpu`: (2, 4, 8, 16, 32, 48, 64, 96)
- `commit_discount_prod`: 0.3
- `nonprod_hours_per_week`: 50
- `windows_usd_per_vcpu_hour`: 0.046
- `rhel_usd_per_vcpu_hour`: 0.013
- `oracle_vcpus_per_license`: 2
- `managed_db_premium`: 1.5
- `refactor_compute_factor`: 0.6
- `block_usd_per_gb_month`: 0.08
- `snapshot_share`: 0.2
- `snapshot_usd_per_gb_month`: 0.05
- `wan_egress_usd_per_gb`: 0.02
- `private_link_usd_month`: 3300
- `landing_zone_usd_month`: 25000
- `cloud_instances_per_fte`: 150
- `saas_usd_per_user_month`: 35
- `saas_min_usd_year`: 12000
- `migrate_usd`: {'rehost': 8000, 'replatform': 25000, 'refactor': 150000, 'repurchase': 40000, 'retire': 8000}
- `migrate_per_server_usd`: {'rehost': 1500, 'replatform': 2500, 'refactor': 0, 'repurchase': 0, 'retire': 500}
- `dual_run_months`: 2
- `retire_month`: 6
- `training_usd_per_team`: 25000
- `plan_start`: 2027-01-01

## Risk register

| ID | Score | Category | Risk | Mitigation |
|---|---|---|---|---|
| R-001 | 20 (4x5) | shared database | Claims Data Hub serves 26 migrating apps (6 of them not in the CMDB); 18 cut over in a different wave than the database | Run log based replication to the managed database from wave 2, point every consumer at a DNS alias, rehearse the cutover twice, and keep the on premises copy writable for rollback for two weeks |
| R-002 | 16 (4x4) | discovery | 3 apps talk to 10.88.14.40 on port 445, an address that is not in the CMDB (2 GB in 14 days) | Find the owner, add it to the inventory, and classify it before the first dependent app moves |
| R-003 | 16 (4x4) | discovery | 4 apps talk to 10.88.14.21 on port 1433, an address that is not in the CMDB (65 GB in 14 days) | Find the owner, add it to the inventory, and classify it before the first dependent app moves |
| R-004 | 16 (4x4) | discovery | Agency Contract API has 1 dependency seen only in network flows (Marketing Campaign Reporting); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-005 | 16 (4x4) | discovery | Catastrophe Gateway has 2 dependencies seen only in network flows (First Notice Tracker, Claims Data Hub); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-006 | 16 (4x4) | discovery | Claim Payment Console has 1 dependency seen only in network flows (Claims Data Hub); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-007 | 16 (4x4) | discovery | First Notice Reporting has 1 dependency seen only in network flows (Claims Data Hub); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-008 | 16 (4x4) | discovery | Loss Control Service has 2 dependencies seen only in network flows (Risk Survey API, Loss Control Portal); 2 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-009 | 16 (4x4) | discovery | Loss Triangle Console has 1 dependency seen only in network flows (Policy Admin Mainframe); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-010 | 16 (4x4) | discovery | Medical Bill Service has 2 dependencies seen only in network flows (Repair Network Portal, Repair Network Gateway); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-011 | 16 (4x4) | discovery | Reinsurance API has 1 dependency seen only in network flows (Premium Accounting Viewer); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-012 | 16 (4x4) | discovery | Reinsurance Engine has 2 dependencies seen only in network flows (Reinsurance Workbench, Risk Survey API); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-013 | 16 (4x4) | discovery | Repair Network Calculator has 2 dependencies seen only in network flows (Fraud Score Calculator, Fraud Score Console); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-014 | 16 (4x4) | discovery | Repair Network Portal has 1 dependency seen only in network flows (Claims Data Hub); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-015 | 16 (4x4) | discovery | Reserve Reporting has 2 dependencies seen only in network flows (Claims Data Hub, Repair Network Gateway); 2 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-016 | 16 (4x4) | latency | Broker Quote Calculator (wave 9) is latency sensitive and its database in Exposure Console (wave 14) moves separately; 6,263 connections a day would cross the WAN | Move both in the same wave, or keep a replica of the database next to Broker Quote Calculator until Exposure Console moves |
| R-017 | 16 (4x4) | latency | Catastrophe API (wave 13) is latency sensitive and its database in Claims Data Hub (wave 3) moves separately; 23,181 connections a day would cross the WAN | Move both in the same wave, or keep a replica of the database next to Catastrophe API until Claims Data Hub moves |
| R-018 | 16 (4x4) | latency | Catastrophe API (wave 13) is latency sensitive and its database in First Notice Reporting (wave 6) moves separately; 180 connections a day would cross the WAN | Move both in the same wave, or keep a replica of the database next to Catastrophe API until First Notice Reporting moves |
| R-019 | 16 (4x4) | latency | Catastrophe Gateway (wave 6) is latency sensitive and its database in Claims Data Hub (wave 3) moves separately; 13,792 connections a day would cross the WAN | Move both in the same wave, or keep a replica of the database next to Catastrophe Gateway until Claims Data Hub moves |
| R-020 | 16 (4x4) | latency | Claim Payment Console (wave 4) is latency sensitive and its database in Claims Data Hub (wave 3) moves separately; 42,739 connections a day would cross the WAN | Move both in the same wave, or keep a replica of the database next to Claim Payment Console until Claims Data Hub moves |
| R-021 | 16 (4x4) | latency | Endorsement Console (wave 11) is latency sensitive and its database in Claims Data Hub (wave 3) moves separately; 24,280 connections a day would cross the WAN | Move both in the same wave, or keep a replica of the database next to Endorsement Console until Claims Data Hub moves |
| R-022 | 16 (4x4) | latency | First Notice Reporting (wave 6) is latency sensitive and its database in Claims Data Hub (wave 3) moves separately; 166,132 connections a day would cross the WAN | Move both in the same wave, or keep a replica of the database next to First Notice Reporting until Claims Data Hub moves |
| R-023 | 16 (4x4) | latency | Loss Control Service (wave 7) is latency sensitive and its database in Risk Survey API (wave 3) moves separately; 143,908 connections a day would cross the WAN | Move both in the same wave, or keep a replica of the database next to Loss Control Service until Risk Survey API moves |
| R-024 | 16 (4x4) | latency | Repair Network Hub (wave 12) is latency sensitive and its database in Claims Data Hub (wave 3) moves separately; 15,006 connections a day would cross the WAN | Move both in the same wave, or keep a replica of the database next to Repair Network Hub until Claims Data Hub moves |
| R-025 | 16 (4x4) | latency | Salvage Batch (wave 5) is latency sensitive and its database in Claims Data Hub (wave 3) moves separately; 10,660 connections a day would cross the WAN | Move both in the same wave, or keep a replica of the database next to Salvage Batch until Claims Data Hub moves |
| R-026 | 16 (4x4) | retirement | Agency Contract API still calls Marketing Campaign Reporting, which is planned for retirement (1,842 connections a day) | Repoint Agency Contract API first, or move the retirement after its wave |
| R-027 | 16 (4x4) | retirement | Identity Sync API still calls Email Archive Gateway, which is planned for retirement (143,345 connections a day) | Repoint Identity Sync API first, or move the retirement after its wave |
| R-028 | 16 (4x4) | retirement | Life Illustration Service still calls Commission Split Hub, which is planned for retirement (137,915 connections a day) | Repoint Life Illustration Service first, or move the retirement after its wave |
| R-029 | 16 (4x4) | retirement | Medical Underwriting Batch still calls Agent Portal API, which is planned for retirement (751 connections a day) | Repoint Medical Underwriting Batch first, or move the retirement after its wave |
| R-030 | 16 (4x4) | retirement | Renewal Calculator still calls Coverage Selector Service, which is planned for retirement (342 connections a day) | Repoint Renewal Calculator first, or move the retirement after its wave |
| R-031 | 16 (4x4) | retirement | Repair Network Calculator still calls Fraud Score Console, which is planned for retirement (16,706 connections a day) | Repoint Repair Network Calculator first, or move the retirement after its wave |
| R-032 | 16 (4x4) | retirement | Risk Survey Workbench still calls Bond Console, which is planned for retirement (19,018 connections a day) | Repoint Risk Survey Workbench first, or move the retirement after its wave |
| R-033 | 16 (4x4) | retirement | Risk Survey Workbench still calls Exposure Calculator, which is planned for retirement (12,406 connections a day) | Repoint Risk Survey Workbench first, or move the retirement after its wave |
| R-034 | 16 (4x4) | retirement | Workers Comp Viewer still calls Bond Console, which is planned for retirement (32,862 connections a day) | Repoint Workers Comp Viewer first, or move the retirement after its wave |
| R-035 | 15 (3x5) | compliance | PCI: 11 apps bring cardholder data into the cloud, starting in wave 3 | Separate PCI account with its own guardrails, control evidence mapped before wave 3, and an assessor walkthrough of the landing zone |
| R-036 | 15 (3x5) | compliance | PHI: 21 apps bring health data into the cloud, starting in wave 3 | Separate PHI account with its own guardrails, control evidence mapped before wave 3, and an assessor walkthrough of the landing zone |
| R-037 | 12 (3x4) | compliance | PII: 104 apps bring personal data into the cloud, starting in wave 2 | Separate PII account with its own guardrails, control evidence mapped before wave 2, and an assessor walkthrough of the landing zone |
| R-038 | 12 (3x4) | compliance | SOX: 27 apps bring financial reporting systems into the cloud, starting in wave 2 | Separate SOX account with its own guardrails, control evidence mapped before wave 2, and an assessor walkthrough of the landing zone |
| R-039 | 12 (4x3) | configuration | Agent Portal Loader has IP literals in its config (10.25.3.79); they change on migration | Replace with DNS names before the wave and rescan the config |
| R-040 | 12 (4x3) | configuration | Bond Gateway has IP literals in its config (10.22.3.146); they change on migration | Replace with DNS names before the wave and rescan the config |
| R-041 | 12 (4x3) | configuration | Claim Payment Loader has IP literals in its config (10.30.1.11); they change on migration | Replace with DNS names before the wave and rescan the config |
| R-042 | 12 (4x3) | configuration | Commission Workbench has IP literals in its config (10.25.3.56); they change on migration | Replace with DNS names before the wave and rescan the config |
| R-043 | 12 (4x3) | configuration | Discount Loader has IP literals in its config (10.20.1.154); they change on migration | Replace with DNS names before the wave and rescan the config |
| R-044 | 12 (4x3) | configuration | Experience Study Gateway has IP literals in its config (10.26.8.25); they change on migration | Replace with DNS names before the wave and rescan the config |
| R-045 | 12 (4x3) | configuration | First Notice Gateway has IP literals in its config (10.30.1.10); they change on migration | Replace with DNS names before the wave and rescan the config |
| R-046 | 12 (4x3) | configuration | Fleet Rating Calculator has IP literals in its config (10.21.5.49); they change on migration | Replace with DNS names before the wave and rescan the config |
| R-047 | 12 (4x3) | configuration | Fleet Rating Viewer has IP literals in its config (10.21.5.126); they change on migration | Replace with DNS names before the wave and rescan the config |
| R-048 | 12 (4x3) | configuration | Life Illustration Engine has IP literals in its config (10.23.6.45); they change on migration | Replace with DNS names before the wave and rescan the config |
| R-049 | 12 (4x3) | configuration | Medical Underwriting Batch has IP literals in its config (10.23.6.30); they change on migration | Replace with DNS names before the wave and rescan the config |
| R-050 | 12 (4x3) | configuration | Premium Accounting Calculator has IP literals in its config (10.24.8.47); they change on migration | Replace with DNS names before the wave and rescan the config |
| R-051 | 12 (4x3) | configuration | Premium Accounting Hub has IP literals in its config (10.10.1.11); they change on migration | Replace with DNS names before the wave and rescan the config |
| R-052 | 12 (4x3) | configuration | Reinsurance Gateway has IP literals in its config (10.24.8.29); they change on migration | Replace with DNS names before the wave and rescan the config |
| R-053 | 12 (4x3) | configuration | Risk Survey API has IP literals in its config (10.21.5.59); they change on migration | Replace with DNS names before the wave and rescan the config |
| R-054 | 12 (4x3) | configuration | Salvage Batch has IP literals in its config (10.30.1.10); they change on migration | Replace with DNS names before the wave and rescan the config |
| R-055 | 12 (4x3) | configuration | Submission Calculator has IP literals in its config (10.21.5.82); they change on migration | Replace with DNS names before the wave and rescan the config |
| R-056 | 12 (4x3) | configuration | Underwriting Rules Workbench has IP literals in its config (10.20.1.147); they change on migration | Replace with DNS names before the wave and rescan the config |
| R-057 | 12 (4x3) | configuration | Workers Comp Console has IP literals in its config (10.21.5.57); they change on migration | Replace with DNS names before the wave and rescan the config |
| R-058 | 12 (4x3) | discovery | Billing Plan Sync has 1 dependency seen only in network flows (Underwriting Rules Gateway); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-059 | 12 (4x3) | discovery | Commission Portal has 1 dependency seen only in network flows (Policy Admin Mainframe); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-060 | 12 (4x3) | discovery | Endorsement Viewer has 2 dependencies seen only in network flows (Underwriting Rules Loader, Renewal Viewer); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-061 | 12 (4x3) | discovery | Experience Study Viewer has 2 dependencies seen only in network flows (Pricing Model Gateway, Pricing Model Calculator); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-062 | 12 (4x3) | discovery | Exposure Portal has 1 dependency seen only in network flows (Fleet Rating Viewer); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-063 | 12 (4x3) | discovery | File Transfer Viewer has 2 dependencies seen only in network flows (Identity Sync Gateway, Identity Sync Service); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-064 | 12 (4x3) | discovery | Fleet Rating Viewer has 2 dependencies seen only in network flows (Fleet Rating Loader, Submission Calculator); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-065 | 12 (4x3) | discovery | Job Scheduler Viewer has 1 dependency seen only in network flows (Email Archive Gateway); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-066 | 12 (4x3) | discovery | Learning Service has 1 dependency seen only in network flows (Time Entry Tracker); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-067 | 12 (4x3) | discovery | Loss Control Viewer has 1 dependency seen only in network flows (Policy Admin Mainframe); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-068 | 12 (4x3) | discovery | Subrogation Batch has 2 dependencies seen only in network flows (Fraud Score Calculator, Reserve Hub); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-069 | 12 (4x3) | discovery | Tax Tracker has 2 dependencies seen only in network flows (Policy Admin Mainframe, Reserve Loader); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-070 | 12 (4x3) | discovery | Underwriting Rules Gateway has 1 dependency seen only in network flows (Home Rating Portal); 1 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-071 | 12 (4x3) | discovery | Workers Comp Gateway has 2 dependencies seen only in network flows (Exposure Hub, Endorsement Batch); 2 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-072 | 12 (4x3) | latency | Pricing Model API (wave 12) is latency sensitive and its database in Pricing Model Gateway (wave 11) moves separately; 16,371 connections a day would cross the WAN | Move both in the same wave, or keep a replica of the database next to Pricing Model API until Pricing Model Gateway moves |
| R-073 | 12 (3x4) | mainframe | 11 apps exchange nightly batch files with Policy Admin Mainframe (57 GB a night); after they move, every file crosses the private link inside the batch window | Measure the batch window on the private link before wave 2, size the link for the nightly peak, and keep file transfer retry and checkpoint settings |
| R-074 | 12 (4x3) | retirement | Agency Contract Hub still calls Commission Gateway, which is planned for retirement (16,418 connections a day) | Repoint Agency Contract Hub first, or move the retirement after its wave |
| R-075 | 12 (4x3) | retirement | Agency Contract Hub still calls Coverage Selector Tracker, which is planned for retirement (1,463 connections a day) | Repoint Agency Contract Hub first, or move the retirement after its wave |
| R-076 | 12 (4x3) | retirement | Agency Contract Hub still calls Tax Service, which is planned for retirement (893 connections a day) | Repoint Agency Contract Hub first, or move the retirement after its wave |
| R-077 | 12 (4x3) | retirement | Annuity Payout Service still calls Medical Underwriting Loader, which is planned for retirement (6,866 connections a day) | Repoint Annuity Payout Service first, or move the retirement after its wave |
| R-078 | 12 (4x3) | retirement | Benefits Console still calls Benefits API, which is planned for retirement (166,528 connections a day) | Repoint Benefits Console first, or move the retirement after its wave |
| R-079 | 12 (4x3) | retirement | Expense Hub still calls Accounts Payable Console, which is planned for retirement (58 connections a day) | Repoint Expense Hub first, or move the retirement after its wave |
| R-080 | 12 (4x3) | retirement | Job Scheduler Viewer still calls Email Archive Gateway, which is planned for retirement (88,998 connections a day) | Repoint Job Scheduler Viewer first, or move the retirement after its wave |
| R-081 | 12 (4x3) | retirement | Lead Routing Reporting still calls Marketing Campaign Reporting, which is planned for retirement (10,841 connections a day) | Repoint Lead Routing Reporting first, or move the retirement after its wave |
| R-082 | 12 (4x3) | retirement | Medical Bill Gateway still calls Fraud Score Console, which is planned for retirement (102,248 connections a day) | Repoint Medical Bill Gateway first, or move the retirement after its wave |
| R-083 | 12 (4x3) | retirement | Tax Sync still calls Tax Service, which is planned for retirement (192,975 connections a day) | Repoint Tax Sync first, or move the retirement after its wave |
| R-084 | 12 (4x3) | skills | Team annuity-ops (cloud skill 1 of 3) owns 8 replatform or refactor moves | Training before its first wave, pair with platform-eng on the first two moves, and put its simplest app first |
| R-085 | 12 (4x3) | skills | Team claims-payments (cloud skill 1 of 3) owns 7 replatform or refactor moves | Training before its first wave, pair with platform-eng on the first two moves, and put its simplest app first |
| R-086 | 12 (4x3) | skills | Team commercial-uw (cloud skill 1 of 3) owns 11 replatform or refactor moves | Training before its first wave, pair with platform-eng on the first two moves, and put its simplest app first |
| R-087 | 12 (4x3) | skills | Team finance-systems (cloud skill 1 of 3) owns 6 replatform or refactor moves | Training before its first wave, pair with platform-eng on the first two moves, and put its simplest app first |
| R-088 | 12 (4x3) | skills | Team life-admin (cloud skill 0 of 3) owns 3 replatform or refactor moves | Training before its first wave, pair with platform-eng on the first two moves, and put its simplest app first |
| R-089 | 12 (4x3) | skills | Team people-systems (cloud skill 1 of 3) owns 2 replatform or refactor moves | Training before its first wave, pair with platform-eng on the first two moves, and put its simplest app first |
| R-090 | 12 (4x3) | skills | Team specialty-lines (cloud skill 1 of 3) owns 6 replatform or refactor moves | Training before its first wave, pair with platform-eng on the first two moves, and put its simplest app first |
| R-091 | 9 (3x3) | lifecycle | Accounts Payable Reporting is rehosted on Windows Server 2016, which is out of support within two years | Upgrade the OS on the cloud copy within two quarters of cutover |
| R-092 | 9 (3x3) | lifecycle | Beneficiary Tracker is rehosted on Windows Server 2012 R2, which is out of support within two years | Upgrade the OS on the cloud copy within two quarters of cutover |
| R-093 | 9 (3x3) | lifecycle | Expense Service is rehosted on Windows Server 2016, which is out of support within two years | Upgrade the OS on the cloud copy within two quarters of cutover |
| R-094 | 9 (3x3) | lifecycle | Fleet Rating Viewer is rehosted on Windows Server 2016, which is out of support within two years | Upgrade the OS on the cloud copy within two quarters of cutover |
| R-095 | 9 (3x3) | lifecycle | Service Desk Gateway is rehosted on Windows Server 2016, which is out of support within two years | Upgrade the OS on the cloud copy within two quarters of cutover |
| R-096 | 8 (2x4) | discovery | Agent Portal Calculator has 1 dependency seen only in network flows (Lead Routing Workbench); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-097 | 8 (2x4) | discovery | Auto Quote Hub has 1 dependency seen only in network flows (Underwriting Rules Workbench); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-098 | 8 (2x4) | discovery | Auto Quote Portal has 1 dependency seen only in network flows (Submission Batch); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-099 | 8 (2x4) | discovery | Benefits Batch has 1 dependency seen only in network flows (Fleet Rating Gateway); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-100 | 8 (2x4) | discovery | Benefits Sync has 1 dependency seen only in network flows (Time Entry Tracker); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-101 | 8 (2x4) | discovery | Catastrophe API has 1 dependency seen only in network flows (First Notice Gateway); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-102 | 8 (2x4) | discovery | Commission Sync has 1 dependency seen only in network flows (Lead Routing Engine); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-103 | 8 (2x4) | discovery | Document Archive Hub has 1 dependency seen only in network flows (Job Scheduler Loader); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-104 | 8 (2x4) | discovery | Experience Study Gateway has 1 dependency seen only in network flows (Pricing Model Gateway); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-105 | 8 (2x4) | discovery | Fleet Rating Loader has 1 dependency seen only in network flows (Fleet Rating Gateway); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-106 | 8 (2x4) | discovery | Fraud Score Batch has 1 dependency seen only in network flows (First Notice Gateway); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-107 | 8 (2x4) | discovery | General Ledger Viewer has 1 dependency seen only in network flows (Tax Batch); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-108 | 8 (2x4) | discovery | Job Scheduler Loader has 1 dependency seen only in network flows (Statutory Reporting Viewer); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-109 | 8 (2x4) | discovery | Lead Routing API has 1 dependency seen only in network flows (Lead Routing Reporting); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-110 | 8 (2x4) | discovery | Medical Underwriting Batch has 1 dependency seen only in network flows (Annuity Payout Sync); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-111 | 8 (2x4) | discovery | Medical Underwriting Service has 2 dependencies seen only in network flows (Beneficiary Portal, Identity Sync Service); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-112 | 8 (2x4) | discovery | Policy Loan Viewer has 1 dependency seen only in network flows (Beneficiary Calculator); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-113 | 8 (2x4) | discovery | Premium Accounting Viewer has 1 dependency seen only in network flows (Reinsurance Workbench); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-114 | 8 (2x4) | discovery | Reinsurance Viewer has 1 dependency seen only in network flows (General Ledger Portal); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-115 | 8 (2x4) | discovery | Reserve Calculator has 1 dependency seen only in network flows (First Notice Console); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-116 | 8 (2x4) | discovery | Service Desk Gateway has 1 dependency seen only in network flows (Service Desk Workbench); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-117 | 8 (2x4) | discovery | Statutory Reporting Batch has 1 dependency seen only in network flows (General Ledger Portal); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-118 | 8 (2x4) | discovery | Statutory Reporting Viewer has 1 dependency seen only in network flows (Expense Hub); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-119 | 8 (2x4) | discovery | Telematics Workbench has 1 dependency seen only in network flows (Telematics Calculator); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-120 | 8 (2x4) | discovery | Underwriting Rules Viewer has 1 dependency seen only in network flows (Telematics Viewer); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-121 | 6 (2x3) | discovery | Annuity Payout Portal has 1 dependency seen only in network flows (Life Illustration Engine); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-122 | 6 (2x3) | discovery | Beneficiary Gateway has 2 dependencies seen only in network flows (Commission Split Service, Annuity Payout Service); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-123 | 6 (2x3) | discovery | Benefits Console has 1 dependency seen only in network flows (Risk Survey Workbench); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-124 | 6 (2x3) | discovery | Capital Model Engine has 1 dependency seen only in network flows (Pricing Model Calculator); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-125 | 6 (2x3) | discovery | Claim Payment Loader has 1 dependency seen only in network flows (First Notice Console); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-126 | 6 (2x3) | discovery | Coverage Selector Reporting has 1 dependency seen only in network flows (Renewal Viewer); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-127 | 6 (2x3) | discovery | Identity Sync Tracker has 1 dependency seen only in network flows (Identity Sync Engine); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-128 | 6 (2x3) | discovery | Lead Routing Workbench has 2 dependencies seen only in network flows (Producer Licensing Reporting, Identity Sync Batch); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-129 | 6 (2x3) | discovery | Producer Licensing API has 1 dependency seen only in network flows (Lead Routing API); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-130 | 6 (2x3) | discovery | Repair Network Gateway has 1 dependency seen only in network flows (Claims Data Hub); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-131 | 6 (2x3) | discovery | Subrogation Hub has 1 dependency seen only in network flows (Catastrophe Tracker); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-132 | 6 (2x3) | discovery | Tax Viewer has 1 dependency seen only in network flows (Reinsurance Hub); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-133 | 6 (2x3) | discovery | Underwriting Rules Calculator has 1 dependency seen only in network flows (Endorsement API); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-134 | 6 (2x3) | discovery | Underwriting Rules Loader has 1 dependency seen only in network flows (Auto Quote Portal); 0 split across waves | Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan |
| R-135 | 6 (2x3) | schedule | Medical Bill Console can only move in 6 of 14 waves (change freezes, team availability) | Book the wave early; a slip pushes it out by several months |
| R-136 | 4 (2x2) | discovery | 15 documented dependencies had no traffic in 14 days | Check for monthly or quarterly jobs before removing them from the CMDB; extend the flow capture over a month end |

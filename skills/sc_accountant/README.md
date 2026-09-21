# Star Citizen Personal ERP 4.9.0.4

Track personal operations, money, cargo, production, fleet assets, plans, and
reports. Simple and Advanced are views of the same records; changing the view
does not reset history.

## Requirements and installation

This skill uses Wingman Skill API v3 and its FastAPI, uvicorn, and Pillow
dependencies. Fully close Wingman, back up the existing skill folder outside
`custom_skills`, and copy this entire `sc_accountant` folder into
`%APPDATA%/ShipBit/WingmanAI/custom_skills`. Restart Wingman and enable
Star Citizen Personal ERP in the desired profile. Preserve user data and saved
profile settings when upgrading. The default configuration must declare API v3.

The skill exposes `erp_report`, `erp_record`, and `erp_dashboard`. Ask Wingman
to open the accounting dashboard for detailed entry and reports. About fifteen
seconds after activation, a startup card provides the computer link and a phone
QR link. The QR contains a session access key; treat it as access to the books.
Restarting issues a new key. The local dashboard port defaults to 7863.

## Optional automatic capture

Enable SC Log Reader 0.5.0 or newer in the same Wingman profile. Leave
SC_LogReader database blank to discover that reader's Runtime Directory, or
provide an explicit full path to its `events.sqlite3`. Capture runs every
fifteen seconds by default; set the interval to zero to pause it. Manual entry
works without the reader. This contribution does not include or start a reader.

The ERP stores its own `erp.sqlite3` in its generated-files directory. Capture
reads the reader database without modifying it. Source identity and cursor are
saved with imports to avoid silently mixing sources or duplicating entries.
Do not run multiple capture processes against the same ERP database.

Requests remain pending until confirmed. Physical rewards are not cash, unknown
costs keep profit incomplete, and recorded balance need not match the game
wallet. Use Attention and wallet reconciliation to review missing evidence.
Legacy records are imported only on explicit request; back up their files first.
The retired Accountant implementation and old dashboard are not included.

Stop the application before backing up its data directory. Local package and
behavioral checks do not establish qualification on the latest running Wingman.
LICENSE contains the skill license; QR generator attribution is retained in
`accountant_ui/qrcodegen.py`.

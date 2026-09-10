---
paths:
  - "benchmarks/**"
---

# Rules for benchmarks

- `results/*.json` are evidence. Never edit them by hand. Rerun the script.
- Every result file carries `measured_at`, a `limitations` list, the product IDs or catalog snapshot it depends on, and the code version.
- Every result names the bucket or endpoint, its region, and who paid for the reads. Requester-pays reads cost money. Record bytes and requests.
- Declare tolerances before you look at a difference. Never change a tolerance to make a check pass. Add a separate diagnostic instead.
- Label what a number is: bytes transferred, requests made, pixels read, or output bytes. Never present one as another.
- Report distinct tiles and distinct tile-dates beside water-body counts. Water-body count alone is not the scale driver (assumption A17).
- Scripts that contact AWS or any provider run only when the user invokes them. Do not run them from an automated skill.

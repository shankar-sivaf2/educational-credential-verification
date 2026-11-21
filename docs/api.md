# API reference

Base URL: `http://127.0.0.1:8000/api`. Interactive docs: `http://127.0.0.1:8000/docs`.

Errors always look like:
```json
{ "error": { "code": "NO_RECORDS", "message": "No records found for that student ID and access code." } }
```

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | /health | none | Database and blockchain status |
| POST | /auth/login | none | Admin login, returns a JWT |
| GET | /auth/me | admin | Current admin |
| POST | /certificates | admin | Issue and register a certificate (201) |
| GET | /certificates | admin | List (`status`, `limit`, `offset`) |
| GET | /certificates/{id} | admin | One certificate |
| POST | /certificates/{id}/revoke | admin | Revoke on-chain |
| GET | /certificates/{id}/qr.png | admin | QR code image |
| GET | /audit | admin | Audit log (`event_type`, `limit`, `offset`) |
| POST | /verify | none | Verify certificate data (JSON body) |
| POST | /verify/upload | none | Verify an uploaded JSON file (max 64 KB, not stored) |
| GET | /verify/status/{id} | none | QR lookup: status only, no personal data |
| POST | /student/records | none* | Student's own certificates (*needs ID + access code) |

## Examples (PowerShell)
Log in:
```powershell
$r = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/auth/login `
  -ContentType application/json -Body '{"username":"admin","password":"ChangeMe@123"}'
$token = $r.access_token
```
Issue:
```powershell
$body = @{ certificate_id="CERT-2026-0001"; student_id="STU0001"; student_name="Asha Raman";
  institution_name="Demo Institute of Technology"; degree="B.Tech";
  department="Computer Science and Engineering"; graduation_year=2026 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/certificates `
  -Headers @{ Authorization = "Bearer $token" } -ContentType application/json -Body $body
```
The response has `certificate`, `access_code` (shown once), `package` and `verify_url`.

## Status codes
| Code | When |
|---|---|
| 401 | Missing, invalid or expired token; wrong login |
| 404 | Certificate not found; `NO_RECORDS` for students |
| 409 | `DUPLICATE_ON_CHAIN` or other duplicate |
| 413 | Uploaded file larger than 64 KB |
| 422 | Invalid input or `INVALID_CERTIFICATE_FILE` |
| 429 | Too many failed attempts (5 in 5 minutes) |
| 502/503 | Blockchain unreachable or transaction failed (certificate is not marked registered) |

Verification always returns 200 with a verdict, including for unknown or altered certificates.
`SERVICE_UNAVAILABLE` is a verdict, not an error, so an outage is never shown as "invalid".
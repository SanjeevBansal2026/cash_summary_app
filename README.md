# Cash Summary App

Django cash reconciliation and approval system for Cashiers, Managers and Super Users.

## Run locally

```bash
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations cashapp
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

Open `http://127.0.0.1:8000/` and use the superuser account. Admin is at `/admin/`.

## Workflow

- Cashier can select only allotted Brand and Location.
- Main Cash: Opening + Collection - Deposit - Transfer to Petty Cash = System Closing.
- Petty Cash: Opening + Received From Main Cash - Expenses = System Closing.
- Denominations are 500/200/100/50/20/10/5/2/1 and their total is compared with System Closing.
- Difference = System Closing - Denomination Total.
- Only Revised entries can be edited by the cashier and resubmitted.
- Managers see only their assigned cashiers and can Approve, Revise or Reject.
- A cashier can have multiple managers.
- Superuser can see all entries and approval history.

## Cloudflare Tunnel

Run the Django server on `0.0.0.0:8000`, then point Cloudflare Tunnel to `http://127.0.0.1:8000`.

For a named hostname, set environment variables before starting Django:

```text
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,cash.example.com
CSRF_TRUSTED_ORIGINS=https://cash.example.com
```

For temporary `trycloudflare.com` tunnels, add the generated hostname to both values if CSRF rejects the request.

## Notes

The included UI is responsive and does not require a JavaScript framework. Uploaded files are stored under `media/`.


## Cloudflare Tunnel

For a Quick Tunnel, start Django on port 9000 and run:

    cloudflared tunnel --url http://127.0.0.1:9000

This build accepts Cloudflare's dynamic `*.trycloudflare.com` hostname and trusts that HTTPS origin for CSRF. No BAT file is required.

For a named tunnel/custom domain, set these environment variables before starting Django:

    DJANGO_ALLOWED_HOSTS=your-domain.example.com
    CSRF_TRUSTED_ORIGINS=https://your-domain.example.com

If Windows PowerShell is being used:

    $env:DJANGO_ALLOWED_HOSTS="your-domain.example.com,127.0.0.1,localhost"
    $env:CSRF_TRUSTED_ORIGINS="https://your-domain.example.com"
    python manage.py runserver 0.0.0.0:9000

# gmail-account-generator

A Python project to generate Gmail accounts.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
copy .env.example .env
```

3. Run the script:
```bash
python main.py
```

## Notes

- The script uses Brave browser by default. If Brave is not installed, it will use the default browser.
- Proxies are read from `proxies.txt`.
- The script uses a DaisySMS API to get phone numbers.
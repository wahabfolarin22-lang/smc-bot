# SMC Bias Bot (H4 / H1 / M15) - quick start

1. Create a PUBLIC GitHub repo and upload everything in this folder (keep the hidden .github folder).
2. Edit TICKERS in config.py to the exact tickers on your TradingView charts ("EXCHANGE:SYMBOL").
3. Repo -> Settings -> Secrets and variables -> Actions -> add TELEGRAM_TOKEN and TELEGRAM_CHAT_ID.
4. Actions tab -> "TradingView data test" -> Run workflow. Every pair should say PASS.
5. Actions tab -> "Bias bot" -> Run workflow with force ticked. 7 briefs should arrive on Telegram.
6. Leave it. It runs Mon-Fri 09:00-17:00 London on its own.

Offline self-test (no internet needed): python selftest.py   -> 25 checks should pass.
Full guide, features and sample messages are in the Claude doc that came with this zip.

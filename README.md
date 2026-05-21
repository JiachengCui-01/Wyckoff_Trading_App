# Wyckoff Trading

Wyckoff trading analysis web app deployed on Vercel.

## Current App

The app is served from `index.html` through `api/index.js` and uses Vercel serverless functions:

- `api/chat.js` reads `data/wyckoff_all_labels_combined.csv` and returns top matching Wyckoff Q&A context.
- `api/analyze.js` fetches Yahoo Finance chart data, detects Wyckoff events such as `SC`, `BC`, `SP`, `UT`, `SOS`, and `SOW`, estimates the current phase, and returns chart/backtest data.

## Notes

This app is for educational analysis only and is not financial advice. The repository keeps only the files needed to run the current Vercel version.

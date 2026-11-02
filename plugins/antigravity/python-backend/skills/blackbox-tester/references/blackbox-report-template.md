# Black-Box Browser Verification Report

> **Zero-Fluff Cap (`<= 50 lines` max, `<= 20 lines` on clean pass)**: Output ONLY the metadata header, viewport metrics table, and actionable defects. Omit all prose sections. If `PASSED`, replace the Defects table with `None.` If pre-flight fails, output ONLY the header and `SKIPPED: No web UI in scope` or `BLOCKED: Not executed — <exact command & terminal error>`.

- **Feature**: `<feature-name>` | **Date**: `YYYY-MM-DD` | **Target URL**: `http://localhost:3000`
- **Runner**: `Playwright Chromium` | **Verdict**: `[PASSED | REJECTED | BLOCKED | SKIPPED]`
- **Journeys**: `[X/Y Passed]` | **Unhandled JS Errors**: `0` | **Unexpected HTTP 4xx/5xx**: `0`

## 1. Viewport & Journey Metrics

| Viewport | Dimensions | Evidence (`docs/<feature-name>/evidence/`) | Overflow-X | Forms & Flows | JS / HTTP Errors | Status |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| **Mobile** | `375x812` | `mobile-375x812.png` | `0px` | `PASS` | `0 / 0` | `PASS` |
| **Tablet** | `768x1024` | `tablet-768x1024.png` | `0px` | `PASS` | `0 / 0` | `PASS` |
| **Desktop** | `1280x800` | `desktop-1280x800.png` | `0px` | `PASS` | `0 / 0` | `PASS` |
| **Widescreen** | `1920x1080` | `widescreen-1920x1080.png` | `0px` | `PASS` | `0 / 0` | `PASS` |

## 2. Actionable Defects (Omit table & write `None.` if `PASSED`, `BLOCKED`, or `SKIPPED`)

| ID | Severity | Viewport / Route | Observed Defect | Reproduction Steps | Required Fix |
| :---: | :---: | :--- | :--- | :--- | :--- |
| `BB-01` | `HIGH` | `375x812` `/checkout` | Submit CTA clipped by sticky bar | Open `/checkout` at `375x812`, scroll bottom | Add `pb-20` safe-area padding |

# Flutter Web with Playwright

Flutter web paints to a canvas, so its text and buttons are not in the DOM. Playwright reaches them through
Flutter's accessibility tree. This works with the release build and needs no change to the app. No `chromedriver`
is needed. Verified on Flutter 3.47.2 with five consecutive runs.

## Run the app

```bash
flutter build web --release
```

Serve `build/web` with the same backend the app uses in development. Do not run the Flutter dev server in the test.

## Turn on the accessibility tree

Do this after every `page.goto` and `page.reload`:

```js
async function enableFlutterSemantics(page) {
  const placeholder = page.locator('flt-semantics-placeholder');
  await placeholder.waitFor({ state: 'attached', timeout: 30000 });
  await placeholder.evaluate((element) => element.click());
}
```

## Type like a user

`locator.fill()` can leave Flutter's controller empty, which sends blank values to the backend. Click, wait for focus,
type, and check the value:

```js
const field = page.getByRole('textbox', { name: 'Item name' });
await field.click();
await expect(field).toBeFocused();
await page.keyboard.type(label, { delay: 20 });
await expect(field).toHaveValue(label);
```

Typing before the field has focus can lose the first characters.

## Rules that do not change

- Locate by role and name: `getByRole('button', { name: 'Add item' })`. Give custom widgets a `Semantics` label.
- Use `recordRun` and take the screenshots for all four viewports, as on any web app.
- Flutter's own files appear as `fetch` requests. `check_evidence.py` ignores them, so a real data request is required.
- Mobile-only projects, with no `web/` directory, are out of scope: return `SKIPPED: mobile target, not in scope`.

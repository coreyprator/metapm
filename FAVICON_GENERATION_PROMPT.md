# Favicon Generation Prompt Template

Use this prompt when you need Claude to generate favicons for a project.

---

## Prompt Template

```
Create a complete favicon set for my project.

**Project Name:** [PROJECT_NAME]
**Primary Color:** [HEX_COLOR e.g., #DC2626]
**Secondary Color:** [HEX_COLOR e.g., #1E293B] (optional)
**Icon Style:** [Choose one]
- Letter/Initial (e.g., "M" for MetaPM)
- Simple geometric shape
- Abstract symbol
- Text abbreviation

**Letter/Symbol to Use:** [e.g., "M", "AF", "✓"]

**Generate these files:**
- favicon.ico (multi-size: 16x16, 32x32, 48x48)
- favicon-16x16.png
- favicon-32x32.png
- apple-touch-icon.png (180x180)
- icon-192.png (for PWA manifest)
- icon-512.png (for PWA manifest)

**Deliver as:** Zip file with all assets ready to copy to /static folder
```

---

## Example: MetaPM

```
Create a complete favicon set for my project.

**Project Name:** MetaPM
**Primary Color:** #DC2626 (red)
**Secondary Color:** #1E293B (dark blue-gray)
**Icon Style:** Letter/Initial with accent

**Letter/Symbol to Use:** "M" with small checkmark accent

**Generate these files:**
- favicon.ico (multi-size: 16x16, 32x32, 48x48)
- favicon-16x16.png
- favicon-32x32.png
- apple-touch-icon.png (180x180)
- icon-192.png (for PWA manifest)
- icon-512.png (for PWA manifest)

**Deliver as:** Zip file with all assets ready to copy to /static folder
```

---

## Example: ArtForge

```
Create a complete favicon set for my project.

**Project Name:** ArtForge
**Primary Color:** #DD4814 (Ubuntu orange)
**Secondary Color:** #FFFFFF (white)
**Icon Style:** Letter/Initial

**Letter/Symbol to Use:** "AF" or stylized "A"

**Generate these files:**
- favicon.ico (multi-size: 16x16, 32x32, 48x48)
- favicon-16x16.png
- favicon-32x32.png
- apple-touch-icon.png (180x180)
- icon-192.png (for PWA manifest)
- icon-512.png (for PWA manifest)

**Deliver as:** Zip file with all assets ready to copy to /static folder
```

---

## HTML Integration

After receiving the favicon files, add to your `<head>`:

```html
<!-- Favicons -->
<link rel="icon" type="image/x-icon" href="/static/favicon.ico">
<link rel="icon" type="image/png" sizes="32x32" href="/static/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/static/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/static/apple-touch-icon.png">

<!-- PWA Manifest (update manifest.json) -->
```

Update `manifest.json`:
```json
{
    "icons": [
        {
            "src": "/static/icon-192.png",
            "sizes": "192x192",
            "type": "image/png",
            "purpose": "any maskable"
        },
        {
            "src": "/static/icon-512.png",
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "any maskable"
        }
    ]
}
```

---

## Why Use Claude Instead of VS Code/DALL-E?

| Reason | Explanation |
|--------|-------------|
| **No dependencies** | Claude has Pillow pre-installed, VS Code needs pip install |
| **Precise sizing** | Favicons require exact 16/32/48/192/512 px sizes |
| **All formats at once** | ICO, PNG, all sizes in one request |
| **Simple is better** | 16x16 requires extreme simplicity - complex art fails |
| **No thrashing** | VS Code AI may iterate endlessly; Claude generates once |
| **Methodology compliant** | Delivers tested, ready-to-deploy assets |

# ANN Intelligence Feed

A professional, editorial-style news website built for GitHub Pages.

## 🚀 Deploy to GitHub Pages

1. **Create a new GitHub repository** (e.g. `ann-feed` or `yourusername.github.io`)
2. **Upload the files** — drop `index.html` and `_config.yml` into the repo root
3. **Enable GitHub Pages:**
   - Go to **Settings → Pages**
   - Source: `Deploy from a branch`
   - Branch: `main` → `/ (root)`
   - Click **Save**
4. Your site will be live at `https://yourusername.github.io/ann-feed` (or your custom domain)

## 📁 File Structure

```
/
├── index.html       ← Main news page (self-contained)
├── _config.yml      ← GitHub Pages / Jekyll config
└── README.md
```

## ✏️ Customising Content

All content is in `index.html`. Key sections:

| Element | How to edit |
|---|---|
| **Ticker** | Edit the `<span>` items inside `.ticker-track` |
| **Breaking banner** | Edit text in `.breaking-banner` |
| **Hero story** | Edit the `#hero-lead` article block |
| **Cards** | Edit `.card` blocks inside each `.card-grid` |
| **Data table** | Edit `<tr>` rows in `.data-table tbody` |
| **Colours** | Edit CSS variables in `:root` |

## 🎨 Design

- **Typography:** Playfair Display (headlines) + Source Serif 4 (body) + DM Mono (labels)
- **Palette:** Aged paper tones with gold accents — editorial broadsheet aesthetic
- **Features:** Live news ticker, breaking banner, responsive 3-column front page, data table, active nav on scroll

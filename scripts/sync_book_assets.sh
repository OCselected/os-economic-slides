#!/bin/bash
set -euo pipefail
BOOK_REPO="${BOOK_REPO:-/home/lee/developing/open-source-economics-book}"
SITE_ROOT="${SITE_ROOT:-/home/lee/developing/os-economic-slides}"
DEST="${SITE_ROOT}/static/book"
mkdir -p "${DEST}"
echo "=== Syncing book assets ==="
cp "${BOOK_REPO}/output/open-source-economics.html" "${DEST}/"
cp "${BOOK_REPO}/output/open-source-economics.pdf"  "${DEST}/"
cp "${BOOK_REPO}/output/open-source-economics.epub" "${DEST}/"
cp "${BOOK_REPO}/styles/book.css"                   "${DEST}/"
# Fix relative CSS path for website context
sed -i 's|href="\.\./book.css"|href="book.css"|g' "${DEST}/open-source-economics.html"
echo "=== Done."
ls -lh "${DEST}"

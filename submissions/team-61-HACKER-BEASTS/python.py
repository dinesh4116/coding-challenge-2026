
import re
import json
from html.parser import HTMLParser
from pathlib import Path


class PageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.text.append(data.strip())


def audit(ad_text, page_text):
    words = lambda text: set(
        re.findall(r"\b[a-z0-9]{4,}\b", text.lower())
    )

    ad_words = words(ad_text)
    page_words = words(page_text)

    matched = sorted(ad_words & page_words)
    missing = sorted(ad_words - page_words)

    score = round(100 * len(matched) / len(ad_words)) if ad_words else 0

    return {
        "score": score,
        "matched_words": matched,
        "words_not_found": missing,
        "warning": (
            "This is a simple keyword estimate, not proof that an ad claim is true."
        )
    }


def main():
    print("=== Message Match Auditor ===")

    ad = input("Enter your advertisement text: ").strip()
    filename = input("Enter saved HTML filename (example: page.html): ").strip()

    path = Path(filename)

    if not ad or not path.is_file():
        print("Error: Enter ad text and a valid HTML filename.")
        return

    parser = PageText()

    try:
        parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    except OSError as error:
        print("Could not read file:", error)
        return

    page = " ".join(parser.text)
    report = audit(ad, page)

    print("\n=== AUDIT REPORT ===")
    print(json.dumps(report, indent=2))

    Path("audit_report.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    print("\nReport saved to audit_report.json")


if __name__ == "__main__":
    main()
